from enum import Enum


class QueryRoute(str, Enum):
    DOMAIN = "DOMAIN"
    COMPATIBILITY = "COMPATIBILITY"
    HYBRID = "HYBRID"


DOMAIN_TERMS = {
    "bios", "uefi", "firmware", "tpm", "secure boot", "operating system",
    "windows", "linux", "driver", "drivers", "security", "management",
    "endpoint manager", "bootloader", "post", "bitlocker",
}
COMPATIBILITY_TERMS = {
    "compatible", "compatibility", "incompatible", "conflict", "conflicts",
    "required", "requirement", "requirements", "minimum version", "supported version",
    "dependency", "dependencies", "depends", "non-compliance", "non-compliant",
    "compliance", "constraint", "remediation", "update order", "upgrade order",
    "readiness", "fixed", "version",
    "support", "rule", "rules",
}
RELATION_TERMS = {
    "affect", "impact", "relationship", "between", "depend", "depends",
    "dependency", "dependencies", "interact", "influence", "prevent",
}


def _matches(query, terms):
    return {term for term in terms if term in query}


def route_query(query):
    normalized = " ".join(query.lower().split())
    domain_hits = _matches(normalized, DOMAIN_TERMS)
    compatibility_hits = _matches(normalized, COMPATIBILITY_TERMS)
    relation_hits = _matches(normalized, RELATION_TERMS)

    if normalized.startswith("which ") and compatibility_hits:
        return QueryRoute.COMPATIBILITY
    if normalized.startswith("how ") and compatibility_hits and relation_hits:
        return QueryRoute.HYBRID
    if " between " in normalized and len(domain_hits) >= 2 and compatibility_hits:
        return QueryRoute.HYBRID
    if domain_hits and compatibility_hits and relation_hits:
        return QueryRoute.HYBRID
    if len(domain_hits) >= 2 and relation_hits:
        return QueryRoute.HYBRID
    if compatibility_hits:
        return QueryRoute.COMPATIBILITY
    return QueryRoute.DOMAIN


class QueryRouter:
    def route(self, query):
        return route_query(query)
