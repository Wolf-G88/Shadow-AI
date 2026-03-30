"""
External Bridge Module
Provides fallback to internet resources when local recognition fails.
Only activates when: 1) Internet available, 2) Low confidence match
"""

import socket
import requests
import re
from typing import Optional, Tuple, List
from concurrent.futures import ThreadPoolExecutor, as_completed


class ExternalBridge:
    """
    Conditional handoff to external resources.
    Offline-first: only uses internet as last resort.
    """
    
    def __init__(self, dns_server="1.1.1.1"):
        self.internet_available = None  # Lazy check
        self.fallback_enabled = True  # Can be disabled for pure offline mode
        self.timeout = 5  # seconds per source (increased for Wikipedia)
        self.max_workers = 3  # Parallel search workers
        self.dns_server = dns_server  # Configurable DNS (Cloudflare by default, fallback to 8.8.8.8)
    
    def check_internet(self, force_recheck=False) -> bool:
        """
        Check internet connectivity with fast DNS lookup.
        Caches result to avoid repeated checks.
        """
        if self.internet_available is not None and not force_recheck:
            return self.internet_available
        
        dns_servers = [self.dns_server, "8.8.8.8", "1.0.0.1"]
        for dns_ip in dns_servers:
            try:
                socket.create_connection((dns_ip, 53), timeout=self.timeout)
                self.internet_available = True
                return True
            except (socket.timeout, socket.error):
                continue
        self.internet_available = False
        return False
    
    def should_reach_out(self, confidence: float, threshold: float = 0.3) -> bool:
        """
        Decide if external fallback should be used.
        
        Args:
            confidence: Recognition confidence (0-1)
            threshold: Minimum confidence to stay local
        
        Returns:
            True if should use external resources
        """
        if not self.fallback_enabled:
            return False
        
        if confidence >= threshold:
            return False
        
        return self.check_internet()
    
    def search_duckduckgo(self, query: str) -> Optional[Tuple[str, str]]:
        """
        Use DuckDuckGo instant answer API (no key required).
        Returns (answer, source) or None.
        """
        try:
            url = "https://api.duckduckgo.com/"
            params = {
                "q": query,
                "format": "json",
                "no_html": 1,
                "skip_disambig": 1
            }
            
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            # Try different answer fields
            answer = data.get("AbstractText") or data.get("Answer") or data.get("Definition")
            
            if answer and len(answer.strip()) > 10:
                return (answer[:500], "DuckDuckGo")
            
            return None
        except Exception:
            return None
    
    def search_wikipedia(self, query: str) -> Optional[Tuple[str, str]]:
        """
        Search Wikipedia for factual information.
        Returns (answer, source) or None.
        """
        try:
            url = "https://en.wikipedia.org/w/api.php"
            params = {
                "action": "query",
                "format": "json",
                "prop": "extracts",
                "exintro": True,
                "explaintext": True,
                "titles": query,
                "redirects": 1
            }
            
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            pages = data.get("query", {}).get("pages", {})
            for page_id, page_data in pages.items():
                if page_id != "-1" and "extract" in page_data:
                    extract = page_data["extract"]
                    if len(extract.strip()) > 20:
                        # Get first paragraph
                        first_para = extract.split("\n\n")[0]
                        return (first_para[:500], "Wikipedia")
            
            return None
        except Exception:
            return None
    
    def search_brave(self, query: str) -> Optional[Tuple[str, str]]:
        """
        Search Brave Search API (requires free API key).
        Returns (answer, source) or None.
        """
        # Brave requires API key - skip if not configured
        # This is a placeholder for future implementation
        return None
    
    def _optimize_query(self, query: str) -> str:
        """Extract main subject from query for better search results."""
        # Remove common question words
        cleaned = re.sub(r'\b(what|when|where|who|why|how|is|was|are|were|the|a|an|did|do|does)\b', '', query, flags=re.IGNORECASE)
        # Remove punctuation
        cleaned = re.sub(r'[?!.,]', '', cleaned)
        # Get words
        words = cleaned.split()
        
        if not words:
            return query
        
        # Extract first meaningful noun (usually the subject)
        # Remove verbs like 'first', 'built', 'made', etc
        meaningful = [w for w in words if w.lower() not in ['first', 'built', 'made', 'created', 'founded', 'started']]
        
        if meaningful:
            # Return first 1-2 words (the main subject)
            return ' '.join(meaningful[:2]).title()
        
        return words[0].title()
    
    def get_external_response(self, user_input: str) -> Tuple[Optional[str], str]:
        """
        Parallel search mesh: race multiple sources, first valid response wins.
        
        Returns:
            (response, source) or (None, "none")
        """
        if not self.check_internet():
            return None, "none"
        
        # Optimize query for better search results
        optimized = self._optimize_query(user_input)
        print(f"[ExternalBridge] Original: '{user_input[:50]}...'", flush=True)
        print(f"[ExternalBridge] Optimized: '{optimized}'", flush=True)
        print(f"[ExternalBridge] Racing search sources...", flush=True)
        
        # Define search functions to race - try both original and optimized
        search_functions = [
            ("Wikipedia", lambda: self.search_wikipedia(optimized) or self.search_wikipedia(user_input)),
            ("DuckDuckGo", lambda: self.search_duckduckgo(optimized) or self.search_duckduckgo(user_input)),
            # ("Brave", lambda: self.search_brave(user_input)),  # Uncomment if API key added
        ]
        
        # Race all sources in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all searches
            future_to_source = {executor.submit(func): name for name, func in search_functions}
            
            # Return first valid result
            for future in as_completed(future_to_source):
                source_name = future_to_source[future]
                try:
                    result = future.result()
                    if result:  # (answer, source) tuple
                        answer, source = result
                        print(f"[ExternalBridge] Winner: {source} responded first", flush=True)
                        # Cancel remaining futures
                        for f in future_to_source:
                            f.cancel()
                        return answer, source
                except Exception as e:
                    print(f"[ExternalBridge] {source_name} failed: {e}", flush=True)
        
        print(f"[ExternalBridge] All sources returned empty", flush=True)
        return None, "none"
    
    def format_external_response(self, answer: str, source: str) -> str:
        """Format external answer with attribution."""
        return f"{answer}\n\n(Source: {source})"
    
    def get_idk_response(self) -> str:
        """Response when no match found and no internet."""
        return "I don't have that information in my knowledge base, and I can't reach external sources right now. Try rephrasing or ask something else."
