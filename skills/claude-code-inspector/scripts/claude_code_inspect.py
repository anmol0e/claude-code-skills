#!/usr/bin/env python3
"""
claude_code_inspect.py — Inspect Claude Code sessions from ~/.claude/.

Usage:
  python3 claude_code_inspect.py sessions [--project PATH]
  python3 claude_code_inspect.py session <sessionId>
  python3 claude_code_inspect.py messages <sessionId> [--limit N]
  python3 claude_code_inspect.py subagents <sessionId>
  python3 claude_code_inspect.py tools <sessionId>
  python3 claude_code_inspect.py stats
  python3 claude_code_inspect.py history [--limit N]
  python3 claude_code_inspect.py projects
"""
import json, sys, os
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "claude-code-core", "scripts"))
from claude_code_core import (
    list_project_dirs, list_sessions, list_subagents,
    parse_jsonl, extract_session_metadata, iso_to_short,
    claude_home, projects_dir,
)


def _find_session(sid):
    """Find a session JSONL file by ID across all projects."""
    for _, _, proj_path in list_project_dirs():
        for s_id, fp, _, _ in list_sessions(proj_path):
            if s_id == sid or s_id.startswith(sid):
                return fp, proj_path
    return None, None


def cmd_projects(_args):
    for encoded, decoded, full_path in list_project_dirs():
        sessions = list_sessions(full_path)
        print(f"  {decoded}")
        print(f"    Sessions: {len(sessions)}")
        total_subs = 0
        for sid, _, _, _ in sessions:
            total_subs += len(list_subagents(full_path, sid))
        if total_subs:
            print(f"    Subagents: {total_subs}")
        print()


def cmd_sessions(args):
    project_filter = None
    if "--project" in args:
        project_filter = args[args.index("--project") + 1]

    for encoded, decoded, proj_path in list_project_dirs():
        if project_filter and project_filter not in decoded:
            continue
        sessions = list_sessions(proj_path)
        if not sessions:
            continue
        print(f"Project: {decoded}")
        print(f"{'sessionId':<40} {'lines':>6} {'size':>8}  {'title':<40} {'updated'}")
        print("-" * 120)
        for sid, fp, lines, size in sessions:
            meta = extract_session_metadata(fp)
            size_str = f"{size/1024:.0f}K"
            print(f"{sid:<40} {lines:>6} {size_str:>8}  {(meta['title'] or '?')[:39]:<40} {iso_to_short(meta['last_timestamp'])}")
        print()


def cmd_session(args):
    sid = args[0]
    fp, proj_path = _find_session(sid)
    if not fp:
        sys.exit(f"Session not found: {sid}")
    meta = extract_session_metadata(fp)
    subs = list_subagents(proj_path, meta["session_id"])
    print(f"Session: {meta['session_id']}")
    print(f"  Title:      {meta['title'] or '(untitled)'}")
    print(f"  Mode:       {meta['mode']}")
    print(f"  Perms:      {meta['permission_mode']}")
    print(f"  CLI:        {meta['version']}")
    print(f"  CWD:        {meta['cwd']}")
    print(f"  Branch:     {meta['git_branch']}")
    print(f"  Lines:      {meta['total_lines']}")
    print(f"  User msgs:  {meta['user_count']}")
    print(f"  Asst msgs:  {meta['assistant_count']}")
    print(f"  Tool calls: {meta['tool_use_count']}")
    print(f"  Subagents:  {len(subs)}")
    print(f"  First:      {iso_to_short(meta['first_timestamp'])}")
    print(f"  Last:       {iso_to_short(meta['last_timestamp'])}")
    if subs:
        print(f"\n  Subagents:")
        for name, _, _, m in subs:
            print(f"    {m.get('name', name):<30} model={m.get('model', '?'):<25} kind={m.get('taskKind', '?')}")


def cmd_messages(args):
    sid = args[0]
    limit = 50
    if "--limit" in args:
        limit = int(args[args.index("--limit") + 1])
    fp, _ = _find_session(sid)
    if not fp:
        sys.exit(f"Session not found: {sid}")

    count = 0
    print(f"{'#':<4} {'type':<12} {'uuid':<38} {'detail':<50} {'timestamp'}")
    print("-" * 140)
    for _, d in parse_jsonl(fp):
        t = d.get("type")
        if t not in ("user", "assistant", "system", "attachment"):
            continue
        count += 1
        if count > limit:
            break
        uuid = d.get("uuid", "")[:36]
        ts = iso_to_short(d.get("timestamp"))
        if t == "user":
            msg = d.get("message", {})
            content = msg.get("content", "")
            preview = content[:49] if isinstance(content, str) else f"[{len(content)} blocks]"
        elif t == "assistant":
            content = d.get("message", {}).get("content", [])
            if isinstance(content, list):
                types = [b.get("type", "?") for b in content if isinstance(b, dict)]
                preview = ", ".join(types)
            else:
                preview = "?"
        elif t == "attachment":
            preview = d.get("attachment", {}).get("type", "?")
        else:
            preview = d.get("subtype", "")
        print(f"{count:<4} {t:<12} {uuid:<38} {preview[:49]:<50} {ts}")
    print(f"\n{count} messages shown")


def cmd_subagents(args):
    sid = args[0]
    fp, proj_path = _find_session(sid)
    if not fp:
        sys.exit(f"Session not found: {sid}")
    subs = list_subagents(proj_path, sid)
    if not subs:
        print("No subagents")
        return
    print(f"{'name':<35} {'model':<25} {'kind':<25} {'depth'} {'color'}")
    print("-" * 120)
    for name, jsonl_path, _, meta in subs:
        lines = sum(1 for _ in open(jsonl_path))
        print(f"{meta.get('name', name)[:34]:<35} {meta.get('model', '?')[:24]:<25} "
              f"{meta.get('taskKind', '?')[:24]:<25} {meta.get('spawnDepth', '?'):<6} {meta.get('color', '')}")
    print(f"\n{len(subs)} subagents")


def cmd_tools(args):
    sid = args[0]
    fp, _ = _find_session(sid)
    if not fp:
        sys.exit(f"Session not found: {sid}")
    tools = Counter()
    for _, d in parse_jsonl(fp):
        if d.get("type") != "assistant":
            continue
        for block in d.get("message", {}).get("content", []):
            if isinstance(block, dict) and block.get("type") == "tool_use":
                tools[block.get("name", "?")] += 1
    print(f"{'Tool':<35} {'Count':>6}")
    print("-" * 45)
    for tool, cnt in tools.most_common():
        print(f"{tool:<35} {cnt:>6}")


def cmd_stats(_args):
    total_sessions = 0
    total_subagents = 0
    total_lines = 0
    total_size = 0
    all_tools = Counter()

    for _, decoded, proj_path in list_project_dirs():
        sessions = list_sessions(proj_path)
        for sid, fp, lines, size in sessions:
            total_sessions += 1
            total_lines += lines
            total_size += size
            subs = list_subagents(proj_path, sid)
            total_subagents += len(subs)
            for _, sfp, _, _ in subs:
                sub_lines = sum(1 for _ in open(sfp))
                total_lines += sub_lines
                total_size += os.path.getsize(sfp)

    history_path = os.path.join(claude_home(), "history.jsonl")
    history_lines = 0
    if os.path.exists(history_path):
        history_lines = sum(1 for _ in open(history_path))

    print("=== Claude Code Stats ===")
    print(f"  Projects:       {len(list_project_dirs())}")
    print(f"  Root sessions:  {total_sessions}")
    print(f"  Subagents:      {total_subagents}")
    print(f"  Total JSONL:    {total_lines} lines")
    print(f"  Total size:     {total_size / 1024:.0f} KB")
    print(f"  History:        {history_lines} entries")


def cmd_history(args):
    limit = 20
    if "--limit" in args:
        limit = int(args[args.index("--limit") + 1])
    history_path = os.path.join(claude_home(), "history.jsonl")
    if not os.path.exists(history_path):
        print("No history.jsonl found")
        return
    entries = list(parse_jsonl(history_path))
    entries.reverse()
    print(f"{'#':<4} {'sessionId':<38} {'timestamp':<22} {'prompt'}")
    print("-" * 110)
    for i, (_, d) in enumerate(entries[:limit]):
        ts = d.get("timestamp")
        ts_str = iso_to_short(ts) if isinstance(ts, str) else ""
        if isinstance(ts, (int, float)):
            from datetime import datetime, timezone
            ts_str = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        print(f"{i+1:<4} {d.get('sessionId', '')[:37]:<38} {ts_str:<22} {d.get('display', '')[:50]}")


COMMANDS = {
    "projects": (cmd_projects, "List project directories"),
    "sessions": (cmd_sessions, "List sessions [--project PATH]"),
    "session": (cmd_session, "Show session details"),
    "messages": (cmd_messages, "List messages in a session"),
    "subagents": (cmd_subagents, "List subagents of a session"),
    "tools": (cmd_tools, "Tool call distribution"),
    "stats": (cmd_stats, "Overall statistics"),
    "history": (cmd_history, "Prompt history"),
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: claude_code_inspect.py <command> [args]\n\nCommands:")
        for name, (_, desc) in COMMANDS.items():
            print(f"  {name:<20} {desc}")
        sys.exit(0)
    cmd = sys.argv[1]
    if cmd not in COMMANDS:
        sys.exit(f"Unknown: {cmd}. Use --help.")
    COMMANDS[cmd][0](sys.argv[2:])
