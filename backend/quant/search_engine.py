"""
Search Engine - Fallback for AI Assistant
Fetches web search results when Gemini is disabled.
"""
import httpx
from bs4 import BeautifulSoup
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

async def search_duckduckgo(query: str, limit: int = 5) -> List[Dict]:
    """
    Perform a raw web search using DuckDuckGo HTML version.
    Returns list of dictionaries with title, link, snippet.
    """
    try:
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
        }
        data = {"q": query}
        
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, data=data, headers=headers)
            
        if response.status_code != 200:
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        results = []
        for result in soup.find_all('div', class_='result'):
            try:
                title_tag = result.find('a', class_='result__a')
                if not title_tag:
                    continue
                    
                title = title_tag.get_text(strip=True)
                link = title_tag['href']
                
                snippet_tag = result.find('a', class_='result__snippet')
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
                
                results.append({
                    "title": title,
                    "link": link,
                    "snippet": snippet
                })
                
                if len(results) >= limit:
                    break
            except Exception:
                continue
                
        return results

    except Exception as e:
        logger.error(f"Search failed: {e}")
        return []

async def perform_smart_search(query: str) -> str:
    """
    Perform a web search and format results as a smart response.
    """
    try:
        results = await search_duckduckgo(query, limit=5)
        
        if not results:
            return f"I searched for '**{query}**' but couldn't find any relevant results."
            
        # Format response
        response_text = f"Here are the top results for '**{query}**':\n\n"
        
        for i, res in enumerate(results, 1):
            response_text += f"{i}. **[{res['title']}]({res['link']})**\n"
            response_text += f"   {res['snippet']}\n\n"
            
        response_text += "\n*Powered by Smart Search*"
        
        return response_text

    except Exception as e:
        logger.error(f"Search failed: {e}")
        return f"I encountered an error while searching: {str(e)}"
