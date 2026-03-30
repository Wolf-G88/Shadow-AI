"""
Router / Orchestrator - Decides which encoder to use
SILS v1 - Shadow Intelligence Layer
"""

import re
from typing import Dict, List, Tuple


class Router:
    """
    Intelligent router that decides which encoder mode to use for each message.
    
    Modes:
    - intent: Command/action-oriented messages (use GRU only)
    - tone: Conversational/emotional messages (use Transformer only)
    - hybrid: Mixed messages (use both + fusion)
    """
    
    def __init__(self, config):
        self.config = config
        self.command_keywords = config["router"]["command_keywords"]
        self.hybrid_threshold = config["router"]["hybrid_threshold"]
        
        # Additional patterns for detection
        self.command_patterns = [
            r'^\w+\s+\w+',  # Verb + noun (e.g., "open file", "delete folder")
            r'^(how do i|how to|show me)',  # Question patterns
            r'![\w]+',  # Shell command prefix
        ]
        
        self.conversational_indicators = [
            r'\?$',  # Questions
            r'!+$',  # Exclamations
            r'\.\.\.+',  # Ellipses
            r'[😀-🙏]',  # Emojis (unicode range)
            r'\b(feel|think|hope|wish|wonder)\b',  # Emotional verbs
            r'\b(maybe|perhaps|probably|kinda|sorta)\b',  # Hedging
        ]
    
    def route(self, message: str) -> Tuple[str, float]:
        """
        Determine which mode to use for a message.
        
        Args:
            message: User input text
        
        Returns:
            (mode, confidence)
            mode: 'intent', 'tone', or 'hybrid'
            confidence: 0.0 to 1.0
        """
        message_lower = message.lower().strip()
        
        # Calculate scores
        intent_score = self._calculate_intent_score(message_lower)
        tone_score = self._calculate_tone_score(message_lower)
        
        # Decision logic
        if intent_score > 0.7 and tone_score < 0.3:
            return 'intent', intent_score
        
        elif tone_score > 0.7 and intent_score < 0.3:
            return 'tone', tone_score
        
        elif abs(intent_score - tone_score) < self.hybrid_threshold:
            # Scores are close → hybrid mode
            confidence = (intent_score + tone_score) / 2
            return 'hybrid', confidence
        
        else:
            # Choose stronger signal
            if intent_score > tone_score:
                return 'intent', intent_score
            else:
                return 'tone', tone_score
    
    def _calculate_intent_score(self, message: str) -> float:
        """Calculate intent/command likelihood (0.0 to 1.0)."""
        score = 0.0
        
        # Check for command keywords
        for keyword in self.command_keywords:
            if message.startswith(keyword):
                score += 0.4
                break
        
        # Check for command patterns
        for pattern in self.command_patterns:
            if re.search(pattern, message):
                score += 0.3
                break
        
        # Short, imperative sentences
        word_count = len(message.split())
        if word_count <= 5:
            score += 0.2
        
        # Starts with verb
        words = message.split()
        if words and self._is_verb(words[0]):
            score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_tone_score(self, message: str) -> float:
        """Calculate conversational/emotional likelihood (0.0 to 1.0)."""
        score = 0.0
        
        # Check conversational indicators
        matches = 0
        for pattern in self.conversational_indicators:
            if re.search(pattern, message):
                matches += 1
        
        score += min(matches * 0.25, 0.75)
        
        # Longer, descriptive sentences
        word_count = len(message.split())
        if word_count > 15:
            score += 0.2
        elif word_count > 8:
            score += 0.1
        
        # Contains personal pronouns
        personal_pronouns = ['i', 'me', 'my', 'mine', 'we', 'us', 'our']
        if any(pronoun in message.split() for pronoun in personal_pronouns):
            score += 0.15
        
        return min(score, 1.0)
    
    def _is_verb(self, word: str) -> bool:
        """Simple heuristic to check if word is likely a verb."""
        # Common command verbs
        command_verbs = [
            'open', 'close', 'delete', 'create', 'make', 'set', 'get',
            'show', 'tell', 'give', 'find', 'search', 'run', 'execute',
            'start', 'stop', 'pause', 'resume', 'install', 'remove',
            'update', 'upgrade', 'configure', 'define', 'explain'
        ]
        
        return word in command_verbs
    
    def get_mode_distribution(self, messages: List[str]) -> Dict[str, float]:
        """
        Analyze mode distribution across multiple messages.
        
        Args:
            messages: List of user messages
        
        Returns:
            dict with mode percentages
        """
        mode_counts = {'intent': 0, 'tone': 0, 'hybrid': 0}
        
        for message in messages:
            mode, _ = self.route(message)
            mode_counts[mode] += 1
        
        total = len(messages)
        if total == 0:
            return mode_counts
        
        return {
            mode: count / total
            for mode, count in mode_counts.items()
        }
    
    def explain_routing(self, message: str) -> Dict:
        """
        Explain routing decision for debugging.
        
        Args:
            message: User input
        
        Returns:
            dict with scores, decision, and reasoning
        """
        message_lower = message.lower().strip()
        
        intent_score = self._calculate_intent_score(message_lower)
        tone_score = self._calculate_tone_score(message_lower)
        mode, confidence = self.route(message)
        
        reasoning = []
        
        # Intent reasoning
        if intent_score > 0:
            for keyword in self.command_keywords:
                if message_lower.startswith(keyword):
                    reasoning.append(f"Starts with command keyword: '{keyword}'")
            
            if len(message.split()) <= 5:
                reasoning.append("Short imperative sentence")
        
        # Tone reasoning
        if tone_score > 0:
            for pattern in self.conversational_indicators:
                if re.search(pattern, message_lower):
                    reasoning.append(f"Contains conversational pattern: {pattern}")
            
            if len(message.split()) > 15:
                reasoning.append("Long descriptive sentence")
        
        return {
            'message': message,
            'intent_score': intent_score,
            'tone_score': tone_score,
            'mode': mode,
            'confidence': confidence,
            'reasoning': reasoning
        }
