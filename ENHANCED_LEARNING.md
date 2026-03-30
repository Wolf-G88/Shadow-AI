# Enhanced Learning System (Wolfy-Style)

Shadow AI v2.0.36 now includes an **Enhanced Learning System** based on Wolfy AI's structured learning backbone, with expanded context comprehension and automatic knowledge organization.

## Features

### 1. Structured Knowledge Base
Knowledge is automatically organized into four categories:
- **Facts**: General information ("remember that...")
- **Skills**: Abilities and expertise ("I can...", "I'm a developer")
- **Preferences**: Likes and dislikes ("I prefer...", "I like...")
- **Relationships**: Personal information ("My name is...", "I am...")

### 2. Natural Language Learning
Shadow automatically detects and learns from natural teaching phrases:

```
User: My name is John Wolf
Shadow: ✓ Learned: name: John Wolf

User: I am a software developer
Shadow: ✓ Learned: skill: a software developer

User: I prefer Python over Java
Shadow: ✓ Learned: preference: Python over Java

User: Remember that Shadow AI was created in 2024
Shadow: ✓ Learned: fact: Shadow AI was created in 2024
```

### 3. Intelligent Question Detection
The system **does NOT** trigger learning on questions:

```
User: what iq do you see from all that knowledge?
Shadow: [searches learned knowledge, doesn't treat as correction]

User: what is my name?
Shadow: Your name is John Wolf.

User: who am i?
Shadow: Your name is John Wolf. You can a software developer.
```

### 4. Context-Aware Search
- **Topic extraction**: Automatically indexes by main topics
- **Relevance scoring**: Finds best matches across all categories
- **Source attribution**: Tracks where knowledge came from
- **Multi-category search**: Searches facts, skills, preferences, relationships simultaneously

### 5. Batch Learning from Files
Load entire text files and Shadow will extract informative sentences:

```
Shadow: Learned 1,396 new items from ULTIMATE_Electric_F150_Blueprint_Master.md
        Total knowledge: 25,961 items across 98 topics.
```

Filters:
- Skips code-heavy lines (< 60% alphanumeric)
- Removes duplicates
- Limits chunks to 500 chars
- Only stores sentences with factual indicators (is, are, has, can, etc.)

### 6. Knowledge Summaries
Three levels of detail:

**Brief**:
```
I've learned 4 things about you across 9 topics.
```

**Detailed**:
```
=== Knowledge Summary ===
Total learned: 4 items
  Facts: 1
  Skills: 1
  Preferences: 1
  Relationships: 1
Topics covered: 9
Learning sources: 1
Last updated: 2026-01-10T14:19:56.051702

=== Top Topics ===
  wolf: 2 items
  john: 2 items
  developer: 1 items
```

### 7. Persistent Storage with Backups
- **Thread-safe**: Multiple concurrent accesses handled safely
- **Automatic backups**: Timestamped backups created on every save
- **Backup rotation**: Keeps last 10 backups, removes older ones
- **Three storage files**:
  - `~/.shadow-ai/enhanced_learning/{user}_knowledge.json` - Main knowledge
  - `~/.shadow-ai/enhanced_learning/{user}_context.json` - Context relationships
  - `~/.shadow-ai/enhanced_learning/{user}_relationships.json` - Knowledge graph

### 8. Context Mapping
Builds relationships between learned items:
- **Topics**: Links facts by common topics
- **Entities**: Tracks mentioned entities and their properties
- **Sources**: Groups knowledge by source file/conversation
- **Connections**: Maps relationships between knowledge items

## Teaching Triggers

### Automatic Detection
The system recognizes these teaching phrases:
- "my name is", "i am", "i'm", "i work", "i live"
- "i prefer", "i like", "i love", "i hate", "i dislike"
- "remember that", "note that", "keep in mind", "learn this"
- "the fact is", "it's important that", "you should know"

### Question Patterns (Skipped)
These patterns are recognized as questions and NOT treated as teaching:
- "what is/are/was/were..."
- "who is/are/was/were..."
- "where is/are/was/were..."
- "when is/are/was/were..."
- "why is/are/was/were..."
- "how is/are/was/were..."
- "can/could/would/should you..."
- Any sentence ending with "?"

## API Reference

### EnhancedLearning Class

```python
from core.enhanced_learning import EnhancedLearning

# Initialize
learning = EnhancedLearning(user_id="default")

# Natural language extraction
result = learning.extract_and_learn("My name is John", source="conversation")
# Returns: "✓ Learned: name: John" or None if not teaching

# Answer questions
answer = learning.answer_question("what is my name?")
# Returns: "Your name is John." or None if not found

# Search knowledge
results = learning.search_knowledge("developer", top_k=5)
# Returns: [{'key': ..., 'value': ..., 'score': ..., 'category': ..., 'source': ...}]

# Batch learning
learned_count = learning.learn_from_batch(text, source="filename.txt")
# Returns: number of items learned

# Get statistics
stats = learning.get_stats()
# Returns: {'total_facts': 10, 'total_skills': 5, ...}

# Get summary
summary = learning.get_summary("detailed")  # or "brief"
# Returns: formatted summary string

# Reset all knowledge
learning.reset_learning()
```

## Integration

The enhanced learning system is integrated into Shadow AI's processing tiers:

```
TIER 0A: Natural language teaching extraction
TIER 0B: Answer from structured knowledge
TIER 0C: Search all learned knowledge
TIER 1:  Recognition engine (knowledge base)
TIER 2:  External bridge (internet search)
TIER 3:  Generative model (LLM)
```

This ensures learned knowledge is checked before falling back to external sources or generation.

## Comparison: Simple vs Enhanced Learning

| Feature | Simple Learning | Enhanced Learning |
|---------|----------------|-------------------|
| Categories | corrections, preferences, facts | facts, skills, preferences, relationships |
| Natural language | Basic keyword triggers | Advanced pattern matching + context |
| Question detection | Keyword-based (buggy) | Regex patterns + question marks |
| Storage | Single flat JSON | Three structured files |
| Context awareness | None | Topic extraction + entity tracking |
| Batch learning | Line-by-line | Intelligent sentence extraction |
| Search | Simple text match | Scored relevance across categories |
| Backups | None | Automatic timestamped rotation |
| Source tracking | Basic | Per-item with timestamps |

## Future Enhancements

Potential improvements for v2.1.0+:
- **NLP topic extraction**: Replace regex with proper NLP (spaCy, NLTK)
- **Entity recognition**: Extract proper nouns, dates, locations automatically
- **Relationship inference**: "John is Mary's brother" → bidirectional link
- **Confidence scoring**: Track how certain each fact is
- **Fact verification**: Check learned facts against external sources
- **Conversation threading**: Link related exchanges
- **Export/import**: Share knowledge between Shadow AI instances
- **Visual knowledge graph**: GUI visualization of connections

---

**Version**: Shadow AI v2.0.36  
**Based on**: Wolfy AI's consciousness system  
**Storage**: `~/.shadow-ai/enhanced_learning/`  
**Thread-safe**: Yes  
**Backup rotation**: 10 versions
