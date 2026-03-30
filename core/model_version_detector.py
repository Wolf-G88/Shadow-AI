"""
Automatic Model Version Detection for Shadow AI
Detects model versions from API responses when not explicitly provided.
"""

import re
import json
from typing import Dict, Optional, Tuple


class ModelVersionDetector:
    """
    Automatic model version detection across all API providers.
    Inspects headers, metadata, and capability signatures.
    """
    
    # Known capability signatures for version inference
    CAPABILITY_SIGNATURES = {
        "openai": {
            "gpt-4-turbo": {"max_tokens": 128000, "vision": True},
            "gpt-4": {"max_tokens": 8192, "vision": False},
            "gpt-3.5-turbo": {"max_tokens": 16385, "vision": False},
        },
        "gemini": {
            "gemini-1.5-pro": {"max_tokens": 2000000, "thinking_mode": True},
            "gemini-1.5-flash": {"max_tokens": 1000000, "thinking_mode": True},
            "gemini-pro": {"max_tokens": 32000, "thinking_mode": False},
        },
        "claude": {
            "claude-3-opus": {"max_tokens": 200000, "extended_thinking": True},
            "claude-3-sonnet": {"max_tokens": 200000, "extended_thinking": False},
            "claude-2": {"max_tokens": 100000, "extended_thinking": False},
        }
    }
    
    # Header patterns to check
    HEADER_PATTERNS = [
        "x-model-version",
        "x-api-version",
        "x-model-id",
        "openai-model",
        "x-request-id",
    ]
    
    def __init__(self):
        self.detected_versions = {}  # Cache detected versions
    
    def detect_from_response(
        self, 
        provider: str, 
        response_data: Dict, 
        headers: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Main detection method.
        
        Args:
            provider: API provider name (openai, gemini, claude, etc.)
            response_data: API response JSON
            headers: HTTP response headers (if available)
        
        Returns:
            Detected model version string or None
        """
        # Try header detection first
        if headers:
            version = self._detect_from_headers(headers)
            if version:
                self.detected_versions[provider] = version
                return version
        
        # Try metadata detection
        version = self._detect_from_metadata(provider, response_data)
        if version:
            self.detected_versions[provider] = version
            return version
        
        # Try capability signature detection
        version = self._detect_from_capabilities(provider, response_data)
        if version:
            self.detected_versions[provider] = version
            return version
        
        # Check cache
        if provider in self.detected_versions:
            return self.detected_versions[provider]
        
        return None
    
    def _detect_from_headers(self, headers: Dict) -> Optional[str]:
        """Detect version from HTTP response headers."""
        for pattern in self.HEADER_PATTERNS:
            for header_key, header_value in headers.items():
                if pattern.lower() in header_key.lower():
                    # Extract version from header value
                    version = self._extract_version_string(header_value)
                    if version:
                        return version
        return None
    
    def _detect_from_metadata(self, provider: str, response_data: Dict) -> Optional[str]:
        """Detect version from API response metadata."""
        # OpenAI format
        if "model" in response_data:
            return response_data["model"]
        
        # Gemini format
        if "candidates" in response_data:
            # Check for model field in candidates
            for candidate in response_data.get("candidates", []):
                if "model" in candidate:
                    return candidate["model"]
        
        # Claude format
        if "type" in response_data and "model" in response_data:
            return response_data["model"]
        
        # Generic metadata check
        metadata_keys = ["model_version", "version", "model_name", "engine"]
        for key in metadata_keys:
            if key in response_data:
                return str(response_data[key])
        
        return None
    
    def _detect_from_capabilities(self, provider: str, response_data: Dict) -> Optional[str]:
        """Detect version from capability signatures."""
        if provider not in self.CAPABILITY_SIGNATURES:
            return None
        
        # Extract capabilities from response
        capabilities = self._extract_capabilities(response_data)
        
        # Match against known signatures
        for model_name, signature in self.CAPABILITY_SIGNATURES[provider].items():
            if self._matches_signature(capabilities, signature):
                return model_name
        
        return None
    
    def _extract_capabilities(self, response_data: Dict) -> Dict:
        """Extract capability information from response."""
        capabilities = {}
        
        # Check for usage info (token limits)
        if "usage" in response_data:
            usage = response_data["usage"]
            capabilities["max_tokens"] = usage.get("total_tokens", 0)
        
        # Check for vision/multimodal support
        if "candidates" in response_data:
            for candidate in response_data.get("candidates", []):
                content = candidate.get("content", {})
                if "parts" in content:
                    for part in content["parts"]:
                        if "inline_data" in part or "file_data" in part:
                            capabilities["vision"] = True
        
        # Check for thinking/reasoning mode
        if "thinking" in response_data or "reasoning_content" in response_data:
            capabilities["thinking_mode"] = True
        
        return capabilities
    
    def _matches_signature(self, capabilities: Dict, signature: Dict) -> bool:
        """Check if capabilities match a known signature."""
        for key, expected_value in signature.items():
            if key not in capabilities:
                continue
            
            actual_value = capabilities[key]
            
            # For numeric values, allow some tolerance
            if isinstance(expected_value, int) and isinstance(actual_value, int):
                if abs(actual_value - expected_value) > expected_value * 0.1:
                    return False
            elif actual_value != expected_value:
                return False
        
        return True
    
    def _extract_version_string(self, text: str) -> Optional[str]:
        """Extract version string from text."""
        # Match version patterns like "v1", "v1.5", "2024-01", "gpt-4-turbo"
        patterns = [
            r'v?\d+\.\d+(?:\.\d+)?',  # v1.5, 1.5.0
            r'gpt-[^/\s]+',            # gpt-4-turbo
            r'claude-[^/\s]+',         # claude-3-opus
            r'gemini-[^/\s]+',         # gemini-1.5-pro
            r'\d{4}-\d{2}',            # 2024-01
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        
        return None
    
    def get_cached_version(self, provider: str) -> Optional[str]:
        """Get cached version for provider."""
        return self.detected_versions.get(provider)
    
    def clear_cache(self):
        """Clear version cache."""
        self.detected_versions.clear()
    
    def infer_version_from_endpoint(self, endpoint: str) -> Optional[str]:
        """Infer version from API endpoint URL."""
        # Extract version from URL path
        # e.g., "https://api.openai.com/v1/chat" -> "v1"
        version = self._extract_version_string(endpoint)
        return version


# Global detector instance
_detector = ModelVersionDetector()


def detect_model_version(
    provider: str, 
    response_data: Dict, 
    headers: Optional[Dict] = None
) -> Optional[str]:
    """
    Convenience function for model version detection.
    
    Args:
        provider: API provider name
        response_data: API response JSON
        headers: HTTP response headers
    
    Returns:
        Detected model version or None
    """
    return _detector.detect_from_response(provider, response_data, headers)


def get_cached_version(provider: str) -> Optional[str]:
    """Get cached version for provider."""
    return _detector.get_cached_version(provider)


def clear_version_cache():
    """Clear version cache."""
    _detector.clear_cache()
