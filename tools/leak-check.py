#!/usr/bin/env python3
"""Fail if any tracked file (or, with --history, any file ever committed) contains a denied term.

The denylist is private and lives OUTSIDE this repo (default: $LEAK_DENYLIST, else
~/Desktop/Lumi-talk/denylist.txt). One term per line, case-insensitive, whole words;
"!term" marks an allowed exception. Hits are printed with the term masked, so logs don't leak it.
Exit codes: 0 clean, 1 hits found, 3 denylist missing (never passes silently).
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_DENYLIST = Path.home() / "Desktop" / "Lumi-talk" / "denylist.txt"


def load_terms(path: Path) -> tuple[list[tuple[str, re.Pattern]], list[re.Pattern]]:
    denied, allowed = [], []
    for line in path.read_text(encoding="utf-8").splitlines():
        term = line.strip().lower()
        if not term or term.startswith("#"):
            continue
        target = allowed if term.startswith("!") else denied
        term = term.lstrip("!")
        words = r"\s+".join(re.escape(w) for w in term.split())
        left = r"\b" if term[0].isalnum() else ""
        right = r"\b" if term[-1].isalnum() else ""
        pattern = re.compile(left + words + right, re.IGNORECASE)
        target.append(pattern) if target is allowed else target.append((term, pattern))
    return denied, allowed


def mask(term: str) -> str:
    return term[0] + "***"


def scan(name: str, data: bytes, denied, allowed) -> list[str]:
    text = data.decode("latin-1")          # every byte maps to a char: binaries' embedded text is scanned too
    for pattern in allowed:
        text = pattern.sub(lambda m: " " * len(m.group()), text)
    hits = []
    for term, pattern in denied:
        for m in pattern.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            hits.append(f"{name}:{line}: {mask(term)}")
    return hits


def git(repo: Path, *args: str, data: bytes | None = None) -> bytes:
    return subprocess.run(["git", "-C", str(repo), *args], input=data, capture_output=True, check=True).stdout


def tracked(repo: Path):
    for name in git(repo, "ls-files", "-z").decode().split("\0"):
        if name and (repo / name).is_file():
            yield name, (repo / name).read_bytes()


def history(repo: Path):
    for commit in git(repo, "rev-list", "--all").decode().split():
        meta = git(repo, "log", "-1", "--format=%an <%ae>%n%cn <%ce>%n%B", commit)
        yield f"commit {commit[:7]} (author/message)", meta
    objects = git(repo, "rev-list", "--all", "--objects").decode().splitlines()
    for line in objects:
        sha, _, path = line.partition(" ")
        if git(repo, "cat-file", "-t", sha).strip() == b"blob":
            yield f"{path or sha} (history {sha[:7]})", git(repo, "cat-file", "blob", sha)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--denylist", type=Path, default=Path(os.environ.get("LEAK_DENYLIST", DEFAULT_DENYLIST)))
    parser.add_argument("--history", action="store_true", help="also scan every blob ever committed")
    args = parser.parse_args(argv)
    if not args.denylist.is_file():
        print(f"leak-check: denylist not found: {args.denylist}", file=sys.stderr)
        return 3
    denied, allowed = load_terms(args.denylist)
    hits = []
    for name, data in (history(args.repo) if args.history else tracked(args.repo)):
        hits += scan(name, data, denied, allowed)
    for hit in hits:
        print(hit)
    print(f"leak-check: {len(hits)} hit(s)" if hits else "leak-check: clean", file=sys.stderr)
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
