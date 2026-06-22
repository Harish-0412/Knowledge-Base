from __future__ import annotations

import asyncio
import re
import time
from typing import Any

import httpx
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.errors import AppError, ErrorResponse
from app.core.config import get_settings

router = APIRouter(
    prefix="/security",
    tags=["Security Intelligence"],
    responses={400: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)

NVD_CVE_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
NVD_CACHE_TTL_SECONDS = 15 * 60
NVD_CACHE_MAX_ENTRIES = 256
_nvd_cache: dict[str, tuple[float, dict[str, Any], str | None]] = {}


def _looks_like_nvd_api_key(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", value.strip()))


class CveEnrichmentRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=300)
    cpe_name: str | None = None
    cve_ids: list[str] = Field(default_factory=list, max_length=1)
    severity: str | None = None
    results_per_page: int = Field(default=8, ge=1, le=20)


class CveMetric(BaseModel):
    source: str
    score: float | None = None
    severity: str | None = None
    vector: str | None = None


class CveRiskItem(BaseModel):
    cve_id: str
    description: str
    published: str | None = None
    last_modified: str | None = None
    metrics: list[CveMetric] = Field(default_factory=list)
    best_score: float | None = None
    severity: str | None = None
    affected_products: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    kev: bool = False
    kev_added: str | None = None
    kev_due_date: str | None = None
    kev_required_action: str | None = None


class CveEnrichmentResponse(BaseModel):
    query: str
    source: str = "NVD CVE API"
    total_results: int = 0
    results: list[CveRiskItem] = Field(default_factory=list)
    warning: str | None = None
    cached: bool = False


@router.post("/cve-enrichment", response_model=CveEnrichmentResponse)
async def enrich_cve_risk(payload: CveEnrichmentRequest) -> CveEnrichmentResponse:
    settings = get_settings()
    params: dict[str, Any] = {
        "resultsPerPage": payload.results_per_page,
    }

    if payload.cve_ids:
        params["cveId"] = payload.cve_ids[0].strip().upper()
    elif payload.cpe_name:
        params["cpeName"] = payload.cpe_name
        params["isVulnerable"] = ""
    else:
        params["keywordSearch"] = _clean_keyword_query(payload.query)

    if payload.severity:
        normalized = payload.severity.strip().upper()
        if normalized in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
            params["cvssV3Severity"] = normalized

    cache_key = repr(sorted(params.items()))
    cached_item = _nvd_cache.get(cache_key)
    cache_hit = bool(cached_item and time.monotonic() - cached_item[0] < NVD_CACHE_TTL_SECONDS)
    credential_warning: str | None = None

    if cache_hit:
        data = cached_item[1]
        credential_warning = cached_item[2]
    else:
        try:
            headers = {"User-Agent": "CompatIQ/0.1 security-enrichment"}
            if settings.nvd_api_key and _looks_like_nvd_api_key(settings.nvd_api_key):
                headers["apiKey"] = settings.nvd_api_key
            elif settings.nvd_api_key:
                credential_warning = "The configured NVD API key has an invalid format. Results were retrieved without a key and may be rate limited."
            async with httpx.AsyncClient(timeout=settings.nvd_timeout_seconds) as client:
                for attempt in range(3):
                    response = await client.get(NVD_CVE_URL, params=params, headers=headers)
                    if (
                        "apiKey" in headers
                        and response.status_code in {403, 404}
                        and "invalid apikey" in response.headers.get("message", "").lower()
                    ):
                        credential_warning = "The configured NVD API key was rejected. Results were retrieved without a key and may be rate limited."
                        headers.pop("apiKey", None)
                        continue
                    if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                        await asyncio.sleep(1.5 * (attempt + 1))
                        continue
                    break
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            upstream_message = exc.response.headers.get("message") or "NVD CVE API returned an error."
            raise AppError(
                code="nvd_api_error",
                message=upstream_message,
                status_code=502,
                details={"status_code": exc.response.status_code, "provider": "NVD"},
            ) from exc
        except Exception as exc:
            raise AppError(
                code="nvd_api_unavailable",
                message="Could not reach the NVD CVE API.",
                status_code=502,
                details={"reason": str(exc)},
            ) from exc

        if len(_nvd_cache) >= NVD_CACHE_MAX_ENTRIES:
            oldest_key = min(_nvd_cache, key=lambda key: _nvd_cache[key][0])
            _nvd_cache.pop(oldest_key, None)
        _nvd_cache[cache_key] = (time.monotonic(), data, credential_warning)

    vulnerabilities = data.get("vulnerabilities") or []
    results = [_map_nvd_vulnerability(item) for item in vulnerabilities]

    warning = credential_warning
    if not results:
        no_results_warning = "No matching CVEs were found for this rule text. Try a product-specific keyword or CPE name."
        warning = f"{warning} {no_results_warning}" if warning else no_results_warning

    return CveEnrichmentResponse(
        query=payload.query,
        total_results=int(data.get("totalResults") or 0),
        results=results,
        warning=warning,
        cached=cache_hit,
    )


def _clean_keyword_query(query: str) -> str:
    words = re.findall(r"[A-Za-z0-9_.+-]+", query)
    stop = {"requires", "require", "minimum", "version", "later", "must", "when", "present", "or", "and", "the"}
    filtered = [w for w in words if len(w) > 1 and w.lower() not in stop]
    return " ".join(filtered[:10]) or query[:120]


def _map_nvd_vulnerability(item: dict[str, Any]) -> CveRiskItem:
    cve = item.get("cve") or {}
    descriptions = cve.get("descriptions") or []
    description = next((d.get("value") for d in descriptions if d.get("lang") == "en"), "")
    metrics = _extract_metrics(cve.get("metrics") or {})
    best_metric = _best_metric(metrics)

    references_json = cve.get("references") or []
    if isinstance(references_json, dict):
        references_json = references_json.get("referenceData") or []

    return CveRiskItem(
        cve_id=cve.get("id", "UNKNOWN"),
        description=description,
        published=cve.get("published"),
        last_modified=cve.get("lastModified"),
        metrics=metrics,
        best_score=best_metric.score if best_metric else None,
        severity=best_metric.severity if best_metric else None,
        affected_products=_extract_affected_products(cve.get("configurations") or []),
        references=[r.get("url") for r in references_json if r.get("url")][:5],
        kev=bool(cve.get("cisaExploitAdd")),
        kev_added=cve.get("cisaExploitAdd"),
        kev_due_date=cve.get("cisaActionDue"),
        kev_required_action=cve.get("cisaRequiredAction"),
    )


def _extract_metrics(metrics_json: dict[str, Any]) -> list[CveMetric]:
    output: list[CveMetric] = []
    metric_sources = [
        ("cvssMetricV40", "CVSS v4.0"),
        ("cvssMetricV31", "CVSS v3.1"),
        ("cvssMetricV30", "CVSS v3.0"),
        ("cvssMetricV2", "CVSS v2.0"),
    ]

    for key, label in metric_sources:
        for metric in metrics_json.get(key) or []:
            cvss = metric.get("cvssData") or {}
            output.append(
                CveMetric(
                    source=label,
                    score=cvss.get("baseScore"),
                    severity=cvss.get("baseSeverity") or metric.get("baseSeverity"),
                    vector=cvss.get("vectorString"),
                )
            )
    return output


def _best_metric(metrics: list[CveMetric]) -> CveMetric | None:
    if not metrics:
        return None
    return max(metrics, key=lambda metric: metric.score or 0)


def _extract_affected_products(configurations: list[dict[str, Any]]) -> list[str]:
    products: list[str] = []

    def visit_node(node: dict[str, Any]) -> None:
        for match in node.get("cpeMatch") or []:
            criteria = match.get("criteria")
            if criteria:
                products.append(criteria)
        for child in node.get("nodes") or []:
            visit_node(child)

    for config in configurations:
        for node in config.get("nodes") or []:
            visit_node(node)

    deduped = []
    seen = set()
    for product in products:
        if product not in seen:
            seen.add(product)
            deduped.append(product)
    return deduped[:8]
