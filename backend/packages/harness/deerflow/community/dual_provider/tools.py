"""
Dual-Provider Web Search Tool
Primary: InfoQuest/BytePlus
Fallback: Tavily

This tool automatically uses InfoQuest first, and falls back to Tavily if InfoQuest fails.
"""

import json
import logging
from typing import Dict

from deerflow.community.infoquest.tools import InfoQuestClient
from deerflow.community.tavily.tools import TavilyClient
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


class DualProviderSearchClient:
    """Web search client that uses InfoQuest as primary and Tavily as fallback"""

    def __init__(self):
        self.infoquest = None
        self.tavily = None
        self.stats = {
            "infoquest_success": 0,
            "infoquest_failure": 0,
            "tavily_fallback": 0,
            "tavily_failure": 0
        }

        # Initialize InfoQuest (primary)
        try:
            self.infoquest = InfoQuestClient()
            logger.info("✅ InfoQuest client initialized (PRIMARY)")
        except Exception as e:
            logger.warning(f"⚠️ InfoQuest initialization failed: {e}")

        # Initialize Tavily (fallback)
        try:
            self.tavily = TavilyClient()
            logger.info("✅ Tavily client initialized (FALLBACK)")
        except Exception as e:
            logger.warning(f"⚠️ Tavily initialization failed: {e}")

    def web_search(self, query: str, max_results: int = 5) -> str:
        """
        Search the web using InfoQuest first, fallback to Tavily if needed
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            JSON string with search results
        """
        # Try InfoQuest first (primary)
        if self.infoquest:
            try:
                logger.info(f"🔍 Searching with InfoQuest (primary): {query}")
                result = self.infoquest.web_search(query)
                # InfoQuest returns JSON, parse and limit results if needed
                import json
                results_list = json.loads(result)
                if len(results_list) > max_results:
                    results_list = results_list[:max_results]
                    result = json.dumps(results_list, ensure_ascii=False, indent=2)
                self.stats["infoquest_success"] += 1
                logger.info("✅ InfoQuest search successful")
                return result
            except Exception as e:
                logger.warning(f"⚠️ InfoQuest search failed: {e}")
                self.stats["infoquest_failure"] += 1

        # Fallback to Tavily
        if self.tavily:
            try:
                logger.info(f"🔄 Falling back to Tavily: {query}")
                result = self.tavily.search(query, max_results=max_results)
                self.stats["tavily_fallback"] += 1
                logger.info("✅ Tavily fallback successful")

                # Normalize Tavily result format to match InfoQuest
                if isinstance(result, dict) and "results" in result:
                    normalized = []
                    for item in result["results"]:
                        normalized.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "snippet": item.get("content", ""),
                            "type": "page"
                        })
                    return json.dumps(normalized, ensure_ascii=False, indent=2)
                return result
            except Exception as e:
                logger.error(f"❌ Tavily fallback also failed: {e}")
                self.stats["tavily_failure"] += 1

        # Both providers failed
        raise Exception(
            "Both InfoQuest and Tavily search providers failed. "
            "Please check API keys and network connectivity."
        )

    def get_stats(self) -> Dict[str, int]:
        """Get usage statistics"""
        return self.stats.copy()


# Global client instance
_dual_client = None


def get_dual_client() -> DualProviderSearchClient:
    """Get or create the dual provider client singleton"""
    global _dual_client
    if _dual_client is None:
        _dual_client = DualProviderSearchClient()
    return _dual_client


@tool
def web_search_dual(query: str) -> str:
    """
    Search the web using dual-provider setup (InfoQuest primary, Tavily fallback).
    
    This tool automatically uses InfoQuest as the primary search provider and falls
    back to Tavily if InfoQuest fails or is unavailable. This ensures maximum
    reliability while optimizing for cost and free tier usage.
    
    Args:
        query: The search query string
        
    Returns:
        JSON string containing search results with title, url, snippet, and type
        
    Example:
        >>> result = web_search_dual("latest AI news")
        >>> # Returns: [{"title": "...", "url": "...", "snippet": "...", "type": "page"}, ...]
    """
    client = get_dual_client()
    return client.web_search(query)


@tool
def web_fetch_dual(url: str) -> str:
    """
    Fetch and extract content from a URL using dual-provider setup.
    
    Tries InfoQuest first, falls back to Tavily if needed.
    
    Args:
        url: The URL to fetch content from
        
    Returns:
        Extracted text content from the webpage
    """
    client = get_dual_client()

    # Try InfoQuest first
    if client.infoquest:
        try:
            logger.info(f"📄 Fetching with InfoQuest: {url}")
            result = client.infoquest.web_fetch(url)
            logger.info("✅ InfoQuest fetch successful")
            return result
        except Exception as e:
            logger.warning(f"⚠️ InfoQuest fetch failed: {e}")

    # Fallback to Tavily
    if client.tavily:
        try:
            logger.info(f"🔄 Falling back to Tavily for fetch: {url}")
            result = client.tavily.extract(url)
            logger.info("✅ Tavily fetch successful")
            return result
        except Exception as e:
            logger.error(f"❌ Tavily fetch also failed: {e}")

    raise Exception(f"Failed to fetch content from {url} using both providers")


@tool
def web_search_stats() -> str:
    """
    Get usage statistics for the dual-provider search system.
    
    Returns:
        JSON string with usage counts for each provider
    """
    client = get_dual_client()
    stats = client.get_stats()
    return json.dumps(stats, indent=2)


# Export tools
__all__ = ['web_search_dual', 'web_fetch_dual', 'web_search_stats']
