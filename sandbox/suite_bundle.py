#!/usr/bin/env python3
"""Pack / unpack the private part of the suite as one encrypted file, so the
repository can be public while the instances stay hidden.

    BENCH_KEY=... python sandbox/suite_bundle.py pack      # -> suite.enc
    BENCH_KEY=... python sandbox/suite_bundle.py unpack    # -> instances.yaml, instances/

The bundle holds instances.yaml (Track A names + optima), instances/ (MPS files,
manifest, reference optima, generator seed, PGLib day files) and the private
Track A notes. Encryption: openssl AES-256-CBC with PBKDF2 (available on macOS
and on GitHub runners). The key lives only in the `BENCH_KEY` repository secret
and in your password manager; anyone with the public repo but not the key sees
generators and tooling, not the evaluated instances.
"""
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = ROOT / "suite.enc"
MEMBERS = ["instances.yaml", "instances"]


def key():
    k = os.environ.get("BENCH_KEY")
    if not k:
        sys.exit("BENCH_KEY environment variable is required")
    return k


def pack():
    key()
    with tempfile.TemporaryDirectory() as td:
        tar = Path(td) / "suite.tar.gz"
        with tarfile.open(tar, "w:gz") as tf:
            for m in MEMBERS:
                p = ROOT / m
                if not p.exists():
                    sys.exit(f"missing {m}")
                tf.add(p, arcname=m, filter=lambda ti: None if "__pycache__" in ti.name else ti)
        subprocess.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-salt", "-pass", "env:BENCH_KEY",
                        "-in", str(tar), "-out", str(BUNDLE)], check=True)
    print(f"packed {MEMBERS} -> {BUNDLE.name} ({BUNDLE.stat().st_size / 1e6:.1f} MB)")


def unpack():
    key()
    if not BUNDLE.exists():
        sys.exit(f"{BUNDLE} not found")
    with tempfile.TemporaryDirectory() as td:
        tar = Path(td) / "suite.tar.gz"
        subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-pass", "env:BENCH_KEY",
                        "-in", str(BUNDLE), "-out", str(tar)], check=True)
        with tarfile.open(tar, "r:gz") as tf:
            tf.extractall(ROOT, filter="data")
    print(f"unpacked {MEMBERS} into {ROOT}")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("pack", "unpack"):
        sys.exit(__doc__)
    pack() if sys.argv[1] == "pack" else unpack()
