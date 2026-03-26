"""
Dual-provider web search with automatic fallback.
Primary: InfoQuest, Fallback: Tavily
"""

from .tools import (
    web_search_dual,
    web_fetch_dual,
    web_search_stats,
    get_dual_client
)

__all__ = [
    "web_search_dual",
    "web_fetch_dual", 
    "web_search_stats",
    "get_dual_client"
]
