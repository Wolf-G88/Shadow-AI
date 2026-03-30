"""
Tone Analysis Engine - Extracts user communication style
SILS v1 - Shadow Intelligence Layer
"""

import re
import numpy as np
from typing import Dict, List


class ToneAnalyzer:
    """
    Extract user's communication style into a 64-dimensional embedding.
    
    Features:
    - Warmth (lexical softness, hedges, friendliness markers)
    - Directness (sentence length, command frequency)
    - Profanity level (normalized count)
    - Punctuation style (ellipses, exclamation, commas)
    - Emotional tone (sentiment)
    - Rhythm (short/long alternation)
    """
    
    def __init__(self):
        # Feature extractors
        self.warmth_markers = [
            'please', 'thanks', 'thank you', 'appreciate', 'grateful',
            'kindly', 'wonderful', 'great', 'awesome', 'nice', 'lovely'
        ]
        
        self.hedges = [
            'maybe', 'perhaps', 'probably', 'possibly', 'kinda', 'sorta',
            'somewhat', 'rather', 'fairly', 'quite', 'relatively', 'might'
        ]
        
        self.profanity_words = [
            'damn', 'hell', 'crap', 'shit', 'fuck', 'ass', 'bitch'
        ]
        
        self.emotional_positive = [
            'love', 'happy', 'joy', 'excited', 'amazing', 'wonderful',
            'fantastic', 'excellent', 'perfect', 'brilliant'
        ]
        
        self.emotional_negative = [
            'hate', 'sad', 'angry', 'frustrated', 'terrible', 'awful',
            'horrible', 'worst', 'sucks', 'annoying'
        ]
    
    def analyze(self, text: str) -> np.ndarray:
        """
        Analyze text and return 64-dim style embedding.
        
        Args:
            text: User message
        
        Returns:
            style_embedding: (64,) numpy array
        """
        text_lower = text.lower()
        words = text_lower.split()
        
        # Extract features
        features = []
        
        # 1. Warmth features (8 dims)
        features.extend(self._extract_warmth(text_lower, words))
        
        # 2. Directness features (8 dims)
        features.extend(self._extract_directness(text, words))
        
        # 3. Profanity features (8 dims)
        features.extend(self._extract_profanity(words))
        
        # 4. Punctuation features (16 dims)
        features.extend(self._extract_punctuation(text))
        
        # 5. Emotional features (16 dims)
        features.extend(self._extract_emotion(words))
        
        # 6. Rhythm features (8 dims)
        features.extend(self._extract_rhythm(text))
        
        # Convert to numpy array and normalize
        embedding = np.array(features, dtype=np.float32)
        
        # Normalize to [-1, 1] range
        embedding = np.tanh(embedding)
        
        return embedding
    
    def _extract_warmth(self, text: str, words: List[str]) -> List[float]:
        """Extract warmth/friendliness features (8 dims)."""
        features = []
        
        # Warmth marker count
        warmth_count = sum(1 for marker in self.warmth_markers if marker in text)
        features.append(warmth_count / 10.0)  # Normalize
        
        # Hedge word count
        hedge_count = sum(1 for hedge in self.hedges if hedge in words)
        features.append(hedge_count / 5.0)
        
        # Politeness markers (please, thank you)
        politeness = int('please' in text or 'thank' in text)
        features.append(float(politeness))
        
        # Softeners (just, a bit, a little)
        softeners = ['just', 'bit', 'little']
        softener_count = sum(1 for s in softeners if s in words)
        features.append(softener_count / 3.0)
        
        # Question form (more indirect/warm)
        has_question = int('?' in text)
        features.append(float(has_question))
        
        # Personal pronouns (I, we - more personal/warm)
        personal = ['i', 'we', 'my', 'our']
        personal_count = sum(1 for p in personal if p in words)
        features.append(personal_count / 4.0)
        
        # Emoji presence (warmth indicator)
        emoji_count = len(re.findall(r'[😀-🙏]', text))
        features.append(min(emoji_count / 3.0, 1.0))
        
        # Average warmth score
        avg_warmth = np.mean(features)
        features.append(avg_warmth)
        
        return features
    
    def _extract_directness(self, text: str, words: List[str]) -> List[float]:
        """Extract directness features (8 dims)."""
        features = []
        
        # Sentence length (shorter = more direct)
        word_count = len(words)
        directness_score = 1.0 / (1.0 + word_count / 10.0)
        features.append(directness_score)
        
        # Imperative mood (command verbs)
        command_verbs = ['do', 'make', 'get', 'give', 'show', 'tell', 'open', 'close']
        starts_with_command = int(words[0] in command_verbs if words else 0)
        features.append(float(starts_with_command))
        
        # No hedging (direct)
        no_hedges = 1.0 - min(sum(1 for h in self.hedges if h in words) / 5.0, 1.0)
        features.append(no_hedges)
        
        # Declarative sentences (ends with period, not question)
        is_declarative = int(text.strip().endswith('.'))
        features.append(float(is_declarative))
        
        # Lack of qualifiers
        qualifiers = ['very', 'really', 'somewhat', 'quite', 'rather']
        qualifier_absence = 1.0 - min(sum(1 for q in qualifiers if q in words) / 3.0, 1.0)
        features.append(qualifier_absence)
        
        # Use of "you" (direct address)
        you_count = words.count('you')
        features.append(min(you_count / 2.0, 1.0))
        
        # Short paragraphs (no multiple sentences)
        sentence_count = len(re.split(r'[.!?]', text))
        single_sentence = 1.0 if sentence_count <= 2 else 0.5
        features.append(single_sentence)
        
        # Average directness
        avg_directness = np.mean(features)
        features.append(avg_directness)
        
        return features
    
    def _extract_profanity(self, words: List[str]) -> List[float]:
        """Extract profanity features (8 dims)."""
        features = []
        
        # Profanity count
        profanity_count = sum(1 for word in words if word in self.profanity_words)
        features.append(min(profanity_count / 3.0, 1.0))
        
        # Profanity ratio
        if len(words) > 0:
            profanity_ratio = profanity_count / len(words)
            features.append(profanity_ratio * 10.0)  # Amplify small values
        else:
            features.append(0.0)
        
        # Strong profanity (f-word, etc.)
        strong_profanity = sum(1 for word in words if word in ['fuck', 'shit'])
        features.append(min(strong_profanity / 2.0, 1.0))
        
        # Mild profanity
        mild_profanity = sum(1 for word in words if word in ['damn', 'hell', 'crap'])
        features.append(min(mild_profanity / 2.0, 1.0))
        
        # All caps (aggressive tone)
        all_caps_words = sum(1 for word in words if word.isupper() and len(word) > 1)
        features.append(min(all_caps_words / 3.0, 1.0))
        
        # Fill remaining dims with profanity-related features
        features.extend([profanity_count > 0, profanity_ratio, np.mean(features)])
        
        return features[:8]
    
    def _extract_punctuation(self, text: str) -> List[float]:
        """Extract punctuation style (16 dims)."""
        features = []
        
        # Ellipses count
        ellipses = len(re.findall(r'\.\.\.+', text))
        features.append(min(ellipses / 3.0, 1.0))
        
        # Exclamation marks
        exclamations = text.count('!')
        features.append(min(exclamations / 3.0, 1.0))
        
        # Question marks
        questions = text.count('?')
        features.append(min(questions / 2.0, 1.0))
        
        # Comma frequency
        commas = text.count(',')
        features.append(min(commas / 5.0, 1.0))
        
        # Semicolons (formal)
        semicolons = text.count(';')
        features.append(min(semicolons / 2.0, 1.0))
        
        # Dashes (casual breaks)
        dashes = text.count('-') + text.count('—')
        features.append(min(dashes / 3.0, 1.0))
        
        # Parentheses (asides)
        parentheses = text.count('(') + text.count(')')
        features.append(min(parentheses / 4.0, 1.0))
        
        # Quotes
        quotes = text.count('"') + text.count("'")
        features.append(min(quotes / 4.0, 1.0))
        
        # Multiple punctuation (e.g., "!!!", "??")
        multi_punct = len(re.findall(r'[!?]{2,}', text))
        features.append(min(multi_punct / 2.0, 1.0))
        
        # Period frequency
        periods = text.count('.')
        features.append(min(periods / 3.0, 1.0))
        
        # Mixed punctuation (!?, ?!)
        mixed = len(re.findall(r'[!?]+', text))
        features.append(min(mixed / 2.0, 1.0))
        
        # Punctuation density
        punct_density = len(re.findall(r'[.,!?;:\-—]', text)) / max(len(text), 1)
        features.append(min(punct_density * 10, 1.0))
        
        # Fill remaining
        while len(features) < 16:
            features.append(np.mean(features))
        
        return features[:16]
    
    def _extract_emotion(self, words: List[str]) -> List[float]:
        """Extract emotional tone (16 dims)."""
        features = []
        
        # Positive emotion count
        pos_count = sum(1 for word in words if word in self.emotional_positive)
        features.append(min(pos_count / 3.0, 1.0))
        
        # Negative emotion count
        neg_count = sum(1 for word in words if word in self.emotional_negative)
        features.append(min(neg_count / 3.0, 1.0))
        
        # Sentiment polarity (positive - negative)
        sentiment = (pos_count - neg_count) / max(len(words), 1)
        features.append(np.tanh(sentiment * 5))  # Normalized
        
        # Intensity markers (very, extremely, so)
        intensity = ['very', 'extremely', 'so', 'really', 'super', 'incredibly']
        intensity_count = sum(1 for i in intensity if i in words)
        features.append(min(intensity_count / 3.0, 1.0))
        
        # Emotional verbs
        emotion_verbs = ['feel', 'think', 'believe', 'hope', 'wish', 'want']
        emotion_verb_count = sum(1 for v in emotion_verbs if v in words)
        features.append(min(emotion_verb_count / 3.0, 1.0))
        
        # Certainty (absolutely, definitely, certainly)
        certainty_words = ['absolutely', 'definitely', 'certainly', 'surely']
        certainty_count = sum(1 for c in certainty_words if c in words)
        features.append(min(certainty_count / 2.0, 1.0))
        
        # Uncertainty (might, maybe, perhaps)
        uncertainty_count = sum(1 for h in self.hedges if h in words)
        features.append(min(uncertainty_count / 3.0, 1.0))
        
        # Fill remaining
        while len(features) < 16:
            features.append(np.mean(features))
        
        return features[:16]
    
    def _extract_rhythm(self, text: str) -> List[float]:
        """Extract rhythm features (8 dims)."""
        sentences = re.split(r'[.!?]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        features = []
        
        if len(sentences) == 0:
            return [0.0] * 8
        
        # Sentence length variation
        lengths = [len(s.split()) for s in sentences]
        if len(lengths) > 1:
            length_std = np.std(lengths)
            features.append(min(length_std / 5.0, 1.0))
        else:
            features.append(0.0)
        
        # Average sentence length
        avg_length = np.mean(lengths) if lengths else 0
        features.append(min(avg_length / 15.0, 1.0))
        
        # Short sentence ratio
        short_ratio = sum(1 for l in lengths if l < 5) / len(lengths)
        features.append(short_ratio)
        
        # Long sentence ratio
        long_ratio = sum(1 for l in lengths if l > 15) / len(lengths)
        features.append(long_ratio)
        
        # Alternation (short-long-short pattern)
        if len(lengths) > 2:
            alternation = sum(1 for i in range(len(lengths) - 2) 
                            if (lengths[i] < 8 and lengths[i+1] > 8) or 
                               (lengths[i] > 8 and lengths[i+1] < 8))
            features.append(min(alternation / len(lengths), 1.0))
        else:
            features.append(0.0)
        
        # Fill remaining
        while len(features) < 8:
            features.append(np.mean(features) if features else 0.0)
        
        return features[:8]
    
    def get_style_summary(self, text: str) -> Dict[str, float]:
        """
        Get human-readable style summary.
        
        Args:
            text: User message
        
        Returns:
            dict with style dimensions
        """
        embedding = self.analyze(text)
        
        # Average features by category
        warmth = float(np.mean(embedding[:8]))
        directness = float(np.mean(embedding[8:16]))
        profanity = float(np.mean(embedding[16:24]))
        punctuation = float(np.mean(embedding[24:40]))
        emotion = float(np.mean(embedding[40:56]))
        rhythm = float(np.mean(embedding[56:64]))
        
        return {
            'warmth': warmth,
            'directness': directness,
            'profanity': profanity,
            'punctuation_richness': punctuation,
            'emotional_intensity': emotion,
            'rhythm_variation': rhythm
        }
