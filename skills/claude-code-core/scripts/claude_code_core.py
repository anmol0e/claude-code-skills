#!/usr/bin/env python3
"""
claude_code_core.py — Shared foundation for Claude Code session skills.

Single source of truth for:
  - Cross-platform ~/.claude/ path detection
  - Project directory discovery and path decoding
  - Session JSONL file discovery (root + subagent)
  - JSONL line parsing and session metadata extraction
  - Subagent meta.json loading

No external dependencies — stdlib only.
"""
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

__version__ = "1.0.0"


# ─── Path Detection ──────────────────────────────────────────────────────────

def claude_home():
    """Cross-platform ~/.claude/ directory."""
    return os.path.expanduser("~/.claude")


def projects_dir():
    """Path to ~/.claude/projects/."""
    return os.path.join(claude_home(), "projects")


def encode_project_path(abs_path):
    """Encode an absolute path as Claude Code does: / → -"""
    return abs_path.replace("/", "-")


def decode_project_path(encoded):
    """Decode a Claude Code project directory name back to absolute path."""
    if encoded.startswith("-"):
        return "/" + encoded[1:].replace("-", "/")
    return encoded.replace("-", "/")


# ─── Session Discovery ───────────────────────────────────────────────────────

def list_project_dirs():
    """List all project directories under ~/.claude/projects/."""
    pd = projects_dir()
    if not os.path.isdir(pd):
        return []
    return [
        (d, decode_project_path(d), os.path.join(pd, d))
        for d in sorted(os.listdir(pd))
        if os.path.isdir(os.path.join(pd, d)) and not d.startswith(".")
    ]


def list_sessions(project_encoded_dir):
    """List root session JSONL files in a project directory.
    Returns list of (session_id, file_path, line_count, size_bytes)."""
    sessions = []
    for f in sorted(os.listdir(project_encoded_dir)):
        if f.endswith(".jsonl") and not f.startswith("agent-"):
            fp = os.path.join(project_encoded_dir, f)
            sid = f.replace(".jsonl", "")
            lines = sum(1 for _ in open(fp))
            size = os.path.getsize(fp)
            sessions.append((sid, fp, lines, size))
    return sessions


def list_subagents(project_encoded_dir, session_id):
    """List subagent sessions for a root session.
    Returns list of (agent_name, jsonl_path, meta_path, meta_data)."""
    subdir = os.path.join(project_encoded_dir, session_id, "subagents")
    if not os.path.isdir(subdir):
        return []
    agents = []
    for f in sorted(os.listdir(subdir)):
        if f.endswith(".jsonl"):
            jsonl_path = os.path.join(subdir, f)
            meta_path = jsonl_path.replace(".jsonl", ".meta.json")
            meta = {}
            if os.path.exists(meta_path):
                with open(meta_path) as mf:
                    meta = json.load(mf)
            agent_name = f.replace(".jsonl", "")
            agents.append((agent_name, jsonl_path, meta_path, meta))
    return agents


# ─── JSONL Parsing ────────────────────────────────────────────────────────────

def parse_jsonl(filepath):
    """Parse a JSONL file, yielding (line_number, parsed_dict) for each valid line."""
    with open(filepath) as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield i, json.loads(line)
            except json.JSONDecodeError:
                continue


def extract_session_metadata(filepath):
    """Extract key metadata from a session JSONL file without loading all lines."""
    meta = {
        "session_id": os.path.basename(filepath).replace(".jsonl", ""),
        "title": None,
        "mode": None,
        "permission_mode": None,
        "version": None,
        "cwd": None,
        "git_branch": None,
        "first_timestamp": None,
        "last_timestamp": None,
        "user_count": 0,
        "assistant_count": 0,
        "tool_use_count": 0,
        "total_lines": 0,
    }
    for _, d in parse_jsonl(filepath):
        meta["total_lines"] += 1
        t = d.get("type")
        if t == "ai-title":
            meta["title"] = d.get("aiTitle")
        elif t == "mode":
            meta["mode"] = d.get("mode")
        elif t == "permission-mode":
            meta["permission_mode"] = d.get("permissionMode")
        elif t == "user":
            meta["user_count"] += 1
            if not meta["version"]:
                meta["version"] = d.get("version")
            if not meta["cwd"]:
                meta["cwd"] = d.get("cwd")
            if not meta["git_branch"]:
                meta["git_branch"] = d.get("gitBranch")
            ts = d.get("timestamp")
            if ts:
                if not meta["first_timestamp"]:
                    meta["first_timestamp"] = ts
                meta["last_timestamp"] = ts
        elif t == "assistant":
            meta["assistant_count"] += 1
            content = d.get("message", {}).get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        meta["tool_use_count"] += 1
            ts = d.get("timestamp")
            if ts:
                meta["last_timestamp"] = ts
    return meta


def iso_to_short(iso_str):
    """Convert ISO timestamp to short display format."""
    if not iso_str:
        return ""
    return iso_str[:19].replace("T", " ")
