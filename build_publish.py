#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""会話ネタ/*.md を AES-256-GCM で暗号化して data.enc.json を生成する。

使い方:
  python build_publish.py            # ビルドのみ
  python build_publish.py --push     # ビルド + git commit + push（GitHub Pages更新）

パスフレーズはこのフォルダの .passphrase.txt（git管理外・1行）から読む。
変更したいときは .passphrase.txt を書き換えて --push すれば、次回アプリ側で
新パスフレーズを入力するだけ（アプリの「記憶」は自動で無効になり再入力を求める）。
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

HERE = Path(__file__).resolve().parent
SOURCE_DIR = HERE.parent / "会話ネタ"
OUT_FILE = HERE / "data.enc.json"
PASS_FILE = HERE / ".passphrase.txt"
HASH_FILE = HERE / ".last_content_hash"  # git管理外。無変更時の再push防止用
PBKDF2_ITER = 310_000
JST = timezone(timedelta(hours=9))


def load_passphrase() -> str:
    if not PASS_FILE.is_file():
        sys.exit(f"[エラー] パスフレーズファイルがありません: {PASS_FILE}")
    pw = PASS_FILE.read_text(encoding="utf-8").strip()
    if len(pw) < 8:
        sys.exit("[エラー] パスフレーズは8文字以上にしてください")
    return pw


def first_h1(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def collect_files() -> list[dict]:
    if not SOURCE_DIR.is_dir():
        sys.exit(f"[エラー] ソースフォルダがありません: {SOURCE_DIR}")
    files = []
    for p in sorted(SOURCE_DIR.rglob("*.md")):
        rel = p.relative_to(SOURCE_DIR).as_posix()
        text = p.read_text(encoding="utf-8")
        files.append({
            "path": rel,
            "title": first_h1(text, p.stem),
            "mtime": datetime.fromtimestamp(p.stat().st_mtime, JST).isoformat(timespec="seconds"),
            "content": text,
        })
    return files


def encrypt(payload: dict, passphrase: str) -> dict:
    salt = os.urandom(16)
    iv = os.urandom(12)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=PBKDF2_ITER)
    key = kdf.derive(passphrase.encode("utf-8"))
    plain = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    ct = AESGCM(key).encrypt(iv, plain, None)
    b64 = lambda b: base64.b64encode(b).decode("ascii")
    return {"v": 1, "kdf": "PBKDF2-SHA256", "iter": PBKDF2_ITER,
            "salt": b64(salt), "iv": b64(iv), "ct": b64(ct)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--push", action="store_true", help="ビルド後に git commit & push する")
    args = ap.parse_args()

    passphrase = load_passphrase()
    files = collect_files()

    # ノート内容＋パスフレーズが前回ビルドと同一なら何もしない
    # （暗号化はソルトが毎回変わるため data.enc.json の比較では検知できない）
    digest = hashlib.sha256(
        (passphrase + "\0" + json.dumps(
            [[f["path"], f["content"]] for f in files], ensure_ascii=False
        )).encode("utf-8")
    ).hexdigest()
    if OUT_FILE.is_file() and HASH_FILE.is_file() and HASH_FILE.read_text().strip() == digest:
        print(f"[OK] 変更なし（{len(files)}件・ビルド/push不要）")
        return

    payload = {"generated": datetime.now(JST).isoformat(timespec="seconds"), "files": files}
    OUT_FILE.write_text(json.dumps(encrypt(payload, passphrase), indent=1), encoding="utf-8")
    HASH_FILE.write_text(digest, encoding="utf-8")
    print(f"[OK] {len(files)}件を暗号化 -> {OUT_FILE.name} ({OUT_FILE.stat().st_size:,} bytes)")

    if args.push:
        run = lambda *cmd: subprocess.run(cmd, cwd=HERE, check=True)
        # アプリ本体の変更（index.html/sw.js等）も同時にデプロイされるよう add 対象に含める
        run("git", "add", "data.enc.json", "index.html", "sw.js", "manifest.webmanifest")
        diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=HERE)
        if diff.returncode == 0:
            print("[OK] 変更なし（push不要）")
            return
        stamp = datetime.now(JST).strftime("%Y-%m-%d %H:%M")
        run("git", "commit", "-m", f"content: 会話ネタ更新 {stamp}")
        run("git", "push")
        print("[OK] push 完了（GitHub Pages 反映まで1〜2分）")


if __name__ == "__main__":
    main()
