# Shadow AI v2.0.36 Release Notes

**Release Date**: January 11, 2026  
**Codename**: "Wolfy's Memory"

## 🎯 Major Feature: Enhanced Wolfy-Style Learning System

Shadow AI v2.0.36 replaces the simple learning system with **Wolfy AI's structured learning backbone**, providing comprehensive context comprehension and knowledge organization.

---

## 🚀 What's New

### Enhanced Learning System
Complete replacement of the basic learning system with Wolfy AI's consciousness-inspired structured learning:

**Natural Language Extraction**
- Automatically learns from conversational teaching phrases
- "My name is..." → Learns your name
- "I am a developer" → Learns your identity/skills  
- "I prefer Python" → Learns your preferences
- "Remember that..." → Stores general facts
- Smart question detection prevents false positives

**Structured Knowledge Base**
Four organized categories:
- **Facts**: General information and truths
- **Skills**: Abilities and expertise
- **Preferences**: Likes, dislikes, favorites
- **Relationships**: Personal information and connections

**Context-Aware Intelligence**
- **Topic Extraction**: Automatically indexes by main topics
- **Relevance Scoring**: Finds best matches across all categories
- **Source Attribution**: Tracks where each piece of knowledge came from
- **Multi-Category Search**: Searches all knowledge simultaneously

**Batch Learning from Files**
- Load entire text files and extract informative sentences
- Intelligent filtering (>30 chars, factual indicators)
- Skips code-heavy lines (<60% alphanumeric)
- Removes duplicates automatically
- Example: "Learned 1,396 new items from blueprint.md"

**Knowledge Summaries**
Three levels of detail:
- **Brief**: "I've learned 25,961 things across 98 topics"
- **Detailed**: Full breakdown with top topics
- **Query**: "what all have you learned" → detailed summary

**Persistent Storage with Backups**
- Three separate files: knowledge, context, relationships
- Automatic timestamped backups on every save
- Keeps last 10 backups, removes older ones
- Thread-safe with locking for concurrent access
- Storage: `~/.shadow-ai/enhanced_learning/`

### Bug Fixes
- ✅ Fixed false positive learning detection ("what iq do you see" no longer triggers correction)
- ✅ Fixed case-sensitive extraction bugs in natural language learning
- ✅ Removed old `user_learning.py` system completely
- ✅ Summary queries now properly detected and answered

---

## 📊 Comparison: Simple vs Enhanced Learning

| Feature | Simple (v2.0.35) | Enhanced (v2.0.36) |
|---------|------------------|-------------------|
| Categories | 3 (corrections, preferences, facts) | 4 (facts, skills, preferences, relationships) |
| Natural Language | Basic keyword triggers | Advanced pattern matching + context |
| Question Detection | Keyword-based (buggy) | Regex patterns + question marks |
| Storage | Single flat JSON | Three structured files |
| Context Awareness | None | Topic extraction + entity tracking |
| Batch Learning | Line-by-line | Intelligent sentence extraction |
| Search | Simple text match | Scored relevance across categories |
| Backups | None | Automatic timestamped rotation (10) |
| Source Tracking | Basic | Per-item with timestamps |

---

## 🏗️ Technical Architecture

### Processing Tiers (Updated)
```
TIER 0A: Natural language teaching extraction (Wolfy-style)
TIER 0B: Answer from structured knowledge base
TIER 0C: Context-aware search across learned knowledge
TIER 1:  Recognition engine (knowledge base patterns)
TIER 2:  External bridge (Wikipedia + DuckDuckGo mesh)
TIER 3:  Generative model (LLM fallback)
```

### Knowledge Storage
```
~/.shadow-ai/enhanced_learning/
├── default_knowledge.json         # Main knowledge base
├── default_context.json            # Topic/entity relationships
├── default_relationships.json      # Knowledge graph connections
└── backups/
    ├── default_20260111_184200.json
    ├── default_20260111_184100.json
    └── ... (last 10 backups)
```

---

## 📖 Example Usage

### Teaching Shadow
```
You: My name is John Wolf
Shadow: ✓ Learned: name: John Wolf

You: I am a software developer
Shadow: ✓ Learned: skill: a software developer

You: I prefer Python over Java
Shadow: ✓ Learned: preference: Python over Java

You: Remember that Shadow AI was created in 2024
Shadow: ✓ Learned: fact: Shadow AI was created in 2024
```

### Querying Knowledge
```
You: what is my name?
Shadow: Your name is John Wolf.

You: who am i?
Shadow: Your name is John Wolf. You are a software developer.

You: what all have you learned?
Shadow: === Knowledge Summary ===
Total learned: 4 items
  Facts: 1
  Skills: 1
  Preferences: 1
  Relationships: 1
Topics covered: 9
Learning sources: 1

=== Top Topics ===
  wolf: 2 items
  john: 2 items
  developer: 1 items
```

### Batch Learning
```
Shadow: [GUI prompts: "Found 5 text files. Yes = Learn from them / No = Analyze normally"]

User: [Clicks Yes]

Shadow: Learned 1,396 new items from ULTIMATE_Electric_F150_Blueprint_Master.md
        Total knowledge: 25,961 items across 98 topics.
```

---

## 🎓 API Reference

```python
from core.enhanced_learning import EnhancedLearning

# Initialize
learning = EnhancedLearning(user_id="default")

# Natural language extraction
result = learning.extract_and_learn("My name is John")
# Returns: "✓ Learned: name: John" or None

# Answer questions
answer = learning.answer_question("what is my name?")
# Returns: "Your name is John." or None

# Search knowledge
results = learning.search_knowledge("developer", top_k=5)
# Returns: [{'key': ..., 'value': ..., 'score': ...}]

# Batch learning
learned_count = learning.learn_from_batch(text, source="file.txt")
# Returns: number of items learned

# Get statistics
stats = learning.get_stats()
# Returns: {'total_facts': 10, 'total_skills': 5, ...}

# Get summary
summary = learning.get_summary("detailed")  # or "brief"

# Reset all knowledge
learning.reset_learning()
```

---

## 🔄 Migration from v2.0.35

The enhanced learning system is a complete replacement:
- Old data in `~/.shadow-ai/user_learning/` is **not migrated**
- Start fresh with the new structured system
- Old simple learning file (`user_learning.py`) has been removed
- All new conversations will use enhanced learning

---

## 📦 Installation

### From .deb Package
```bash
# Remove old version
sudo apt remove shadow-ai

# Install new version
sudo dpkg -i shadow-ai-2.0.36.deb

# Fix dependencies if needed
sudo apt-get install -f

# Launch
shadow-ai
```

### From Source
```bash
cd ~/Downloads/shadow-ai-v2
./install.sh
./run.sh
```

---

## 🧪 Tested With

- Ubuntu 22.04 LTS
- Python 3.10+
- Ollama models: gemma2:2b, llama3.2, mistral, qwen2.5, etc.
- 10 AI model pulls confirmed working

---

## 🔮 Future Enhancements (v2.1.0+)

Potential improvements being considered:
- NLP topic extraction (spaCy, NLTK)
- Entity recognition (extract proper nouns, dates, locations)
- Relationship inference ("John is Mary's brother" → bidirectional)
- Confidence scoring for facts
- Fact verification against external sources
- Conversation threading
- Export/import knowledge between instances
- Visual knowledge graph GUI

---

## 🐺 Credits

Enhanced Learning System based on **Wolfy AI's consciousness system**:
- Structured knowledge base architecture
- Natural language extraction patterns
- State management with backups
- Teaching trigger detection

Shadow AI development by **Wolf Clan**.

---

## 📄 Documentation

- Main README: `/opt/shadow-ai/README.md`
- Enhanced Learning: `/opt/shadow-ai/ENHANCED_LEARNING.md`
- Quick Reference: `/opt/shadow-ai/QUICK_REFERENCE.md`
- SILS v1 Technical: `/opt/shadow-ai/docs/SILS_v1_COMPLETE.md`

---

## 🔗 Storage Locations

- **Program**: `/opt/shadow-ai/`
- **Launcher**: `/usr/local/bin/shadow-ai`
- **User Data**: `~/.shadow-ai/`
- **Enhanced Learning**: `~/.shadow-ai/enhanced_learning/`
- **Memory**: `~/.shadow-ai/memory.json`
- **Config**: `~/.shadow-ai/config.json`

---

**Version**: 2.0.36  
**Based on**: Wolfy AI consciousness system + SILS v1  
**Thread-Safe**: Yes  
**Backup Rotation**: 10 versions  
**Zero Telemetry**: Always
