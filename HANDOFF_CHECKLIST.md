# 板監視システム 引き継ぎチェックリスト

**前のセッション完了日**: 2026-05-14  
**新セッション開始予定**: 次のチャットルーム  
**プロジェクト**: trading-system / board_monitor

---

## 📋 引き継ぎドキュメント

新しいセッションで最初に確認するべきファイル（上から順に読むこと）：

### 1️⃣ **QUICK_START.md** ⭐ 最初にこれを読む
- 1分で理解する現状
- すぐやること（5分）
- よくあるトラブル
- 場所: `C:\Users\flute\OneDrive\デスクトップ\trading-system\QUICK_START.md`

### 2️⃣ **board_monitor/README.md** ⭐ 次にこれを読む
- プロジェクト概要
- ファイル構成
- UIレイアウト詳細
- 実行方法（テスト、本番）
- トラブルシューティング
- 場所: `board_monitor/README.md`

### 3️⃣ **BOARD_MONITOR_HANDOFF.md** 詳細な技術情報
- 実装の重要ポイント
- expand=False の説明（5つの場所）
- WebSocket データフロー
- 既知の問題と対策
- 次のステップ
- 場所: `C:\Users\flute\OneDrive\デスクトップ\trading-system\BOARD_MONITOR_HANDOFF.md`

### 4️⃣ **memory/board_monitor_status.md** プロジェクトメモリ
- 設計仕様（確定）
- 実装状況
- 参考にした実在ツール
- 場所: `C:\Users\flute\.claude\projects\C--Users-flute-OneDrive-------\memory\board_monitor_status.md`

---

## ✅ チェック項目（新セッション開始時）

### ファイル確認
- [ ] `board_monitor/` ディレクトリが存在
- [ ] `board_monitor/app.py` が存在
- [ ] `board_monitor/gui/main_window.py` が存在
- [ ] `board_monitor/gui/board_panel.py` が存在
- [ ] `board_monitor/gui/detail_window.py` が存在
- [ ] `board_monitor/kabu_api/websocket_client.py` が存在
- [ ] `board_monitor/test_ui.py` が存在
- [ ] `board_monitor/README.md` が存在
- [ ] `QUICK_START.md` が存在（このディレクトリ）
- [ ] `BOARD_MONITOR_HANDOFF.md` が存在

### 動作確認
- [ ] Python 3.11以上がインストール済み
- [ ] `pip install -r board_monitor/requirements.txt` が実行可能
- [ ] `python board_monitor/test_ui.py` が実行可能（UIテスト）
- [ ] ダミーデータが表示される（5つの板が見える）
- [ ] 色分けが正しい（売=赤、買=緑）
- [ ] フォントが小さく読める（6pt）

### メモリ確認
- [ ] `memory/board_monitor_status.md` に現在の実装状況が記録されている

---

## 🚀 新セッション開始手順

### ステップ1: ドキュメント確認（5分）
```
1. QUICK_START.md を読む
2. board_monitor/README.md を読む
3. BOARD_MONITOR_HANDOFF.md を読む（必要な部分）
```

### ステップ2: UIテスト実行（5分）
```bash
cd board_monitor
python test_ui.py
```
- [ ] 上下2段が表示される
- [ ] 各段に5つの板が横に並ぶ
- [ ] 色分けが正しい
- [ ] クリック可能

### ステップ3: kabuStation API テスト（10分）
```bash
# .env ファイル作成
echo KABU_API_PASSWORD=your_password > .env

# 実行
python board_monitor/app.py
```
- [ ] WebSocket が接続される
- [ ] リアルタイムデータが表示される
- [ ] フラッシュが動作する

### ステップ4: メモリ更新（新セッション終了時）
- [ ] 進捗状況を `memory/board_monitor_status.md` に記録

---

## 📊 現在の実装状況（スナップショット）

### ✅ 完成した機能
- **メインウィンドウ**: 上下2段×5タブ（最大50銘柄）
- **板パネル（v2）**: マネックス証券パターン（売り5段+買い5段）
- **インタラクション**: 左クリック（詳細）、ダブルクリック（登録）
- **色分け**: 売=赤系、買=緑系、フラッシュ=ピンク/水色
- **WebSocket**: kabuStation API との連携実装
- **スレッド**: メインスレッド（GUI）+ データスレッド（WebSocket）

### 🎨 UIの見た目

```
【1つの板パネル】
┌──────────────────┐
│ 9984 1234.50 △2% │ <- 銘柄コード + 現在値 + 騰落率
│始-- 高-- 安-- 高v │ <- 情報行
├──────────────────┤
│ 売1 1235.50  100 │ <- 売り気配5段
│ 売2 1235.40   50 │
│ 売3 1235.30  150 │
│ 売4 1235.20   75 │
│ 売5 1235.10  200 │
├──────────────────┤
│ 買1 1234.90  200 │ <- 買い気配5段
│ 買2 1234.80   75 │
│ 買3 1234.70  150 │
│ 買4 1234.60   50 │
│ 買5 1234.50  100 │
└──────────────────┘
```

### 🔴 重要な技術ポイント

**expand=False が5箇所に必須:**
1. 上段セクション: `upper_frame.pack(fill=tk.X, expand=False)`
2. 下段セクション: `lower_frame.pack(fill=tk.X, expand=False)`
3. 板フレーム: `boards_frame.pack(fill=tk.X, expand=False)`
4. ヘッダー行: `header_frame.pack(fill=tk.X, expand=False)`
5. 情報行: `info_frame.pack(fill=tk.X, expand=False)`

**ルール:** セクション・パネル・行はすべて `expand=False`

---

## 📝 ファイル説明

### board_monitor/ フォルダ

| ファイル | 説明 |
|---------|------|
| `app.py` | メインアプリケーション（Tkinter起動、WebSocket連携） |
| `gui/main_window.py` | メインウィンドウ（上下2段、各5タブ） |
| `gui/board_panel.py` | 個別の板パネル（マネックス証券風） |
| `gui/detail_window.py` | 詳細ウィンドウ（左：銘柄情報、右：板） |
| `kabu_api/websocket_client.py` | kabuStation WebSocket クライアント |
| `kabu_api/board_parser.py` | 板データパーサー（parse_kabu_board） |
| `test_ui.py` | UIテスト用（ダミーデータ） |
| `requirements.txt` | 依存パッケージ |
| `README.md` | 詳細説明 |

### トップレベル（trading-system/）

| ファイル | 説明 |
|---------|------|
| `QUICK_START.md` | 1分で理解する現状 |
| `BOARD_MONITOR_HANDOFF.md` | 技術詳細と次のステップ |
| `HANDOFF_CHECKLIST.md` | このファイル |
| `SPEC.md` | 前日検討システムの仕様 |
| `CLAUDE.md` | プロジェクト全体のルール |

---

## 🔗 関連するプロジェクト

このプロジェクトは、以下の部分システムの一部です：

### 1. 前日検討システム（scanning_system）
- J-Quants API でスコアリング
- 候補銘柄をスクリーニング
- **板監視システムと統合予定**: 前日スコアを板画面に表示

### 2. 出来高監視システム（volume_monitor）
- 出来高急増の検出
- アラート通知
- **板監視システムと統合予定**: 出来高の急増を検出

### 3. 上昇サイン通知（price_alert）
- 特定の価格に達したときのアラート
- **板監視システムと統合予定**: リアルタイム監視結果をアラート

---

## 🎯 次のセッションの優先順位

### 優先度 🔴 高
1. test_ui.py で UI確認（崩れていないか）
2. kabuStation API 実連携テスト
3. 本番銘柄登録テスト

### 優先度 🟡 中
1. パフォーマンス検証（50銘柄同時表示）
2. メモリ使用量確認
3. 応答速度の最適化

### 優先度 🟢 低
1. 前日検討システムとの統合
2. 通知機能の追加
3. UI のカスタマイズ

---

## 📞 問い合わせ先

このドキュメントについてわからないことがあれば：

1. **QUICK_START.md** を再読
2. **board_monitor/README.md** を確認
3. **BOARD_MONITOR_HANDOFF.md** で技術詳細を確認
4. **memory/board_monitor_status.md** でプロジェクト状況を確認

---

**秀長より:**  
前のセッションで、実在の証券ツール（マネックス証券マルチボード500など）を参考にして、expand=False の問題を完全に解決しました。UIレイアウトはコンパクトで実用的です。次のセッションでも自信を持って進めてください。頑張ってください！🙏
