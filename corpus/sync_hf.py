"""Keep the Hugging Face dataset in step with this repo.

The Hub copy is a separate store, so it drifts the moment the corpus is rebuilt
or the card is edited here. That drift is silent and it is the dangerous kind:
the public copy keeps claiming counts the data no longer has.

Two modes:

  python corpus/sync_hf.py --check    compare local files against the Hub; no token
                                      needed, exits non-zero if anything differs
  python corpus/sync_hf.py            upload whatever differs (needs a write token)

`--check` reads the Hub over plain HTTPS, so CI can run it on every release
without holding a credential.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = "kishormorol/banglachhanda"
ROOT = Path(__file__).resolve().parent.parent

# local path -> path in the dataset repo
FILES = {
    "hf/README.md": "README.md",
    "CITATION.cff": "CITATION.cff",
    "corpus/poems.jsonl": "data/poems.jsonl",
    "corpus/pilot.jsonl": "data/pilot.jsonl",
    "docs/annotation-guide-v0.1.html": "docs/annotation-guide-v0.1.html",
}

RAW = "https://huggingface.co/datasets/{repo}/raw/main/{path}"
RESOLVE = "https://huggingface.co/datasets/{repo}/resolve/main/{path}"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def remote_bytes(path: str) -> bytes | None:
    """Fetch a file from the Hub, or None when it is not there yet.

    Large files are served as an LFS pointer by /raw, so fall back to /resolve,
    which always returns the content itself.
    """
    for template in (RAW, RESOLVE):
        url = template.format(repo=REPO, path=path)
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                body = response.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            raise
        if body.startswith(b"version https://git-lfs"):
            continue        # an LFS pointer; try /resolve
        return body
    return body


def compare() -> list[tuple[str, str, str]]:
    """Returns (local_path, remote_path, state) for every tracked file."""
    rows = []
    for local, remote in FILES.items():
        local_path = ROOT / local
        if not local_path.exists():
            rows.append((local, remote, "MISSING LOCALLY"))
            continue
        local_bytes = local_path.read_bytes()
        try:
            hub_bytes = remote_bytes(remote)
        except Exception as exc:                    # noqa: BLE001
            rows.append((local, remote, f"ERROR {exc}"))
            continue
        if hub_bytes is None:
            rows.append((local, remote, "NOT ON HUB"))
        elif digest(hub_bytes) == digest(local_bytes):
            rows.append((local, remote, "in sync"))
        else:
            rows.append((local, remote, "DRIFTED"))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report drift, upload nothing")
    args = ap.parse_args()

    rows = compare()
    width = max(len(r[0]) for r in rows)
    for local, remote, state in rows:
        marker = " " if state == "in sync" else "!"
        print(f" {marker} {local:<{width}}  ->  {remote:<32} {state}")

    stale = [r for r in rows if r[2] not in ("in sync",)]
    if args.check:
        if stale:
            print(f"\n{len(stale)} file(s) differ from the Hub. Run: python corpus/sync_hf.py")
            return 1
        print("\nHub copy matches this repo.")
        return 0

    if not stale:
        print("\nNothing to upload.")
        return 0

    token = os.environ.get("HF_TOKEN")
    if not token:
        token_file = Path.home() / ".cache/huggingface/token"
        if token_file.exists():
            token = token_file.read_text().strip()
    if not token:
        print("\nNo HF token found (set HF_TOKEN or log in with the Hub CLI).", file=sys.stderr)
        return 2

    from huggingface_hub import HfApi                # imported late: --check needs no dependency

    api = HfApi(token=token)
    for local, remote, state in stale:
        if state == "MISSING LOCALLY":
            print(f"skipping {local}: not in this working tree")
            continue
        api.upload_file(
            path_or_fileobj=str(ROOT / local),
            path_in_repo=remote,
            repo_id=REPO,
            repo_type="dataset",
            commit_message=f"Sync {remote} from the repo",
        )
        print(f"uploaded {remote}")

    print("\nRe-checking…")
    for local, remote, state in compare():
        if state != "in sync":
            print(f" ! {remote}: {state}")
            return 1
    print("Hub copy matches this repo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
