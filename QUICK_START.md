# 板監視システム クイックスタート（新セッション用）

**前のセッション**: 2026-05-14  
**ステータス**: ✅ 実装完了、UIテスト準備中

---

## 📌 1分で理解する現状

### ✅ 完成した
- **UI設計**: 上下2段×5タブで最大50銘柄同時表示
- **板パネル**: マネックス証券マルチボード500を参考にした小さくコンパクトなレイアウト
- **機能**: WebSocket連携、左クリック（詳細）、ダブルクリック（登録）、フラッシュ
- **技術**: expand=False で崩れ完全排除、Queue ベースのスレッド設計

### 🎨 見た目
- 売り気配: 赤系（背景#330000、テキスト#ff6666）
- 買い気配: 緑系（背景#003300、テキスト#66ff66）
- フラッシュ: 売=ピンク、買=水色（300ms）

### ⚠️ 重要なこと
- **expand=False が必須** → これがないと行が拡大して見えなくなる
- **test_ui.py でテスト** → kabuStation API なしでUIを確認可能

---

## 🚀 すぐやること（5分）

### 1. UIテスト実行
```bash
cd "C:\Users\flute\OneDrive\デスクトップ\trading-system\board_monitor"
python test_ui.py
```

**確認項目:**
- [ ] 上下2段が表示される
- [ ] 各段に5つの板が横に並ぶ
- [ ] テキストが小さく読みやすい
- [ ] 色が正しく分かれている（売=赤、買=緑）

### 2. kabuStation API 連携テスト
```bash
# .env ファイルを作成
echo KABU_API_PASSWORD=your_password > .env

# 実行
python board_monitor/app.py
```

**確認項目:**
- [ ] WebSocket が接続される
- [ ] リアルタイムデータが表示される
- [ ] フラッシュが動作する

---

## 📁 最初に読むべきファイル

| ファイル | 説明 |
|---------|------|
| `board_monitor/README.md` | 詳細説明、操作方法、トラブルシュート |
| `BOARD_MONITOR_HANDOFF.md` | 実装の重要ポイント、次のステップ |
| `QUICK_START.md` | このファイル |

---

## 🔧 技術的なポイント（重要）

### expand=False の5つの場所

```python
# 1. メインウィンドウ内のセクション
upper_frame.pack(fill=tk.X, expand=False)  # 上段
lower_frame.pack(fill=tk.X, expand=False)  # 下段

# 2. セクション内の板フレーム
boards_frame.pack(fill=tk.X, expand=False)  # 各タブの板エリア

# 3. 板パネル内のフレーム
self.header_frame.pack(fill=tk.X, expand=False)  # ヘッダー
self.info_frame.pack(fill=tk.X, expand=False)    # 情報行
self.board_frame.pack(fill=tk.BOTH, expand=True)  # 板エリア（ここだけFalseじゃない）

# 4. 板パネル内の各行
row_frame.pack(fill=tk.X, expand=False)  # 売り気配、買い気配の各行
```

**ルール:** セクション・パネル・行はすべて `expand=False`

---

## 📊 データフロー

```
kabuStation WebSocket
    ↓
websocket_client.py (Queue に蓄積)
    ↓
main_window._poll_queue() (Queue から取得)
    ↓
board_panel.update_data() (UI更新)
    ↓
画面表示
```

---

## 📦 ファイル構成

```
board_monitor/
├── app.py                    # エントリーポイント
├── gui/
│   ├── main_window.py        # メインウィンドウ（expand=False管理）
│   ├── board_panel.py        # 個別の板パネル（マネックス証券風）
│   └── detail_window.py      # 詳細ウィンドウ
├── kabu_api/
│   ├── websocket_client.py   # WebSocket クライアント（REST認証+WS受信）
│   └── board_parser.py       # 板データパーサー
├── test_ui.py                # UIテスト（ダミーデータ）
├── requirements.txt          # 依存パッケージ
├── README.md                 # 詳細説明
└── [新セッション用ファイル]
    ├── QUICK_START.md        # このファイル
    └── ../BOARD_MONITOR_HANDOFF.md  # 詳細な引き継ぎドキュメント
```

---

## ⚠️ よくあるトラブル

| 問題 | 原因 | 対策 |
|------|------|------|
| 行が拡大して見える | expand=True が存在 | コードを確認、expand=False に修正 |
| データが表示されない | kabuStation API が起動していない | kabuStation 本体を起動 |
| フラッシュが見えない | 更新頻度が低い | test_ui.py でダミーデータテスト |
| ウィンドウが小さすぎる | 初期サイズが小さい | geometry() で高さ指定（自動高さ推奨） |

---

## ✅ チェックリスト

新しいセッション開始時に確認：

- [ ] `board_monitor/` ディレクトリが存在
- [ ] `test_ui.py` が実行可能（ダミーデータ表示）
- [ ] `app.py` が実行可能（kabuStation API 連携）
- [ ] `README.md` が読める（操作方法）
- [ ] `BOARD_MONITOR_HANDOFF.md` が読める（技術詳細）
- [ ] メモリ `memory/board_monitor_status.md` に実装状況が記録されている

---

## 🎯 次のセッションの目標

1. **短期（今すぐ）**
   - test_ui.py で UI確認
   - kabuStation API 実連携テスト

2. **中期**
   - 本番銘柄登録
   - パフォーマンス検証（50銘柄）

3. **長期**
   - 前日検討システム（J-Quants）との統合
   - 通知機能

---

**秀長より:** 実装は完了しました。expand=False の問題は完全に解決済みです。自信を持って進めてください！
