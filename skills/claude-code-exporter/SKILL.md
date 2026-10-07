---
name: claude-code-exporter
description: >-
  Full-fidelity export of Claude Code sessions to portable formats. Copies raw
  JSONL verbatim (lossless), converts to AgentLog v0.2.0 events, and generates
  ASI v1 normalized messages with typed parts. Includes subagent session export.
  Trigger: "export claude session", "claude code export", "agentlog from claude",
  "archive claude session", "claude chat history".
compatibility: "Requires Python 3.9+. Reads Claude Code data from ~/.claude/."
license: MIT
---

# Claude Code Exporter

Export Claude Code sessions to 3 portable formats.

**Primary tool:** `python3 scripts/claude_code_export.py <subcommand>`

For data model details, see `claude-code-inspector`.

## Output

```
~/claude_exports/
├── <sid>.raw_session.jsonl     # Verbatim copy of original JSONL (lossless)
├── <sid>.subagents/            # Subagent JSONL + meta.json files (if any)
├── <sid>.agentlog.jsonl        # AgentLog v0.2.0 events
└── <sid>.asi.jsonl             # ASI v1 normalized messages
```

## Usage

```bash
python3 scripts/claude_code_export.py --list
python3 scripts/claude_code_export.py --export <sessionId>
python3 scripts/claude_code_export.py --export <sessionId> --outdir ~/my_exports
python3 scripts/claude_code_export.py --export <sessionId> --no-agentlog
python3 scripts/claude_code_export.py --verify <file>
```

## Format Mapping

Claude Code stores Anthropic API content blocks natively. The mapping is direct:

### AgentLog v0.2.0

| Claude Code block | AgentLog event |
|-------------------|---------------|
| `thinking` | `reasoning` (intent + rationale) |
| `text` (assistant) | `message` (role=assistant) |
| `text` (user) | `message` (role=user) |
| `tool_use` | `toolCall` (name, input) |
| `tool_result` | `toolCall` (output, status) |
| system `turn_duration` | `message` (role=system) |

### ASI v1

| Claude Code block | ASI part kind |
|-------------------|--------------|
| `thinking` | `reasoning` (text + signature) |
| `text` | `text` |
| `tool_use` | `tool_call` (call_id, name, arguments) |
| `tool_result` | `tool_result` (call_id, output, is_error) |

## Cross-references

| Need | Skill |
|------|-------|
| Session listing, data model details | `claude-code-inspector` |
| Shared utilities (path detection, JSONL parsing) | `claude-code-core` |
