#!/usr/bin/env python3
"""PreToolUse hook (Bash): guard `git commit` before it runs.

1. Subject line over 72 chars (Conventional Commits, ~/.claude/CLAUDE.md).
2. Placeholder author identity: a repo-local `user.email` (e.g. `your@email.com`)
   silently overrides the global one, and the bad address is only visible after
   the commits are pushed. Fixing it afterwards costs a history rewrite.

Only the FIRST -m / --message= after each `git commit` is the subject (later ones are body
paragraphs). Heredoc / -F shapes and unbalanced quotes are left alone.
"""
import json
import shlex
import subprocess
import sys

LIMIT = 72

PLACEHOLDER_EMAILS = {
    "your@email.com",
    "you@example.com",
    "your.email@example.com",
    "youremail@example.com",
    "user@example.com",
    "email@example.com",
    "name@example.com",
    "changeme@example.com",
}
PLACEHOLDER_NAMES = {"your name", "yourname", "firstname lastname", "changeme"}


def subjects(command: str) -> list[str]:
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return []
    found: list[str] = []
    armed = False
    for i, tok in enumerate(tokens):
        if tok == "git" and i + 1 < len(tokens) and tokens[i + 1] == "commit":
            armed = True
            continue
        if not armed:
            continue
        if tok == "-m" and i + 1 < len(tokens):
            found.append(tokens[i + 1])
            armed = False
        elif tok.startswith("--message="):
            found.append(tok[len("--message="):])
            armed = False
        elif tok in ("&&", "||", ";", "|"):
            armed = False
    return found


def git_config(cwd: str, key: str) -> str | None:
    try:
        run = subprocess.run(
            ["git", "-C", cwd, "config", "--get", key],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return None
    return run.stdout.strip()


def identity_problem(cwd: str) -> str | None:
    if not cwd:
        return None
    email = git_config(cwd, "user.email")
    if email is None:
        return None
    name = git_config(cwd, "user.name") or ""
    if email.lower() in PLACEHOLDER_EMAILS or (email and "@" not in email):
        return (
            f"author email is the placeholder {email!r}. Set the real one before committing: "
            f"`git config user.email <address>` (repo-local config overrides ~/.gitconfig; "
            f"check with `git config --show-origin --get-all user.email`)."
        )
    if name.lower() in PLACEHOLDER_NAMES:
        return (
            f"author name is the placeholder {name!r}. Set the real one: "
            f"`git config user.name '<Name>'`."
        )
    return None


def deny(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    command = (data.get("tool_input") or {}).get("command") or ""
    if "git commit" not in command:
        return

    for subject in subjects(command):
        first_line = subject.splitlines()[0] if subject else ""
        if len(first_line) > LIMIT:
            deny(
                f"commit subject is {len(first_line)} chars, limit is {LIMIT} "
                f"(Conventional Commits, ~/.claude/CLAUDE.md): shorten it. Nothing ran, re-run the whole "
                f"command (git add included). Subject: {first_line!r}"
            )
            return

    problem = identity_problem(data.get("cwd") or "")
    if problem:
        deny(f"commit blocked: {problem} Nothing ran, re-run the whole command afterwards.")


if __name__ == "__main__":
    main()
