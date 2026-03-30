"""
Bottom-up Recognition System
Matches user input against knowledge base instead of generating from scratch.
Wolfy AI-inspired grounding approach.
"""

import json
import random
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher
from .resource_paths import get_resource_root


class RecognitionEngine:
    """
    Grounded retrieval system that matches input to knowledge base.
    Falls back to generative model only when no match is found.
    """
    
    def __init__(self, kb_path=None):
        if kb_path is None:
            kb_path = get_resource_root() / "data" / "knowledge_base.json"
        
        self.kb_path = kb_path
        self.knowledge_base = self._load_kb()
        self.confidence_threshold = 0.6  # Minimum match confidence
    
    def _load_kb(self):
        """Load knowledge base from JSON."""
        try:
            with open(self.kb_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load knowledge base: {e}")
            return {}
    
    def _similarity(self, text1, text2):
        """Calculate similarity between two strings."""
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    def _intent_override(self, user_input_lower):
        """Force-match certain intents regardless of phrasing."""
        capability_phrases = [
            "what can you do",
            "what all can you do",
            "what all you can do",
            "what can u do",
            "what can shadow ai do",
            "what can shadow ai do for me",
            "what all can shadow ai do",
            "what can shadow do",
            "what can shadow do for me",
            "what all can shadow do",
            "capabilities",
            "features",
            "what are you capable of",
            "how can you help",
            "what do you do"
        ]
        if any(p in user_input_lower for p in capability_phrases):
            return "capabilities", 1.0
        return None, 0.0
    
    def _match_pattern(self, user_input):
        """
        Find best matching pattern in knowledge base.
        Returns (category, confidence) or (None, 0) if no match.
        """
        user_input_lower = user_input.lower().strip()
        best_match = None
        best_confidence = 0
        
        for category, data in self.knowledge_base.items():
            patterns = data.get("patterns", [])
            
            for pattern in patterns:
                # Check for exact substring match
                if pattern in user_input_lower:
                    confidence = 1.0
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = category
                
                # Check for fuzzy match
                else:
                    similarity = self._similarity(user_input_lower, pattern)
                    if similarity > best_confidence and similarity >= self.confidence_threshold:
                        best_confidence = similarity
                        best_match = category
        
        return best_match, best_confidence
    
    def _resolve_dynamic(self, response, enhanced_learning=None):
        """Resolve dynamic placeholders like DYNAMIC:TIME."""
        if response == "DYNAMIC:TIME":
            return datetime.now().strftime("%I:%M %p")
        elif response == "DYNAMIC:DATE":
            return datetime.now().strftime("%B %d, %Y")
        elif response == "DYNAMIC:LEARNING_STATS" and enhanced_learning:
            return enhanced_learning.get_summary("detailed")
        elif response == "DYNAMIC:RESET_LEARNING" and enhanced_learning:
            enhanced_learning.reset_learning()
            return "All learned knowledge has been cleared. We start fresh!"
        return response
    
    def recognize(self, user_input, enhanced_learning=None):
        """
        Attempt to recognize user input and retrieve response.
        
        Returns:
            (response, confidence, matched_category) if match found
            (None, 0, None) if no match (should fall back to generation)
        """
        user_input_lower = user_input.lower().strip()
        override_category, override_confidence = self._intent_override(user_input_lower)
        if override_category:
            responses = self.knowledge_base.get(override_category, {}).get("responses", [])
            if responses:
                response = random.choice(responses)
                response = self._resolve_dynamic(response, enhanced_learning)
                return response, override_confidence, override_category
        
        category, confidence = self._match_pattern(user_input)
        
        if category is None:
            return None, 0, None
        
        # Get random response from category
        responses = self.knowledge_base[category].get("responses", [])
        if not responses:
            return None, 0, None
        
        response = random.choice(responses)
        response = self._resolve_dynamic(response, enhanced_learning)
        
        return response, confidence, category
    
    def add_entry(self, category, patterns, responses):
        """Add new entry to knowledge base."""
        self.knowledge_base[category] = {
            "patterns": patterns,
            "responses": responses
        }
        self._save_kb()
    
    def _save_kb(self):
        """Save knowledge base to disk."""
        try:
            with open(self.kb_path, 'w') as f:
                json.dump(self.knowledge_base, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save knowledge base: {e}")
