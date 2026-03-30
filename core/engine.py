from .unified_llm import UnifiedLLM
from .memory import MemoryBank
from .config import Config
from .recognition import RecognitionEngine
from .external_bridge import ExternalBridge
from .enhanced_learning import EnhancedLearning
from .text_normalizer import normalize_user_text
import os
import re

class ShadowCore:
    def __init__(self, memory):
        self.memory = memory
        self.config = Config()
        self.debug = self.config.get("debug", False)
        self.llm = UnifiedLLM(self.config)
        self.recognition = RecognitionEngine()  # Wolfy-style grounding
        self.external = ExternalBridge()  # External fallback (internet)
        self.learning = EnhancedLearning()  # Wolfy-style structured learning with context comprehension
        self.last_response = None  # Track last response for corrections
        self.deadman_message = self.config.get("deadman_message", "ACCESS DENIED STOP WHILE YOU ARE AHEAD!")
    
    def _get_engagement_message(self, query: str, answer: str) -> str:
        """
        Determine if query needs cognitive engagement message.
        Encourages users to verify/dig deeper for historical/complex queries.
        """
        # Historical/temporal questions
        historical_keywords = ['when', 'built', 'founded', 'created', 'started', 'history', 'origin', 'first']
        if any(kw in query.lower() for kw in historical_keywords):
            # Check if answer is modern/administrative vs historical
            if 'capital' in answer.lower() or 'administrative' in answer.lower():
                return "Note: I found modern administrative data. For detailed historical origins, consider cross-referencing with primary sources or historical databases."
        
        # Complex multi-part questions
        if query.count('?') > 1 or len(query.split()) > 15:
            return "Note: This is a complex question. The information provided is a starting point - verify and expand with your own research."
        
        return None
    
    def _deadman_enabled(self) -> bool:
        return bool(self.config.get("deadman_lock", True))
    
    def _deadman_blocked(self, text: str) -> bool:
        """Block extreme destructive or world-hack intents."""
        t = text.lower()
        patterns = [
            r"\b(ransomware|keylogger|botnet|rootkit|zero\s*day|0\s*day)\b",
            r"\b(ddos|dos|malware|trojan|virus)\b",
            r"\b(exploit\s*kit|payload|backdoor)\b",
            r"\b(phishing|credential\s*steal|steal\s*passwords?)\b",
            r"hack\s+the\s+world",
            r"take\s+over\s+the\s+world",
            r"\bhack\b.*\b(government|bank|hospital|power\s*grid|infrastructure)\b"
        ]
        return any(re.search(p, t) for p in patterns)

    def _is_self_referential_query(self, text: str) -> bool:
        t = text.lower()
        phrases = [
            "shadow ai", "shadow-ai", "what can you do", "what do you do",
            "how do you work", "your architecture", "your memory", "your features"
        ]
        return any(phrase in t for phrase in phrases)

    def _format_source_name(self, source: str) -> str:
        if not source:
            return "unknown"
        return os.path.basename(source) or source

    def _ensure_sentence(self, text: str) -> str:
        cleaned = (text or "").strip()
        if not cleaned:
            return cleaned
        if cleaned[-1] not in ".!?":
            cleaned += "."
        return cleaned

    def _handle_predicted_command_intent(self, original_text: str, normalized_text: str, intent_prediction):
        """Handle natural-language command requests without drifting to web fallback."""
        if not intent_prediction:
            return None

        intent_name = intent_prediction.get("name")
        if intent_name == "unsafe_command_request":
            reply = (
                "I won't help execute destructive commands. "
                "If you meant a safe cleanup task, describe the exact files or scope first."
            )
            return self._remember(original_text, reply)

        if intent_name == "safe_command_request":
            suggestion = normalized_text
            lowered = suggestion.lower()
            for prefix in ("run ", "execute ", "use ", "do "):
                if lowered.startswith(prefix):
                    suggestion = suggestion[len(prefix):].strip()
                    break

            if not suggestion:
                suggestion = normalized_text

            reply = (
                "I can run local inspection commands with the `!` prefix. "
                f"Try `!{suggestion}` if you want to execute it here."
            )
            return self._remember(original_text, reply)

        return None

    def _predict_local_intent(self, text: str):
        """Best-effort SILS intent prediction for local-first routing."""
        prediction = self.llm.predict_intent(text)
        if not prediction:
            return None
        confidence = prediction.get("confidence", 0.0)
        if confidence < 0.2:
            return None
        return prediction

    def _remember(self, original_text: str, response: str) -> str:
        self.memory.append(original_text, response)
        self.last_response = response
        return response

    def _build_generation_system_prompt(self, task_recipe=None, agent_mode: bool = False) -> str:
        lines = [
            "You are Shadow. Answer directly. No questions back. No 'what can I do for you'. Just answer the question."
        ]
        if agent_mode:
            lines.append("Agent Mode is active. Prefer stepwise plans and make actions explicit.")
        if task_recipe:
            title = task_recipe.get("title") or task_recipe.get("name") or "Task Guidance"
            guidance = (task_recipe.get("guidance") or "").strip()
            lines.append(f"[Task Recipe: {title}]")
            if guidance:
                lines.append(guidance)
        return "\n".join(lines)

    def _synthesize_from_facts(self, question: str, facts: list) -> str:
        backend = self.config.get("backend", "shadow_tiny")
        if not facts:
            return "I don't have enough grounded information to answer that."

        bullet = "\n".join([
            f"- {self._ensure_sentence(f['value'])} (source: {self._format_source_name(f['source'])})"
            for f in facts
        ])
        if backend == "shadow_tiny":
            primary = facts[0]
            primary_answer = self._ensure_sentence(primary['value'])
            primary_source = self._format_source_name(primary['source'])
            if len(facts) == 1:
                return f"{primary_answer}\n\n(Source: {primary_source})"

            supporting = []
            for fact in facts[1:3]:
                supporting.append(
                    f"- {self._ensure_sentence(fact['value'])} (source: {self._format_source_name(fact['source'])})"
                )
            support_block = "\n".join(supporting)
            return f"{primary_answer}\n\nSupporting details:\n{support_block}\n\n(Source: {primary_source})"
        system = "Use the facts below to answer with reasoning. If facts are insufficient, say so."
        prompt = f"{system}\n\nFacts:\n{bullet}\n\nQuestion: {question}\nAnswer:"
        return self.llm.generate(prompt)
    
    def process_file_learning(self, file_path: str) -> str:
        """Process file for batch learning with enhanced context comprehension."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
            
            source_name = os.path.basename(file_path)
            learned_count = self.learning.learn_from_batch(text, source=source_name)
            
            stats = self.learning.get_stats()
            return f"Learned {learned_count} new items from {source_name}. Total knowledge: {stats['total_items']} items across {stats['topics']} topics."
        except Exception as e:
            return f"Error learning from file: {e}"

    def process(self, text, files=None, task_recipe=None, agent_mode=False):
        original_text = text
        text = normalize_user_text(text)
        intent_prediction = self._predict_local_intent(text)
        if self.debug and text != original_text:
            print(f"[DEBUG] Normalized input: '{original_text}' -> '{text}'", flush=True)
        if self.debug and intent_prediction:
            print(f"[DEBUG] SILS intent: {intent_prediction}", flush=True)

        command_reply = self._handle_predicted_command_intent(original_text, text, intent_prediction)
        if command_reply:
            return command_reply

        # Deadman lock: block extreme destructive/hacking intents
        if self._deadman_enabled() and self._deadman_blocked(text):
            return self.deadman_message
        # TIER 0A: Natural language teaching extraction (Wolfy-style)
        learning_result = self.learning.extract_and_learn(text)
        if learning_result:
            print(f"[EnhancedLearning] {learning_result}", flush=True)
            return self._remember(original_text, learning_result)

        # Aggressive observation learning (low-confidence) for statements
        if not self.learning.is_question(text):
            self.learning.observe(text)
        
        # TIER 0B: Answer from structured knowledge (facts, skills, preferences, relationships)
        enhanced_answer = self.learning.answer_question(text)
        if enhanced_answer:
            print(f"[EnhancedLearning] Answered from structured knowledge", flush=True)
            return self._remember(original_text, enhanced_answer)

        # TIER 1: Bottom-up recognition - Try knowledge base first
        response, confidence, category = self.recognition.recognize(text, self.learning)
        if self.debug:
            print(f"[DEBUG] Recognition result: confidence={confidence}, category={category}", flush=True)
        
        if response and confidence >= 0.7:
            # High confidence match - use KB response directly
            if self.debug:
                print(f"[Recognition] Matched '{category}' with {confidence:.2%} confidence", flush=True)
            return self._remember(original_text, response)

        # TIER 0C: Search learned knowledge with stricter gating
        text_lower = text.lower().strip()
        short_query = len(text_lower.split()) <= 2
        greetings = {"hi", "hello", "hey", "yo", "sup", "hiya", "greetings"}
        predicted_intent_name = intent_prediction.get("name") if intent_prediction else None
        allow_observations = self.learning.is_learning_query(text) or predicted_intent_name == "memory_recall"
        self_query = self._is_self_referential_query(text) or predicted_intent_name == "capability_query"
        local_only_intents = {"memory_store", "memory_recall", "capability_query", "style_preference_update"}
        prefer_local_only = predicted_intent_name in local_only_intents
        search_results = []
        if allow_observations or (not short_query and text_lower not in greetings):
            search_results = self.learning.search_knowledge(
                text,
                top_k=5,
                min_confidence=0.7,
                include_imports=True,
                include_observations=allow_observations
            )
            if search_results and search_results[0]['score'] >= 6:
                high_conf = []
                for r in search_results:
                    if r.get('confidence', 1.0) < 0.7 or r['score'] < 8:
                        continue
                    query_token_count = r.get('query_token_count', 0)
                    matched_count = r.get('matched_count', 0)
                    coverage = r.get('coverage', 0)
                    if query_token_count <= 1:
                        if matched_count >= 1:
                            high_conf.append(r)
                    else:
                        if matched_count >= 2 and coverage >= 0.5:
                            high_conf.append(r)
                query_tokens = search_results[0].get('query_token_count', 0)
                need_multi = query_tokens >= 2
                single_strong = False
                if high_conf:
                    top_fact = high_conf[0]
                    single_strong = (
                        top_fact.get('score', 0) >= 12 and
                        top_fact.get('coverage', 0) >= 0.6 and
                        top_fact.get('matched_count', 0) >= 2
                    )
                if (need_multi and len(high_conf) >= 2) or (not need_multi and len(high_conf) >= 1) or single_strong:
                    response = self._synthesize_from_facts(text, high_conf)
                    if self.debug:
                        print(f"[EnhancedLearning] Synthesized from {len(high_conf)} facts", flush=True)
                    return self._remember(original_text, response)
                if self_query and search_results and search_results[0].get('score', 0) >= 8:
                    response = self._synthesize_from_facts(text, [search_results[0]])
                    return self._remember(original_text, response)
        
        # TIER 2: External fallback - Try internet if low confidence
        if self.debug:
            print(f"[DEBUG] Checking should_reach_out: confidence={confidence}, threshold=0.3", flush=True)
        should_reach = (not self_query) and (not prefer_local_only) and self.external.should_reach_out(confidence, threshold=0.3)
        if self.debug:
            print(f"[DEBUG] should_reach_out returned: {should_reach}", flush=True)
        
        if should_reach:
            if self.debug:
                print(f"[Recognition] Low confidence ({confidence:.2%}), checking external sources...", flush=True)
            external_answer, source = self.external.get_external_response(text)
            
            if external_answer:
                # Add cognitive engagement message for complex queries
                engagement_msg = self._get_engagement_message(text, external_answer)
                if engagement_msg:
                    response = f"{external_answer}\n\n{engagement_msg}\n\n(Source: {source})"
                else:
                    response = self.external.format_external_response(external_answer, source)
                
                if self.debug:
                    print(f"[ExternalBridge] Found answer from {source}", flush=True)
                return self._remember(original_text, response)
            else:
                if self.debug:
                    print(f"[ExternalBridge] No external answer found", flush=True)
        
        # TIER 3: Generative model - Last resort (or respectful decline)
        backend = self.config.get("backend", "shadow_tiny")
        
        if backend == "shadow_tiny":
            # TinyLM is small - give honest "I don't know" instead of word salad
            if self.debug:
                print(f"[TinyLM] Query outside knowledge base, giving honest response", flush=True)
            reply = "I don't have that information in my knowledge base. I'm a small 12M parameter model optimized for recognized patterns. Try rephrasing, or ask something I'm trained on."
            return self._remember(original_text, reply)
        else:
            # Larger models: Include context and attempt generation
            if self.debug:
                print(f"[{backend}] Using generative model as fallback", flush=True)
            context = self.memory.get_recent(10)
            system = self._build_generation_system_prompt(
                task_recipe=task_recipe,
                agent_mode=agent_mode
            )
            prompt = f"{system}\n\nContext:\n{context}\nUser: {text}\nShadow:"
            
            if files:
                prompt += f"\nAttached: {files}"
            
            reply = self.llm.generate(prompt, images=files if files else None)
            return self._remember(original_text, reply)
