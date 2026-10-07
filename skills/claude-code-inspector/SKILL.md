---
name: claude-code-inspector
description: >-
  Inspect, list, query, and navigate Claude Code sessions from ~/.claude/.
  Read-only operations against session JSONL files, subagent metadata, prompt
  history, and job state. Use when asked to find Claude Code sessions, count
  messages, list subagents, check tool usage, view prompt history, or understand
  the Claude Code data model.
  Trigger: "inspect claude code", "claude sessions", "claude history",
  "list claude sessions", "claude subagents", "claude tools".
compatibility: "Requires Python 3.9+. Reads Claude Code data from ~/.claude/."
license: MIT
---

# Claude Code Inspector

Read-only inspection of Claude Code sessions in `~/.claude/`.

**Primary tool:** `python3 scripts/claude_code_inspect.py <subcommand>`

## Data Model

Claude Code stores sessions as **JSONL files** (one line per event) — no database.

### Storage layout

```
~/.claude/projects/<encoded-path>/
├── <uuid>.jsonl                           ← root session
├── <uuid>/subagents/
│   ├── agent-<name>-<hash>.jsonl          ← subagent session
│   └── agent-<name>-<hash>.meta.json      ← subagent metadata
```

Path encoding: `/Users/foo/project` → `-Users-foo-project`

### 13 message types

| Type | Description |
|------|-------------|
| `user` | User message (30 fields: uuid, message, timestamp, cwd, version, gitBranch, origin, toolUseResult, etc.) |
| `assistant` | AI response (23 fields: message with content blocks, effort, model, attributionAgent, etc.) |
| `attachment` | Context injection (8 subtypes: file, skill_listing, total_tokens_reminder, task_reminder, agent_listing_delta, date_change, invoked_skills, command_permissions) |
| `system` | System events (5 subtypes: compact_boundary, local_command, turn_duration, agents_killed, informational) |
| `ai-title` | Auto-generated session title |
| `mode` | Mode setting (normal, plan) |
| `permission-mode` | Permission mode (bypassPermissions, etc.) |
| `last-prompt` | Last prompt tracking (for resume) |
| `queue-operation` | Queue operations (enqueue) |
| `agent-name` | Subagent name assignment |
| `agent-color` | Subagent color assignment |
| `atis-latch` | ATIS latch state |
| `file-history-snapshot` | File state snapshot |

### 4 content block types (Anthropic API native)

| Block | Fields | Description |
|-------|--------|-------------|
| `thinking` | type, thinking, signature | Chain-of-thought reasoning |
| `tool_use` | type, id, name, input | Tool invocation |
| `tool_result` | type, tool_use_id, content, is_error | Tool output |
| `text` | type, text | Text response |

### Subagent meta.json

Fields: `agentType`, `description`, `name`, `spawnDepth`, `model`, `taskKind`, `teamName`, `color`, `planModeRequired`, `permissionMode`.

## Commands

```bash
python3 scripts/claude_code_inspect.py projects              # List project directories
python3 scripts/claude_code_inspect.py sessions               # List all sessions
python3 scripts/claude_code_inspect.py sessions --project /path # Filter by project
python3 scripts/claude_code_inspect.py session <sessionId>    # Session details
python3 scripts/claude_code_inspect.py messages <sessionId>   # List messages
python3 scripts/claude_code_inspect.py subagents <sessionId>  # List subagents
python3 scripts/claude_code_inspect.py tools <sessionId>      # Tool call distribution
python3 scripts/claude_code_inspect.py stats                  # Overall statistics
python3 scripts/claude_code_inspect.py history                # Prompt history
```
