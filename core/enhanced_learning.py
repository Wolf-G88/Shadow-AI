# Enhanced learning system for Shadow AI
# Combines Wolfy's structured learning backbone with expanded context comprehension
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import threading
import re
import time
from .app_paths import get_enhanced_learning_dir

class EnhancedLearning:
    """
    Advanced learning system with:
    - Structured knowledge base (facts, skills, preferences, relationships)
    - Context comprehension across multiple learning sources
    - Natural language extraction and teaching detection
    - Automatic categorization and indexing
    - Persistent storage with backup
    """
    
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.data_dir = str(get_enhanced_learning_dir())
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Knowledge files
        self.knowledge_file = os.path.join(self.data_dir, f"{user_id}_knowledge.json")
        self.context_file = os.path.join(self.data_dir, f"{user_id}_context.json")
        self.relationships_file = os.path.join(self.data_dir, f"{user_id}_relationships.json")
        
        # Load existing knowledge
        self.knowledge = self.load_knowledge()
        self.context_map = self.load_context_map()
        self.relationships = self.load_relationships()
        
        # Thread safety
        self.lock = threading.Lock()
        
        # Teaching triggers (from Wolfy + more)
        self.teaching_phrases = [
            "my name is", "i am", "i'm", "i work", "i live",
            "i prefer", "i like", "i love", "i hate", "i dislike",
            "remember that", "note that", "keep in mind", "learn this",
            "the fact is", "it's important that", "you should know"
        ]
        
        # Question patterns
        self.question_patterns = [
            r"what (is|are|was|were|do|does|did)",
            r"who (is|are|was|were|am|do|does)",
            r"where (is|are|was|were|do|does)",
            r"when (is|are|was|were|do|does|did)",
            r"why (is|are|was|were|do|does|did)",
            r"how (is|are|was|were|do|does|did|can|could|would)",
            r"(can|could|would|should|will) (you|i|we|they)"
        ]
        
        # Categories for automatic classification
        self.category_keywords = {
            'facts': ['is', 'are', 'was', 'were', 'has', 'have', 'contains', 'means'],
            'skills': ['can', 'able to', 'know how', 'expertise', 'proficient', 'skilled'],
            'preferences': ['prefer', 'like', 'love', 'favorite', 'enjoy', 'hate', 'dislike'],
            'relationships': ['my', 'our', 'family', 'friend', 'colleague', 'name', 'am', "i'm"]
        }
        
        # Stop words for relevance scoring (to avoid parroting on generic queries)
        self.stop_words = set([
            'a', 'an', 'the', 'and', 'or', 'but', 'if', 'then', 'else', 'so',
            'i', 'me', 'my', 'mine', 'we', 'our', 'ours', 'you', 'your', 'yours',
            'he', 'him', 'his', 'she', 'her', 'hers', 'they', 'them', 'their', 'theirs',
            'it', 'its', 'this', 'that', 'these', 'those',
            'all', 'any', 'anything', 'everything', 'something', 'stuff', 'things',
            'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'do', 'does', 'did', 'doing', 'done',
            'can', 'could', 'would', 'should', 'will', 'shall', 'may', 'might', 'must',
            'what', 'who', 'whom', 'whose', 'which', 'when', 'where', 'why', 'how',
            'help', 'please', 'tell', 'show', 'give', 'get', 'need', 'want', 'ask',
            'use', 'uses',
            'about', 'with', 'from', 'into', 'over', 'under', 'of', 'to', 'for', 'in', 'on', 'at'
        ])
        
        # Phrases that explicitly request learned knowledge
        self.learning_query_phrases = [
            'what did you learn', 'what have you learned', 'what all have you learned',
            'show me what you learned', 'tell me what you learned', 'learning stats',
            'what do you remember', 'do you remember', 'recall', 'remember'
        ]
    
    def load_knowledge(self) -> Dict:
        """Load structured knowledge base"""
        if os.path.exists(self.knowledge_file):
            try:
                with open(self.knowledge_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            'facts': {},
            'skills': {},
            'preferences': {},
            'relationships': {},
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat(),
                'total_items': 0
            }
        }
    
    def load_context_map(self) -> Dict:
        """Load context relationship map for connecting related knowledge"""
        if os.path.exists(self.context_file):
            try:
                with open(self.context_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            'topics': {},  # topic -> [related_facts]
            'entities': {},  # entity -> {type, facts, relationships}
            'temporal': {},  # time-based context
            'sources': {}  # source -> learned_items
        }
    
    def load_relationships(self) -> Dict:
        """Load relationship graph between knowledge items"""
        if os.path.exists(self.relationships_file):
            try:
                with open(self.relationships_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            'connections': {},  # item_id -> [connected_item_ids]
            'hierarchy': {},  # parent -> children
            'implications': {}  # fact -> [implied_facts]
        }
    
    def save_all(self):
        """Save all knowledge bases with thread safety"""
        with self.lock:
            try:
                # Update metadata
                self.knowledge['metadata']['last_updated'] = datetime.now().isoformat()
                self.knowledge['metadata']['total_items'] = sum(
                    len(self.knowledge[cat]) for cat in ['facts', 'skills', 'preferences', 'relationships']
                )
                
                # Save knowledge
                with open(self.knowledge_file, 'w') as f:
                    json.dump(self.knowledge, f, indent=2)
                
                # Save context map
                with open(self.context_file, 'w') as f:
                    json.dump(self.context_map, f, indent=2)
                
                # Save relationships
                with open(self.relationships_file, 'w') as f:
                    json.dump(self.relationships, f, indent=2)
                
                # Create backup
                self.create_backup()
            except Exception as e:
                print(f"Error saving enhanced learning data: {e}")
    
    def create_backup(self):
        """Create timestamped backup"""
        try:
            backup_dir = os.path.join(self.data_dir, 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(backup_dir, f"{self.user_id}_{timestamp}.json")
            
            backup_data = {
                'knowledge': self.knowledge,
                'context_map': self.context_map,
                'relationships': self.relationships
            }
            
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            # Keep only last 10 backups
            self.cleanup_old_backups(backup_dir, 10)
        except Exception as e:
            print(f"Error creating backup: {e}")
    
    def cleanup_old_backups(self, backup_dir: str, keep_count: int = 10):
        """Keep only the most recent backups"""
        try:
            backups = sorted([
                f for f in os.listdir(backup_dir)
                if f.startswith(self.user_id) and f.endswith('.json')
            ], reverse=True)
            
            for old_backup in backups[keep_count:]:
                os.remove(os.path.join(backup_dir, old_backup))
        except Exception as e:
            print(f"Error cleaning up backups: {e}")
    
    def detect_teaching(self, user_input: str) -> bool:
        """Detect if user is teaching (not asking a question)"""
        text_lower = user_input.lower().strip()
        
        # Skip questions
        if '?' in user_input:
            return False
        
        # Check for question patterns
        for pattern in self.question_patterns:
            if re.search(pattern, text_lower):
                return False
        
        # Check for teaching phrases
        for phrase in self.teaching_phrases:
            if phrase in text_lower:
                return True
        
        return False

    def is_question(self, text: str) -> bool:
        text_lower = text.lower().strip()
        if '?' in text:
            return True
        for pattern in self.question_patterns:
            if re.search(pattern, text_lower):
                return True
        return False
    
    def is_learning_query(self, text: str) -> bool:
        text_lower = text.lower().strip()
        if text_lower.startswith('/recall') or text_lower.startswith('/remember'):
            return True
        return any(phrase in text_lower for phrase in self.learning_query_phrases)
    
    def tokenize(self, text: str) -> List[str]:
        tokens = re.findall(r'\b[a-z0-9]+\b', text.lower())
        return [t for t in tokens if t not in self.stop_words]
    
    def extract_and_learn(self, user_input: str, source: str = "conversation",
                          learn_type: str = "explicit", answerable: bool = True) -> Optional[str]:
        """
        Extract knowledge from natural language and learn it.
        Returns feedback message if learned something, None otherwise.
        """
        if not self.detect_teaching(user_input):
            return None
        
        text_lower = user_input.lower().strip()
        learned = []
        
        # Extract name
        if 'my name is' in text_lower:
            # Split on lowercase version but preserve original case in result
            parts = text_lower.split('my name is', 1)
            # Find position in original string
            start_pos = user_input.lower().find('my name is') + len('my name is')
            name = user_input[start_pos:].strip().rstrip('.,!;')
            self.learn_fact('user_name', name, 'relationships', source, confidence=1.0,
                            learn_type=learn_type, answerable=answerable)
            learned.append(f"name: {name}")
        
        # Extract identity/role
        if 'i am' in text_lower or "i'm" in text_lower:
            split_on = 'i am' if 'i am' in text_lower else "i'm"
            # Find position and extract from original
            start_pos = user_input.lower().find(split_on) + len(split_on)
            identity = user_input[start_pos:].strip().rstrip('.,!;')
            
            # Determine if it's a skill or identity
            if any(kw in text_lower for kw in ['can', 'able to', 'expert', 'developer', 'engineer']):
                self.learn_fact('user_skills', identity, 'skills', source, confidence=1.0,
                                learn_type=learn_type, answerable=answerable)
                learned.append(f"skill: {identity}")
            else:
                self.learn_fact('user_identity', identity, 'relationships', source, confidence=1.0,
                                learn_type=learn_type, answerable=answerable)
                learned.append(f"identity: {identity}")
        
        # Extract preferences
        for pref_word in ['prefer', 'like', 'love', 'favorite']:
            if pref_word in text_lower:
                start_pos = text_lower.find(pref_word) + len(pref_word)
                preference = user_input[start_pos:].strip().rstrip('.,!;')
                if preference:  # Only if there's content after the keyword
                    self.learn_fact(f'prefers_{pref_word}', preference, 'preferences', source, confidence=1.0,
                                    learn_type=learn_type, answerable=answerable)
                    learned.append(f"preference: {preference}")
                break
        
        # Extract general facts with "remember that" or "note that"
        for trigger in ['remember that', 'note that', 'keep in mind', 'learn this']:
            if trigger in text_lower:
                start_pos = text_lower.find(trigger) + len(trigger)
                fact = user_input[start_pos:].strip().rstrip('.,!;')
                if fact:  # Only if there's content
                    # Auto-generate key from fact
                    fact_key = self.generate_key_from_text(fact)
                    self.learn_fact(fact_key, fact, 'facts', source, confidence=1.0,
                                    learn_type=learn_type, answerable=answerable)
                    learned.append(f"fact: {fact[:50]}")
                break
        
        if learned:
            self.save_all()
            return f"✓ Learned: {', '.join(learned)}"
        
        return None
    
    def generate_key_from_text(self, text: str) -> str:
        """Generate a key from text for storage"""
        # Remove common words and take first few significant words
        stop_words = ['the', 'is', 'are', 'was', 'were', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to']
        words = [w.lower() for w in re.findall(r'\w+', text) if w.lower() not in stop_words]
        key = '_'.join(words[:5])  # Use first 5 significant words
        return key
    
    def learn_fact(self, key: str, value: str, category: str, source: str = "conversation",
                   confidence: float = 1.0, learn_type: str = "explicit", answerable: bool = True):
        """Learn a new fact in the specified category"""
        with self.lock:
            if category not in self.knowledge:
                self.knowledge[category] = {}

            existing = self.knowledge[category].get(key)
            if isinstance(existing, dict):
                existing_value = existing.get('value')
                existing_source = existing.get('source')
                if existing_value == value and existing_source == source:
                    return False
            
            # Store with metadata
            self.knowledge[category][key] = {
                'value': value,
                'learned_at': datetime.now().isoformat(),
                'source': source,
                'confidence': confidence,
                'learn_type': learn_type,
                'answerable': answerable
            }
            
            # Update context map
            self.update_context_map(key, value, category, source)
            return True
    
    def update_context_map(self, key: str, value: str, category: str, source: str):
        """Update context relationships"""
        # Extract topics from value
        topics = self.extract_topics(value)
        for topic in topics:
            if topic not in self.context_map['topics']:
                self.context_map['topics'][topic] = []
            self.context_map['topics'][topic].append({
                'key': key,
                'category': category,
                'value': value
            })
        
        # Track source
        if source not in self.context_map['sources']:
            self.context_map['sources'][source] = []
        self.context_map['sources'][source].append({
            'key': key,
            'category': category,
            'timestamp': datetime.now().isoformat()
        })

    def observe(self, text: str, source: str = "conversation") -> bool:
        """Aggressively learn from non-question statements as low-confidence notes."""
        if self.is_question(text):
            return False
        cleaned = text.strip()
        if len(cleaned) < 6:
            return False
        if not self.is_informative(cleaned):
            return False
        key = f"obs_{self.generate_key_from_text(cleaned)}_{int(time.time())}"
        self.learn_fact(key, cleaned, 'facts', source, confidence=0.3, learn_type="observation", answerable=False)
        self.save_all()
        return True
    
    def extract_topics(self, text: str) -> List[str]:
        """Extract main topics from text"""
        # Simple topic extraction - can be enhanced with NLP
        words = re.findall(r'\b[a-z]{4,}\b', text.lower())
        # Remove common words
        stop_words = set(['that', 'this', 'with', 'from', 'have', 'been', 'were', 'said', 'each', 'which', 'their', 'will', 'would', 'there', 'could', 'should'])
        topics = [w for w in words if w not in stop_words]
        return list(set(topics))[:10]  # Return unique topics, max 10
    
    def search_knowledge(self, query: str, top_k: int = 5, min_confidence: float = 0.0,
                         include_imports: bool = False, include_observations: bool = False,
                         require_token_overlap: bool = True) -> List[Dict]:
        """Search across all knowledge with context awareness"""
        query_tokens = self.tokenize(query)
        if not query_tokens:
            return []
        query_phrase = " ".join(query_tokens)
        results = []
        
        # Search all categories
        for category in ['facts', 'skills', 'preferences', 'relationships']:
            for key, data in self.knowledge[category].items():
                value = data.get('value', '') if isinstance(data, dict) else str(data)
                confidence = data.get('confidence', 1.0) if isinstance(data, dict) else 1.0
                source = data.get('source', 'unknown') if isinstance(data, dict) else 'unknown'
                learn_type = data.get('learn_type') if isinstance(data, dict) else None
                answerable = data.get('answerable', True) if isinstance(data, dict) else True
                
                if confidence < min_confidence:
                    continue
                
                # Infer learn_type for older entries without metadata
                if learn_type is None:
                    if source not in ['conversation', 'unknown']:
                        learn_type = 'import'
                    else:
                        learn_type = 'explicit'
                
                if learn_type == 'import' and not include_imports:
                    continue
                if learn_type == 'observation' and not include_observations:
                    continue
                if answerable is False and not (include_imports or include_observations):
                    continue
                
                # Calculate relevance score
                score = 0
                key_lower = key.replace('_', ' ').lower()
                value_lower = value.lower()
                
                # Token matches (stopword-filtered)
                key_tokens = set(self.tokenize(key_lower))
                value_tokens = set(self.tokenize(value_lower))
                
                key_matches = set(query_tokens) & key_tokens
                value_matches = set(query_tokens) & value_tokens
                matched = key_matches | value_matches
                
                if require_token_overlap and not matched:
                    continue
                
                score += len(key_matches) * 3
                score += len(value_matches) * 2
                score += sum(len(token) for token in key_matches) * 0.2
                score += sum(len(token) for token in value_matches) * 0.15
                
                # Phrase matches (after stopword filtering)
                if query_phrase:
                    if query_phrase in key_lower:
                        score += 6
                    if query_phrase in value_lower:
                        score += 5
                
                if score > 0:
                    matched_count = len(matched)
                    query_token_count = len(query_tokens)
                    coverage = matched_count / query_token_count if query_token_count else 0
                    results.append({
                        'key': key,
                        'value': value,
                        'category': category,
                        'score': score,
                        'source': source,
                        'learned_at': data.get('learned_at', 'unknown') if isinstance(data, dict) else 'unknown',
                        'confidence': confidence,
                        'learn_type': learn_type,
                        'answerable': answerable,
                        'matched_count': matched_count,
                        'query_token_count': query_token_count,
                        'coverage': coverage
                    })
        
        # Sort by score and return top_k
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_k]
    
    def answer_question(self, question: str) -> Optional[str]:
        """Answer questions based on learned knowledge"""
        question_lower = question.lower().strip()
        
        # Summary queries - check these first before name/identity
        summary_keywords = ['what have you learned', 'what all have you learned', 'what did you learn',
                          'show me what you learned', 'tell me what you learned']
        if any(kw in question_lower for kw in summary_keywords):
            return self.get_summary("detailed")
        
        # Brief summary
        if question_lower in ['summary', 'give me a summary', 'learning summary']:
            return self.get_summary("detailed")
        
        # Direct name query
        if 'what is my name' in question_lower or "what's my name" in question_lower:
            name_data = self.knowledge['relationships'].get('user_name')
            if name_data:
                name = name_data.get('value', name_data) if isinstance(name_data, dict) else name_data
                return f"Your name is {name}."
            return "I don't know your name yet. You can tell me by saying 'My name is [name]'."
        
        # Identity query
        if 'who am i' in question_lower or 'what do you know about me' in question_lower:
            parts = []
            
            if 'user_name' in self.knowledge['relationships']:
                name = self.knowledge['relationships']['user_name']
                name_val = name.get('value', name) if isinstance(name, dict) else name
                parts.append(f"Your name is {name_val}")
            
            if 'user_identity' in self.knowledge['relationships']:
                identity = self.knowledge['relationships']['user_identity']
                id_val = identity.get('value', identity) if isinstance(identity, dict) else identity
                parts.append(f"you are {id_val}")
            
            if 'user_skills' in self.knowledge['skills']:
                skills = self.knowledge['skills']['user_skills']
                skill_val = skills.get('value', skills) if isinstance(skills, dict) else skills
                parts.append(f"you can {skill_val}")
            
            if parts:
                return '. '.join(parts).capitalize() + '.'
            return "Tell me about yourself so I can learn who you are."
        
        # For other questions, defer to engine reasoning/synthesis
        return None
    
    def get_stats(self) -> Dict:
        """Get learning statistics"""
        return {
            'total_facts': len(self.knowledge['facts']),
            'total_skills': len(self.knowledge['skills']),
            'total_preferences': len(self.knowledge['preferences']),
            'total_relationships': len(self.knowledge['relationships']),
            'total_items': self.knowledge['metadata']['total_items'],
            'topics': len(self.context_map['topics']),
            'sources': len(self.context_map['sources']),
            'last_updated': self.knowledge['metadata']['last_updated']
        }
    
    def get_summary(self, summary_type: str = "brief") -> str:
        """Get knowledge summary"""
        stats = self.get_stats()
        
        if summary_type == "brief":
            return f"I've learned {stats['total_items']} things about you across {stats['topics']} topics."
        
        elif summary_type == "detailed":
            lines = [
                f"=== Knowledge Summary ===",
                f"Total learned: {stats['total_items']} items",
                f"  Facts: {stats['total_facts']}",
                f"  Skills: {stats['total_skills']}",
                f"  Preferences: {stats['total_preferences']}",
                f"  Relationships: {stats['total_relationships']}",
                f"Topics covered: {stats['topics']}",
                f"Learning sources: {stats['sources']}",
                f"Last updated: {stats['last_updated']}"
            ]
            
            # Show top topics
            if self.context_map['topics']:
                lines.append("\n=== Top Topics ===")
                sorted_topics = sorted(
                    self.context_map['topics'].items(),
                    key=lambda x: len(x[1]),
                    reverse=True
                )[:5]
                for topic, items in sorted_topics:
                    lines.append(f"  {topic}: {len(items)} items")
            
            return '\n'.join(lines)
        
        return "Unknown summary type. Use 'brief' or 'detailed'."

    def normalize_import_text(self, text: str) -> str:
        """Light markdown cleanup so imported docs learn as readable facts."""
        normalized = text.replace('\r\n', '\n')
        normalized = re.sub(r'```.*?```', ' ', normalized, flags=re.DOTALL)
        normalized = re.sub(r'`([^`]*)`', r'\1', normalized)
        normalized = re.sub(r'!\[.*?\]\(.*?\)', ' ', normalized)
        normalized = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', normalized)
        normalized = re.sub(r'^\s{0,3}#+\s*', '', normalized, flags=re.MULTILINE)
        normalized = re.sub(r'^\s*[-*]\s+', '', normalized, flags=re.MULTILINE)
        normalized = re.sub(r'^\s*>\s+', '', normalized, flags=re.MULTILINE)
        normalized = re.sub(r'\n{3,}', '\n\n', normalized)
        return normalized

    def cleanup_import_sentence(self, sentence: str) -> str:
        sentence = sentence.strip()
        sentence = sentence.replace('**', '').replace('__', '').replace('*', '')
        if ' - ' in sentence and not re.search(r'\b(is|are|was|were|has|have|uses|supports|contains|runs|works|avoids|includes|provides)\b', sentence.lower()):
            left, right = sentence.split(' - ', 1)
            sentence = f"{left.strip()} uses {right.strip()}"
        sentence = re.sub(r'\s+', ' ', sentence)
        return sentence.strip(' -\t')
    
    def learn_from_batch(self, text: str, source: str = "batch_import") -> int:
        """Learn from batch text with enhanced context comprehension"""
        text = self.normalize_import_text(text)
        # Split into sentences
        sentences = re.split(r'[.!?]+\s+|\n+', text)
        learned_count = 0
        
        for sentence in sentences:
            sentence = self.cleanup_import_sentence(sentence)
            if len(sentence) < 20:  # Skip very short sentences
                continue
            
            # Try to extract and learn
            result = self.extract_and_learn(sentence, source, learn_type="import", answerable=True)
            if result:
                learned_count += 1
            else:
                # Even if not a teaching phrase, store as general fact if it looks informative
                if self.is_informative(sentence):
                    key = self.generate_key_from_text(sentence)
                    self.learn_fact(key, sentence, 'facts', source, confidence=0.75, learn_type="import", answerable=True)
                    learned_count += 1
        
        self.save_all()
        return learned_count
    
    def is_informative(self, sentence: str) -> bool:
        """Check if sentence is informative enough to store"""
        # Must have certain length and structure
        if len(sentence) < 30:
            return False

        sentence_lower = sentence.lower()

        # Skip lines that are mostly code, commands, or file paths.
        code_markers = ['{', '}', '=>', '::', '</', '/>', 'sudo ', 'def ', 'class ', 'import ', '#include']
        if any(marker in sentence for marker in code_markers):
            return False
        if sentence.count('/') >= 3 or sentence.count('\\') >= 3:
            return False
        if sum(ch in '[](){}<>' for ch in sentence) > 6:
            return False
        
        # Should have verbs that indicate facts
        fact_indicators = [
            'is', 'are', 'was', 'were', 'has', 'have', 'can', 'could', 'will', 'would', 'should',
            'uses', 'supports', 'stores', 'contains', 'runs', 'works', 'avoids', 'includes', 'provides'
        ]
        
        return any(f' {indicator} ' in f' {sentence_lower} ' for indicator in fact_indicators)
    
    def reset_learning(self):
        """Clear all learned knowledge"""
        with self.lock:
            self.knowledge = {
                'facts': {},
                'skills': {},
                'preferences': {},
                'relationships': {},
                'metadata': {
                    'created_at': datetime.now().isoformat(),
                    'last_updated': datetime.now().isoformat(),
                    'total_items': 0
                }
            }
            self.context_map = {
                'topics': {},
                'entities': {},
                'temporal': {},
                'sources': {}
            }
            self.relationships = {
                'connections': {},
                'hierarchy': {},
                'implications': {}
            }
            self.save_all()
