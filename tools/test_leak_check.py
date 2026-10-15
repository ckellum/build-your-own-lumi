import importlib.util
import subprocess
import zlib
import struct
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("leak_check", Path(__file__).with_name("leak-check.py"))
leak_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(leak_check)


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    git(r, "init", "-q")
    git(r, "config", "user.email", "t@example.com")
    git(r, "config", "user.name", "t")
    return r


@pytest.fixture
def denylist(tmp_path):
    p = tmp_path / "deny.txt"
    p.write_text("# comment\nzebraville\nsecret room\nquokka\n!xquokka\n")
    return p


def commit(repo, name, data):
    path = repo / name
    path.write_bytes(data if isinstance(data, bytes) else data.encode())
    git(repo, "add", name)
    git(repo, "commit", "-qm", "x")


def test_denied_word_in_a_tracked_file_fails_and_is_masked(repo, denylist, capsys):
    commit(repo, "a.txt", "Hello from Zebraville\n")
    assert leak_check.main(["--repo", str(repo), "--denylist", str(denylist)]) == 1
    out = capsys.readouterr().out
    assert "a.txt:1" in out and "z***" in out and "zebraville" not in out.lower()


def test_clean_repo_passes(repo, denylist):
    commit(repo, "a.txt", "Hello from Example Con\n")
    assert leak_check.main(["--repo", str(repo), "--denylist", str(denylist)]) == 0


def test_missing_denylist_never_passes(repo, tmp_path):
    commit(repo, "a.txt", "fine\n")
    assert leak_check.main(["--repo", str(repo), "--denylist", str(tmp_path / "nope.txt")]) == 3


def test_exception_allows_the_public_github_name(repo, denylist):
    commit(repo, "a.md", "See github.com/xquokka/project\n")
    assert leak_check.main(["--repo", str(repo), "--denylist", str(denylist)]) == 0


def test_whole_words_only(repo, denylist):
    commit(repo, "a.txt", "atzebraville and secret roomy\n")
    assert leak_check.main(["--repo", str(repo), "--denylist", str(denylist)]) == 0


def test_phrases_match_across_case_and_spacing(repo, denylist):
    commit(repo, "a.txt", "meet in the Secret  Room\n")
    assert leak_check.main(["--repo", str(repo), "--denylist", str(denylist)]) == 1


def png_with_text(key, value):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 0)
    idat = zlib.compress(b"\x00\x00")
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"tEXt", key + b"\x00" + value)
            + chunk(b"IDAT", idat) + chunk(b"IEND", b""))


def test_metadata_inside_an_image_is_scanned(repo, denylist):
    commit(repo, "pic.png", png_with_text(b"Location", b"Zebraville office"))
    assert leak_check.main(["--repo", str(repo), "--denylist", str(denylist)]) == 1


def test_history_catches_a_word_deleted_later(repo, denylist):
    commit(repo, "a.txt", "Zebraville\n")
    commit(repo, "a.txt", "clean now\n")
    assert leak_check.main(["--repo", str(repo), "--denylist", str(denylist)]) == 0
    assert leak_check.main(["--repo", str(repo), "--denylist", str(denylist), "--history"]) == 1


def test_history_scans_commit_authors_and_messages(repo, denylist):
    commit(repo, "a.txt", "clean\n")
    git(repo, "-c", "user.name=Pat Quokka", "commit", "--allow-empty", "-qm", "clean message")
    assert leak_check.main(["--repo", str(repo), "--denylist", str(denylist), "--history"]) == 1


def test_history_scans_commit_messages(repo, denylist):
    commit(repo, "a.txt", "clean\n")
    git(repo, "commit", "--allow-empty", "-qm", "notes from zebraville")
    assert leak_check.main(["--repo", str(repo), "--denylist", str(denylist), "--history"]) == 1


def test_file_names_are_scanned(repo, denylist):
    commit(repo, "zebraville-notes.txt", "clean\n")
    assert leak_check.main(["--repo", str(repo), "--denylist", str(denylist)]) == 1


def test_compressed_png_text_is_scanned(repo, denylist):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    ztxt = b"Comment\x00\x00" + zlib.compress(b"shot in Zebraville")
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 0))
           + chunk(b"zTXt", ztxt) + chunk(b"IDAT", zlib.compress(b"\x00\x00")) + chunk(b"IEND", b""))
    commit(repo, "pic.png", png)
    assert leak_check.main(["--repo", str(repo), "--denylist", str(denylist)]) == 1


def test_annotated_tag_messages_are_scanned(repo, denylist):
    commit(repo, "a.txt", "clean\n")
    git(repo, "tag", "-a", "v1", "-m", "release from zebraville")
    assert leak_check.main(["--repo", str(repo), "--denylist", str(denylist), "--history"]) == 1
