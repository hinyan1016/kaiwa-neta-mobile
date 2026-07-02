# 会話ネタ モバイル（暗号化PWA）

`会話ネタ/` のMarkdownノートをiPhone等のスマホで読むためのWebアプリ。
GitHub Pages で公開するが、**中身は AES-256-GCM で暗号化**されており、
パスフレーズを知らない人には読めない。

- 公開URL: https://hinyan1016.github.io/kaiwa-neta-mobile/
- パスフレーズ: `.passphrase.txt`（このフォルダ・**git管理外**）

## iPhoneでの初回セットアップ

1. Safari で上記URLを開く
2. パスフレーズを入力（「この端末で記憶する」にチェックすると次回から自動）
3. 共有ボタン →「ホーム画面に追加」→ 以降はアプリとして起動できる

## 内容を更新したとき（PC側）

会話ネタの `.md` を追加・編集したら:

```bash
python build_publish.py --push
```

これだけで暗号化→commit→push まで完了。1〜2分でスマホ側に反映される
（アプリの一覧画面を開き直すと最新データを取得する）。

## セキュリティの仕組み

- `data.enc.json` = 全ノートをJSON化 → PBKDF2-SHA256（31万回）で鍵導出 → AES-256-GCM 暗号化
- リポジトリ・Pages 上に平文は一切置かない（このREADMEにも内容は書かない）
- 復号はブラウザ内（WebCrypto）で完結。パスフレーズはどこにも送信されない
- 「この端末で記憶する」は localStorage 保存。共有端末では使わないこと
- ヘッダの 🔒 ボタンで記憶を消去してロックできる

## パスフレーズ変更

`.passphrase.txt` を書き換えて `python build_publish.py --push`。
以降、旧パスフレーズでは復号できなくなる（各端末で再入力が必要）。

## ファイル構成

| ファイル | 役割 |
|---|---|
| `index.html` | アプリ本体（単一ファイル・外部依存なし） |
| `sw.js` | オフラインキャッシュ（データはネットワーク優先） |
| `manifest.webmanifest` / `icon-*.png` | ホーム画面追加用 |
| `build_publish.py` | `../会話ネタ/*.md` → `data.enc.json` 生成・push |
| `data.enc.json` | 暗号化済みノートデータ（これのみ内容物） |
