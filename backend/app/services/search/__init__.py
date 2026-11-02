"""Search package exporting the Tavily adapter and SAP search helpers."""

from backend.app.services.search.base import (
    SearchHit,
    ImageHit,
    SearchProviderError,
    SearchProviderUnavailableError,
    SearchProviderInterface,
)
from backend.app.services.search.tavily_provider import TavilySearchProvider
from backend.app.services.search.unified_service import (
    UnifiedSearchService,
    unified_search_service,
    APPROVED_SAP_DOMAINS,
)

__all__ = [
    "SearchHit",
    "ImageHit",
    "SearchProviderError",
    "SearchProviderUnavailableError",
    "SearchProviderInterface",
    "TavilySearchProvider",
    "UnifiedSearchService",
    "unified_search_service",
    "APPROVED_SAP_DOMAINS",
]
