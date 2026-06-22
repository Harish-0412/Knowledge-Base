from app.api.security_intelligence import (
    _clean_keyword_query,
    _looks_like_nvd_api_key,
    _map_nvd_vulnerability,
)


def test_clean_keyword_query_keeps_product_and_version() -> None:
    assert _clean_keyword_query("Dell BIOS requires minimum version 2.4.1 or later") == "Dell BIOS 2.4.1"


def test_nvd_api_key_format_detection() -> None:
    assert _looks_like_nvd_api_key("12345678-1234-1234-1234-123456789abc") is True
    assert _looks_like_nvd_api_key("not-a-valid-key") is False


def test_map_nvd_vulnerability_extracts_risk_details() -> None:
    result = _map_nvd_vulnerability(
        {
            "cve": {
                "id": "CVE-2026-1234",
                "published": "2026-01-02T00:00:00.000",
                "descriptions": [{"lang": "en", "value": "Example vulnerability."}],
                "metrics": {
                    "cvssMetricV31": [
                        {"cvssData": {"baseScore": 9.8, "baseSeverity": "CRITICAL", "vectorString": "CVSS:3.1/AV:N"}}
                    ]
                },
                "configurations": [
                    {"nodes": [{"cpeMatch": [{"criteria": "cpe:2.3:a:vendor:product:1.0:*:*:*:*:*:*:*"}]}]}
                ],
                "references": [{"url": "https://example.com/advisory"}],
                "cisaExploitAdd": "2026-02-01",
            }
        }
    )

    assert result.cve_id == "CVE-2026-1234"
    assert result.best_score == 9.8
    assert result.severity == "CRITICAL"
    assert result.kev is True
    assert result.affected_products == ["cpe:2.3:a:vendor:product:1.0:*:*:*:*:*:*:*"]
    assert result.references == ["https://example.com/advisory"]
