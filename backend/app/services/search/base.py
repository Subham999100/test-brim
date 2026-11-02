"""Shared Tavily result types and provider interface."""

from dataclasses import dataclass
from typing import List, Optional, Protocol


class SearchProviderError(Exception):
    """Base exception for search provider errors."""
    pass


class SearchProviderUnavailableError(SearchProviderError):
    """Raised when Tavily is not configured or unavailable."""
    pass


@dataclass
class SearchHit:
    """Normalized search result hit."""
    title: str
    url: str
    snippet: str
    raw_content: Optional[str] = None
    score: float = 0.0
    published_date: Optional[str] = None
    engine: Optional[str] = None


@dataclass
class ImageHit:
    """Normalized visual search hit."""
    url: str
    source_url: Optional[str] = None
    source_title: Optional[str] = None
    description: Optional[str] = None
    alt_text: Optional[str] = None
    thumbnail_url: Optional[str] = None
    resolution: Optional[str] = None
    img_format: Optional[str] = None


class SearchProviderInterface(Protocol):
    """Interface defining capabilities of search backends."""

    def search(
        self,
        query: str,
        *,
        max_results: int = 5,
        search_depth: str = "basic",
        topic: str = "general",
        time_range: Optional[str] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        include_raw_content: bool = True,
        include_images: bool = False,
    ) -> List[SearchHit]:
        ...

    def search_images(
        self,
        query: str,
        *,
        max_images: int = 4,
    ) -> List[ImageHit]:
        ...
