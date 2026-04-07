# OPUS 実装指示書（batch after 4039f9c）

## この文書の位置づけ
これは**複数タスクをまとめた実装指示書**です。
設計書ではありません。実装対象、変更ファイル、追加関数、追加テストを固定します。

対象コミット: `4039f9c`
このコミットで以下は完了済み。
- `GET /api/directory-summary`
- web UI summary panel
- gate / manual review / total runs / flagged runs / latest / recommended の表示
- 424 tests passing

したがって、今回の実装対象は **summary panel を review 作業向けに少し操作可能にすること** に限定します。

この指示書は 3 タスクで構成する。
- Task A: manual-review-only filter を追加
- Task B: refresh / loaded-state 表示を追加
- Task C: web UI テストを追加

---

## 今回の目的
web UI 上で summary を見たときに、
- 要確認 run だけを見られる
- summary が読み込み済みか分かる
- 再読込できる

状態にする。

新しい評価意味論は追加しない。
既存の `/api/directory-summary` レスポンスをそのまま使う。

---

## 変更してよいファイル
今回変更してよいのは次だけ。

- `server.py`
- `static/index.html`
- `tests/test_web_summary_panel.py`
- 必要なら `docs/solution_catalog_live_ablation_protocol.md`

**それ以外は変更しないこと。**

---

## 変更してはいけないもの
- `scripts/run_solution_catalog_live_ablation.py`
- `_index_summary.json` の schema
- multi-domain ablation 系コード
- evaluator / prompt / catalog contract

---

# Task A: manual-review-only filter を追加

## 目的
summary panel で flagged rows がある場合、その artifact path だけに絞って見られるようにする。

## 変更ファイル
- `static/index.html`

## 実装内容
summary panel に toggle を 1 つ追加する。

### 表示仕様
- ラベル: `Show manual-review only`
- checkbox または button toggle のどちらでもよい
- default は off

### 動作仕様
- off: `recommended_artifact_paths` を従来どおり表示
- on: `flagged_rows[].artifact_path` のみ表示
- flagged rows が 0 件なら on にしても `none`
- 順序は summary 内の順序を維持する
- 重複があれば先勝ちで重複除去

### 注意
- API 追加は不要
- client-side のみで処理する
- latest artifact 表示は変えない

## テスト追加
1. filter off で recommended artifacts が表示される
2. filter on で flagged artifact paths のみ表示される
3. flagged rows が空なら `none`

---

# Task B: refresh / loaded-state 表示を追加

## 目的
summary panel が stale か不明、という状態を避ける。

## 変更ファイル
- `static/index.html`

## 実装内容
summary panel に以下を追加する。

### 追加項目
1. `Refresh Summary` button
2. `Summary status` 1 行

### `Summary status` の表示値
- 初期: `not loaded`
- 読み込み成功: `loaded`
- 読み込み失敗: `error`
- summary 不在: `empty`

### 動作仕様
- `Load Ablation Summary` 実行成功 → `loaded`
- summary 不在 (`error=no_summary`) → `empty`
- fetch 失敗または parse 失敗 → `error`
- `Refresh Summary` は `loadSummary()` を再実行するだけでよい

### 注意
- status 表示は panel の上部かボタン横でよい
- 新しい API は不要

## テスト追加
4. 初期状態で `not loaded`
5. 成功時に `loaded`
6. no_summary で `empty`
7. 例外時に `error`

---

# Task C: web UI テストを追加

## 目的
新しい UI 状態が壊れないようにする。

## 変更ファイル
- `tests/test_web_summary_panel.py`

## 必須検証項目
8. recommended と flagged の切替が機能する
9. flagged の順序が保持される
10. refresh 操作が同じ loader を再利用する前提で壊れない
11. status 表示が `not loaded / loaded / empty / error` を取りうる

### テスト方針
- 既存テストと同様に lightweight でよい
- DOM そのものの完全 E2E は不要
- 文字列生成・状態分岐中心でよい

---

## 受け入れ条件
次を満たしたら完了。

1. summary panel に manual-review-only filter が追加される
2. summary panel に refresh button が追加される
3. summary status が表示される
4. filter off/on で表示内容が切り替わる
5. no_summary / error の状態が区別される
6. 既存 `/api/directory-summary` は変更しない
7. 全テストが通る

---

## 実装順
必ずこの順で実装すること。

1. Task A: filter
2. Task B: refresh / status
3. Task C: テスト追加
4. 必要なら protocol を最小更新

---

## コミット分割
可能なら 2 コミットまで分けてよい。

### Option 1: 1コミット
```text
Add filter and refresh controls to web summary panel
```

### Option 2: 2コミット
1. `Add manual-review filter to web summary panel`
2. `Add refresh and status to web summary panel`

---

## やってはいけないこと
- `/api/directory-summary` の schema を変更すること
- full artifact JSON を UI で読むこと
- multi-domain UI に広げること
- free-form explanation を増やすこと

---

## 期待する差分の大きさ
- 中規模だが局所的
- 対象は `server.py` / `static/index.html` / UI テストのみ
- OPUS が 1 回で実装可能な範囲
