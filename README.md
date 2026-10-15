# Build Your Own Lumi

A voice concierge you can build on the computer you already have: scan a badge (or press Enter),
ask a question out loud, and Lumi answers out loud, with a talking face.

**Guide:** https://ckellum.github.io/build-your-own-lumi/

- `minilumi/`: the starter kit (Python). Start with [minilumi/README.md](minilumi/README.md).
- `index.html`, `css/`, `js/`: the guide site (plain HTML, no build step).
- `tools/leak-check.py`: the pre-push check that keeps private data out of this repo.

Three ways to run it: **workstation** (big local models), **laptop** (32 GB RAM or a mid-range GPU),
or **cloud** (no GPU, API keys). See [minilumi/TESTED.md](minilumi/TESTED.md) for what we actually ran.

Built with [Claude Code](https://claude.com/claude-code). MIT licensed.
