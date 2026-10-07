#!/usr/bin/env python3
"""
claude_code_export.py — Export Claude Code sessions to AgentLog v0.2.0 + ASI v1.

Usage:
  python3 claude_code_export.py --list
  python3 claude_code_export.py --export <sessionId> [--outdir DIR]
  python3 claude_code_export.py --export <sessionId> --no-agentlog --no-asi
  python3 claude_code_export.py --verify <file>

Output:
  <sid>.raw_session.jsonl   — original JSONL (copied verbatim, lossless)
  <sid>.agentlog.jsonl      — AgentLog v0.2.0 events
  <sid>.asi.jsonl           — ASI v1 normalized parts
"""
import json, sys, os, argparse, hashlib
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "claude-code-core", "scripts"))
from claude_code_core import (
    list_project_dirs, list_sessions, list_subagents,
    parse_jsonl, extract_session_metadata, claude_home,
)

__version__ = "1.0.0"


# ─── AgentLog v0.2.0 ─────────────────────────────────────────────────────────

def session_to_agentlog(filepath, meta):
    """Convert a Claude Code session JSONL to AgentLog v0.2.0 events."""
    events = []
    all_commits = []
    model = None
    eid_counter = [0]

    def eid():
        eid_counter[0] += 1
        return f"{meta['session_id']}-{eid_counter[0]}"

    for _, d in parse_jsonl(filepath):
        t = d.get("type")
        ts = d.get("timestamp") or datetime.now(tz=timezone.utc).isoformat()

        if t == "user":
            msg = d.get("message", {})
            content = msg.get("content", "")
            text = content if isinstance(content, str) else ""
            if isinstance(content, list):
                text = " ".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
            events.append({
                "type": "message", "id": eid(), "timestamp": ts,
                "role": "user", "content": text,
                "properties": {
                    "claude:uuid": d.get("uuid"),
                    "claude:cwd": d.get("cwd"),
                    "claude:gitBranch": d.get("gitBranch"),
                    "claude:origin": d.get("origin"),
                },
            })

        elif t == "assistant":
            msg = d.get("message", {})
            if not model:
                model = msg.get("model")
            content = msg.get("content", [])
            if not isinstance(content, list):
                continue

            for block in content:
                if not isinstance(block, dict):
                    continue
                bt = block.get("type")

                if bt == "thinking":
                    events.append({
                        "type": "reasoning", "id": eid(), "timestamp": ts,
                        "intent": block["thinking"][:200] if block.get("thinking") else "",
                        "rationale": block.get("thinking", ""),
                        "alternatives": [],
                        "properties": {"claude:signature": block.get("signature")},
                    })

                elif bt == "text":
                    events.append({
                        "type": "message", "id": eid(), "timestamp": ts,
                        "role": "assistant", "content": block.get("text", ""),
                        "properties": {"claude:uuid": d.get("uuid"), "claude:effort": d.get("effort")},
                    })

                elif bt == "tool_use":
                    events.append({
                        "type": "toolCall", "id": eid(), "timestamp": ts,
                        "name": block.get("name", "unknown"),
                        "input": block.get("input", {}),
                        "output": None, "status": "success", "parentId": None, "summary": None,
                        "properties": {"claude:callId": block.get("id")},
                    })

                elif bt == "tool_result":
                    result_content = block.get("content", "")
                    if isinstance(result_content, list):
                        result_content = " ".join(
                            b.get("text", "") for b in result_content
                            if isinstance(b, dict) and b.get("type") == "text"
                        )
                    events.append({
                        "type": "toolCall", "id": eid(), "timestamp": ts,
                        "name": "tool_result",
                        "input": {"tool_use_id": block.get("tool_use_id")},
                        "output": result_content if isinstance(result_content, str) else json.dumps(result_content, default=str),
                        "status": "error" if block.get("is_error") else "success",
                        "properties": {},
                    })

        elif t == "system":
            if d.get("subtype") == "turn_duration":
                events.append({
                    "type": "message", "id": eid(), "timestamp": ts,
                    "role": "system",
                    "content": f"Turn duration: {d.get('durationMs')}ms",
                    "properties": {"claude:subtype": d.get("subtype")},
                })

    msg_count = sum(1 for e in events if e["type"] == "message")
    tool_count = sum(1 for e in events if e["type"] == "toolCall")

    return {
        "specVersion": "0.2.0", "id": meta["session_id"],
        "startTime": meta.get("first_timestamp"),
        "endTime": meta.get("last_timestamp"),
        "status": "completed",
        "agent": {"name": "Claude Code", "version": meta.get("version"), "model": model, "properties": {}},
        "project": {"name": "", "workingDirectory": meta.get("cwd"), "properties": {}},
        "events": events,
        "metrics": {
            "messageCount": msg_count, "toolCallCount": tool_count,
            "properties": {},
        },
        "properties": {"claude:mode": meta.get("mode")},
    }


# ─── ASI v1 ──────────────────────────────────────────────────────────────────

def session_to_asi(filepath, meta):
    """Convert a Claude Code session JSONL to ASI v1 normalized messages."""
    messages = []

    for _, d in parse_jsonl(filepath):
        t = d.get("type")
        if t == "user":
            msg = d.get("message", {})
            content = msg.get("content", "")
            parts = []
            if isinstance(content, str):
                parts.append({"kind": "text", "text": content})
            elif isinstance(content, list):
                for b in content:
                    if isinstance(b, dict) and b.get("type") == "text":
                        parts.append({"kind": "text", "text": b.get("text", "")})
            messages.append({
                "id": d.get("uuid"), "role": "user",
                "created_at": d.get("timestamp"), "parts": parts,
            })

        elif t == "assistant":
            msg = d.get("message", {})
            content = msg.get("content", [])
            if not isinstance(content, list):
                continue
            parts = []
            for block in content:
                if not isinstance(block, dict):
                    continue
                bt = block.get("type")
                if bt == "thinking":
                    parts.append({
                        "kind": "reasoning", "text": block.get("thinking", ""),
                        "signature": block.get("signature"),
                    })
                elif bt == "text":
                    parts.append({"kind": "text", "text": block.get("text", "")})
                elif bt == "tool_use":
                    parts.append({
                        "kind": "tool_call", "call_id": block.get("id"),
                        "name": block.get("name", ""), "arguments": block.get("input", {}),
                    })
                elif bt == "tool_result":
                    rc = block.get("content", "")
                    if isinstance(rc, list):
                        rc = " ".join(b.get("text", "") for b in rc if isinstance(b, dict))
                    parts.append({
                        "kind": "tool_result", "call_id": block.get("tool_use_id"),
                        "output": rc if isinstance(rc, str) else json.dumps(rc, default=str),
                        "is_error": block.get("is_error", False),
                    })
            messages.append({
                "id": d.get("uuid"), "role": "assistant",
                "created_at": d.get("timestamp"), "parts": parts,
            })

    return {
        "session": {
            "id": meta["session_id"], "title": meta.get("title"),
            "created_at": meta.get("first_timestamp"),
            "updated_at": meta.get("last_timestamp"),
            "model": None, "cwd": meta.get("cwd"),
        },
        "messages": messages,
    }


# ─── Export ───────────────────────────────────────────────────────────────────

def find_session_file(sid):
    for _, _, proj_path in list_project_dirs():
        for s_id, fp, _, _ in list_sessions(proj_path):
            if s_id == sid or s_id.startswith(sid):
                return fp, proj_path, s_id
    return None, None, None


def export_session(sid, outdir, want_agentlog=True, want_asi=True):
    fp, proj_path, full_sid = find_session_file(sid)
    if not fp:
        sys.exit(f"Session not found: {sid}")

    meta = extract_session_metadata(fp)
    os.makedirs(outdir, exist_ok=True)
    written = []
    exported_at = datetime.now(tz=timezone.utc).isoformat()

    # 1. Raw copy (verbatim JSONL — the lossless source)
    import shutil
    raw_file = os.path.join(outdir, f"{full_sid}.raw_session.jsonl")
    shutil.copy2(fp, raw_file)
    written.append(raw_file)
    print(f"Session: {meta.get('title') or '(untitled)'} ({meta['total_lines']} lines)")

    # Copy subagent files too
    subs = list_subagents(proj_path, full_sid)
    if subs:
        sub_dir = os.path.join(outdir, f"{full_sid}.subagents")
        os.makedirs(sub_dir, exist_ok=True)
        for name, jsonl_p, meta_p, _ in subs:
            shutil.copy2(jsonl_p, os.path.join(sub_dir, os.path.basename(jsonl_p)))
            if os.path.exists(meta_p):
                shutil.copy2(meta_p, os.path.join(sub_dir, os.path.basename(meta_p)))
        print(f"  + {len(subs)} subagent sessions copied")

    # 2. AgentLog v0.2.0
    if want_agentlog:
        al = session_to_agentlog(fp, meta)
        al_file = os.path.join(outdir, f"{full_sid}.agentlog.jsonl")
        with open(al_file, "w") as f:
            envelope = {k: v for k, v in al.items() if k != "events"}
            envelope["type"] = "session"
            f.write(json.dumps(envelope, default=str, ensure_ascii=False) + "\n")
            for event in al["events"]:
                f.write(json.dumps(event, default=str, ensure_ascii=False) + "\n")
        written.append(al_file)
        print(f"  AgentLog: {al['metrics']['messageCount']} messages, {al['metrics']['toolCallCount']} tool calls")

    # 3. ASI v1
    if want_asi:
        asi = session_to_asi(fp, meta)
        asi_file = os.path.join(outdir, f"{full_sid}.asi.jsonl")
        with open(asi_file, "w") as f:
            f.write(json.dumps({
                "asi_version": "1.0", "type": "session", "session": asi["session"],
                "exported_at": exported_at,
            }, default=str, ensure_ascii=False) + "\n")
            for msg in asi["messages"]:
                f.write(json.dumps({"type": "message", **msg}, default=str, ensure_ascii=False) + "\n")
        written.append(asi_file)
        print(f"  ASI: {len(asi['messages'])} messages")

    for fp in written:
        print(f"  Wrote: {fp}")


def verify(path):
    if path.endswith(".raw_session.jsonl"):
        lines = list(parse_jsonl(path))
        types = set(d.get("type") for _, d in lines)
        print(f"OK [raw]: {len(lines)} lines, types={sorted(types)}")
    elif path.endswith(".agentlog.jsonl"):
        lines = [json.loads(l) for l in open(path) if l.strip()]
        if lines and lines[0].get("specVersion") == "0.2.0":
            events = lines[1:]
            print(f"OK [agentlog]: {len(events)} events, session={lines[0].get('id')}")
        else:
            print("INVALID: bad agentlog format")
            sys.exit(1)
    elif path.endswith(".asi.jsonl"):
        lines = [json.loads(l) for l in open(path) if l.strip()]
        if lines and lines[0].get("asi_version", "").startswith("1."):
            msgs = [l for l in lines[1:] if l.get("type") == "message"]
            print(f"OK [asi]: {len(msgs)} messages, session={lines[0].get('session', {}).get('title')}")
        else:
            print("INVALID: bad ASI format")
            sys.exit(1)
    else:
        print(f"Unknown format: {path}")
        sys.exit(1)


def cmd_list():
    for _, decoded, proj_path in list_project_dirs():
        sessions = list_sessions(proj_path)
        if not sessions:
            continue
        print(f"Project: {decoded}")
        for sid, fp, lines, size in sessions:
            meta = extract_session_metadata(fp)
            subs = len(list_subagents(proj_path, sid))
            print(f"  {sid}  {meta.get('title') or '?':<40}  {lines} lines  {subs} subs")
        print()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Claude Code session exporter (raw + AgentLog + ASI)")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--export", metavar="SESSION_ID")
    ap.add_argument("--outdir", default=os.path.expanduser("~/claude_exports"))
    ap.add_argument("--no-agentlog", action="store_true")
    ap.add_argument("--no-asi", action="store_true")
    ap.add_argument("--verify", metavar="FILE")
    a = ap.parse_args()

    if a.verify:
        verify(a.verify)
    elif a.list:
        cmd_list()
    elif a.export:
        export_session(a.export, a.outdir, want_agentlog=not a.no_agentlog, want_asi=not a.no_asi)
    else:
        ap.print_help()
