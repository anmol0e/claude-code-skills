---
name: claude-code-core
description: >-
  Shared Python foundation for the claude-code skill suite (inspector, exporter).
  Provides cross-platform ~/.claude/ path detection, project directory discovery,
  session JSONL file discovery (root + subagent), JSONL parsing, and session
  metadata extraction. Other claude-code skills import from this module.
  Not invoked directly.
compatibility: "Requires Python 3.9+. Reads Claude Code session files from ~/.claude/."
license: MIT
---

# Claude Code Core

Shared Python utilities for `claude-code-inspector` and `claude-code-exporter`.

**Not invoked directly.** Exists so `scripts/claude_code_core.py` is discoverable.

## What it provides

| Function | Purpose |
|----------|---------|
| `claude_home()` | `~/.claude/` path |
| `projects_dir()` | `~/.claude/projects/` path |
| `encode_project_path(path)` | Encode `/abs/path` → `-abs-path` |
| `decode_project_path(encoded)` | Decode `-abs-path` → `/abs/path` |
| `list_project_dirs()` | List all project directories with decoded paths |
| `list_sessions(project_dir)` | List root session JSONL files |
| `list_subagents(project_dir, sid)` | List subagent JSONL + meta.json pairs |
| `parse_jsonl(filepath)` | Yield `(line_num, dict)` from a JSONL file |
| `extract_session_metadata(filepath)` | Extract title, counts, timestamps without full load |

## How other skills import it

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "claude-code-core", "scripts"))
from claude_code_core import list_project_dirs, list_sessions, parse_jsonl
```
