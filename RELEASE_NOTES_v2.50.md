Shadow AI v2.50 Release Notes
Date: January 27, 2026

Highlights
- Deadman Lock: hard-blocks extreme destructive/world‑hack intents and commands with a fixed “ACCESS DENIED STOP WHILE YOU ARE AHEAD!” response.
- Agent Backend Selector: choose Ollama / GGUF / API specifically for Agent Mode per request.
- Anti‑parrot fixes: capability questions route to KB first; learned‑search relevance tightened.

Improvements
- Safer command execution by blocking catastrophic OS‑kill and disk‑wipe patterns.
- Cleaner capability intent handling for natural phrasing (“what all can you do”).

Notes
- Deadman lock is enabled by default and currently has no UI unlock.
