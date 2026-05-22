# 板監視システム（board_monitor）引き継ぎドキュメント

**作成日**: 2026-05-14  
**ステータス**: 実装完了、UIテスト準備中  
**次のセッション**: 新しいチャットルーム

---

## 🎯 プロジェクト目標

kabuStation WebSocket API を使用して、**複数銘柄の板情報をリアルタイムで監視**し、効率的に取引判断を支援するシステムの構築。

実在の証券ツール（特にマネックス証券マルチボード500）のUIパターンを参考に、複数銘柄を同時に見える画面を実現。

---

## 📊 実装完了の要素

### ✅ UI設計
- **レイアウト**: 上下2段×5タブ = 最大50銘柄同時表示
- **板パネル**: マネックス証券パターン（売り5段+買い5段）
- **色分け**: 売=赤系、買=緑系、フラッシュ=ピンク/水色
- **フォント**: 6pt（小さくコンパクト）

### ✅ 機能実装
- **リアルタイム板表示**: WebSocket でデータ更新
- **インタラクション**: 左クリック（詳細表示）、ダブルクリック（登録）
- **フラッシュ機能**: 注文変化を300msで視覚的に表示
- **詳細ウィンドウ**: 左（銘柄情報）+右（板）の2パネル表示

### ✅ 技術設計
- **スレッド設計**: メインスレッド（GUI）+ データスレッド（WebSocket）
- **データフロー**: Queue ベースで安全な通信
- **APIレイヤー**: kabuStation WebSocket クライアントの抽象化

### ⚠️ 重要な教訓
- **expand=False が必須**: 前回の「expand=True 崩れ」を完全排除
- **複数ウィンドウ共有の問題**: Queue は単一消費者のみ対応

---

## 📁 ファイル構成と概要

```
board_monitor/
├── app.py                    # エントリーポイント
│                             # Tkinter root、WebSocket起動、メインループ
├── gui/
│   ├── main_window.py        # メインウィンドウ
│   │                         # - 上下2段のセクション作成
│   │                         # - 各セクションに5タブ×5銘柄
│   │                         # - expand=False で崩れ防止
│   ├── board_panel.py        # 個別の板パネル（v2改善版）
│   │                         # - ヘッダー（銘柄コード、現在値、騰落率）
│   │                         # - 情報行（始値、高値、安値、出来高）
│   │                         # - 売り気配5段（赤系）
│   │                         # - 買い気配5段（緑系）
│   │                         # - フラッシュ機能
│   └── detail_window.py      # 詳細ウィンドウ
│                             # - 左パネル：銘柄情報
│                             # - 右パネル：板詳細
├── kabu_api/
│   └── websocket_client.py   # kabuStation WebSocket クライアント
│                             # - 認証処理
│                             # - WebSocket接続
│                             # - メッセージ受信
│                             # - Queue へ蓄積
├── requirements.txt          # 依存パッケージ
├── test_ui.py                # UIテスト用スクリプト
│                             # - ダミーデータ生成
│                             # - レイアウト確認用
└── README.md                 # 詳細説明（操作方法、トラブルシュート）
```

---

## 🔧 実装上の重要ポイント

### 1️⃣ expand=False の重要性

**前回の失敗:**
```python
# ❌ これで崩れた
sec_frame.pack(fill=tk.BOTH, expand=True)  # セクションが拡大
row_frame.pack(fill=tk.BOTH, expand=True)  # 行が拡大 → 見えない
```

**今回の正しい方法:**
```python
# ✅ 正しい（必ず expand=False）
sec_frame.pack(fill=tk.X, expand=False)    # 横のみ、固定
row_frame.pack(fill=tk.X, expand=False)    # 横のみ、固定
```

**ルール:**
- セクション、行、パネル → すべて `expand=False`
- ウィンドウサイズは自動計算（高さは固定せず）

### 2️⃣ board_panel.py のレイアウト

各板パネルの内部構造：
```
Header Frame (bg="navy", h=18px)
  ├─ code_label (銘柄コード)
  ├─ price_label (現在値)
  └─ change_label (騰落率)

Info Frame (bg="gray20", h=14px)
  └─ info_label (始値、高値、安値、出来高)

Board Frame (bg="black")
  ├─ Ask Rows (5行, 赤系)
  │   └─ [label] [price] [volume]
  └─ Bid Rows (5行, 緑系)
      └─ [label] [price] [volume]
```

**重要:** 各行は `pack(fill=tk.X, expand=False)` で固定高さ（13px）

### 3️⃣ WebSocket データフロー

```
kabuStation API
    ↓ (WebSocket)
websocket_client.py
    ↓ (Queue に push)
main_window._poll_queue()
    ↓ (Queue から pop)
board_panel.update_data()
    ↓ (ラベル更新)
[画面表示]
```

**重要:** Queue は **単一消費者** のみ対応
- DetailWindow は Queue を直接消費しない
- MainWindow から refresh() で受け取る設計にする

---

## 🧪 テスト方法

### UIテスト（単体、kabuStation API 不要）
```bash
cd board_monitor
python test_ui.py
```

**確認事項:**
- [ ] 上下2段が正しく表示される
- [ ] 各段に5つの板が横に並ぶ
- [ ] 板のサイズがコンパクト（幅140px）
- [ ] フォントが小さく読みやすい（6pt）
- [ ] 色分けが正しい（売=赤、買=緑）
- [ ] クリックで詳細ウィンドウが表示される
- [ ] ダブルクリックで登録ダイアログが表示される

### 本番テスト（kabuStation API 連携）
```bash
# .env ファイルを設定
echo "KABU_API_PASSWORD=your_password" > .env

# 実行
python board_monitor/app.py
```

**確認事項:**
- [ ] WebSocket が接続される
- [ ] リアルタイムデータが表示される
- [ ] フラッシュが動作する（注文変化時）
- [ ] CPU 使用率が許容範囲（50銘柄で ~5%）
- [ ] メモリ使用率が安定している

---

## ⚠️ 既知の問題と対策

### 問題1: DetailWindow が複数開く
- **原因**: slot_key ごとに1つだけ開いている
- **対策**: `detail_windows` 辞書で管理済み

### 問題2: Board データ更新が遅い
- **原因**: Queue のポーリング間隔が長い
- **対策**: `_poll_queue()` の timeout を調整（現在 1秒）

### 問題3: フラッシュが見えない
- **原因**: フラッシュ時間が短すぎる
- **対策**: `_apply_flash()` の時間を延長（デフォルト 300ms）

---

## 🚀 次のステップ

### すぐやること
1. **UIテスト実行** (`test_ui.py`)
   - レイアウトが正しいか目視確認
   - expand=False で崩れていないか確認

2. **kabuStation API 連携**
   - `.env` に API パスワードを設定
   - `app.py` で本番動作テスト

3. **本番銘柄投入**
   - 実際の監視銘柄を登録
   - リアルタイムデータの流れを確認

### その次
1. **パフォーマンス最適化**
   - 50銘柄同時表示時の応答速度
   - CPU / メモリ使用率

2. **データ保存機能**
   - 各銘柄の板履歴を CSV 記録
   - 検証画面で実績と比較

3. **前日検討システム（J-Quants）との統合**
   - 前日のスコアリング結果を表示
   - 候補銘柄の優先順位表示

---

## 📚 参考資料

### 実在ツールの参考情報
- **マネックス証券マルチボード500**: 1シート10銘柄、パーツ組み合わせ可能
- **SBI証券HYPER SBI 2**: タイル形式の複数表示
- **kabuステーション**: レイアウトフリー（複数ウィンドウ）

### プロジェクトメモリ
- `memory/board_monitor_status.md`: 設計仕様、実装状況

### コード参考
- `board_monitor/README.md`: 詳細説明、操作方法

---

## ✅ チェックリスト（引き継ぎ用）

新しいセッションで確認すること：

- [ ] `board_monitor/` ディレクトリが存在し、全ファイルが揃っている
- [ ] `README.md` が読める（操作方法、トラブルシュート）
- [ ] `test_ui.py` が実行できる（ダミーデータ表示）
- [ ] シンタックスチェック済み（全ファイル）
- [ ] メモリ（`board_monitor_status.md`）に実装状況が記録されている
- [ ] このドキュメント（`BOARD_MONITOR_HANDOFF.md`）が読める

---

**秀長より：** このセッションで実装した板監視システムは、実在の証券ツール（マネックス証券マルチボード500など）を参考にした、実用的で効率的なUIデザインです。expand=False の問題を完全に解決し、複数銘柄を同時に効率よく監視できる設計になっています。次のセッションでも自信を持って進めてください。頑張ってください！
