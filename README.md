# Claude Code Skills

Inspect, query, and export Claude Code sessions from `~/.claude/`.

Three skills for working with Claude Code's file-based JSONL session data — usable from **Cursor**, **Claude Code**, **Gemini CLI**, and any host supporting [Agent Skills](https://agentskills.io).

## Skills

| Skill | What it does |
|-------|-------------|
| **claude-code-core** | Shared Python utilities: path detection, project discovery, JSONL parsing, session metadata extraction |
| **claude-code-inspector** | List sessions, show details, query messages, subagent trees, tool distribution, prompt history, stats |
| **claude-code-exporter** | Export to 3 formats: raw JSONL copy (lossless), AgentLog v0.2.0, ASI v1 normalized |

## Install

### Cursor — From GitHub Repository

Customize → From GitHub Repository → `anmol0e/claude-code-skills`

### npx (any agent)

```bash
npx skills add anmol0e/claude-code-skills
npx skills add anmol0e/claude-code-skills --agent cursor --agent claude-code
```

### Claude Code

```bash
/plugin marketplace add anmol0e/claude-code-skills
```

### Gemini CLI

```bash
gemini skills install https://github.com/anmol0e/claude-code-skills.git --path skills
```

### Manual

```bash
git clone https://github.com/anmol0e/claude-code-skills.git
cp -r claude-code-skills/skills/* ~/.cursor/skills/    # or ~/.claude/skills/
```

## Quick Start

```
> List my Claude Code sessions
> Export the Stuxnet session to AgentLog format
> How many tool calls did my last Claude Code session use?
```

## Data Model

Claude Code stores sessions as flat **JSONL files** (one event per line) — no database.

```
~/.claude/projects/<encoded-path>/
├── <uuid>.jsonl                    ← root session
└── <uuid>/subagents/
    ├── agent-<name>-<hash>.jsonl   ← subagent session
    └── agent-<name>-<hash>.meta.json
```

Content blocks use the **Anthropic API format** directly: `thinking`, `tool_use`, `tool_result`, `text`.

## Output Formats (Export)

| File | Format | Use case |
|------|--------|----------|
| `.raw_session.jsonl` | Verbatim JSONL copy | Lossless backup / migration |
| `.agentlog.jsonl` | AgentLog v0.2.0 | Ecosystem tools, analytics |
| `.asi.jsonl` | ASI v1 normalized | Typed parts, streaming-friendly |

## Requirements

- Python 3.9+ (stdlib only)
- Claude Code installed (`~/.claude/` must exist with session data)

## License

[MIT](LICENSE)
