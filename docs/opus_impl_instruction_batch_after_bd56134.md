# OPUS 実装指示書（batch after bd56134）

## この文書の位置づけ
これは**複数タスクをまとめた実装指示書**です。
設計書ではありません。実装対象、変更ファイル、追加関数、追加テストを固定します。

対象コミット: `bd56134`
このコミットで以下は完了済み。
- `/api/directory-summary`
- web UI summary panel
- manual-review-only filter
- refresh button
- summary status 表示
- 434 tests passing

したがって、今回の実装対象は **summary panel の review 導線をもう一段明確にすること** に限定します。

この指示書は 3 タスクで構成する。
- Task A: separate lists block を追加
- Task B: client-side fetched timestamp を追加
- Task C: web UI テストを追加

---

## 今回の目的
web UI 上で summary を見たときに、
- recommended と flagged を切り替えず両方把握できる
- いつ読み込んだ表示か分かる
- summary panel の状態が視覚的に安定する

状態にする。

新しい評価意味論は追加しない。
既存の `/api/directory-summary` レスポンスをそのまま使う。

---

## 変更してよいファイル
今回変更してよいのは次だけ。

- `static/index.html`
- `tests/test_web_summary_panel.py`
- 必要なら `docs/solution_catalog_live_ablation_protocol.md`

**それ以外は変更しないこと。**

---

## 変更してはいけないもの
- `server.py`
- `scripts/run_solution_catalog_live_ablation.py`
- `_index_summary.json` の schema
- multi-domain ablation 系コード
- evaluator / prompt / catalog contract

---

# Task A: separate lists block を追加

## 目的
filter 切替とは別に、recommended / flagged の両方を panel 下部で常に確認できるようにする。

## 変更ファイル
- `static/index.html`

## 実装内容
summary panel に 2 つの block を追加する。

### 追加 block
1. `Recommended list`
2. `Flagged list`

### 表示ルール
- `Recommended list`
  - `recommended_artifact_paths` を順序維持で表示
  - 空なら `none`
- `Flagged list`
  - `flagged_rows[].artifact_path` を先勝ち重複除去して表示
  - 空なら `none`
- 既存の toggle/filter は残す
- 既存の主表示リストも残す

### UI 制約
- テーブルは不要
- 既存 `summary-list` を再利用してよい
- 見出しは固定文言にする
  - `Recommended list`
  - `Flagged list`

## テスト追加
1. recommended list が表示される
2. flagged list が表示される
3. flagged list が重複除去される
4. 空の場合 `none`

---

# Task B: client-side fetched timestamp を追加

## 目的
いま表示している summary がいつ読み込まれたものかを UI 上で分かるようにする。

## 変更ファイル
- `static/index.html`

## 実装内容
client-side state に fetched timestamp を追加する。

### 追加 state
- `_summaryFetchedAt`

### ルール
- `loadSummary()` 成功時に `new Date()` を保存
- `empty` / `error` の場合は `null` に戻してよい
- panel 上部に 1 行追加する
  - ラベル: `Fetched at`
  - 値: local time string
- `null` のときは `none`

### 注意
- server 側 timestamp は追加しない
- client-side の取得時刻だけでよい
- exact formatting は `toLocaleString()` でよい

## テスト追加
5. loaded のとき fetched timestamp が設定される前提で表示される
6. empty のとき `none`
7. error のとき `none`

---

# Task C: web UI テストを追加

## 目的
新しい表示ブロックと fetched timestamp が壊れないようにする。

## 変更ファイル
- `tests/test_web_summary_panel.py`

## 必須検証項目
8. recommended list / flagged list が独立して存在する
9. toggle の有無に関係なく separate list data は保持される
10. fetched timestamp は loaded 時のみ有効
11. fetched timestamp がない場合 `none`

### テスト方針
- 既存テストと同じく lightweight でよい
- state 分岐と文字列生成中心でよい
- 完全 DOM E2E は不要

---

## 受け入れ条件
次を満たしたら完了。

1. summary panel に `Recommended list` block が追加される
2. summary panel に `Flagged list` block が追加される
3. fetched timestamp が表示される
4. loaded 以外では fetched timestamp は `none`
5. 既存 filter / refresh / status は壊さない
6. `/api/directory-summary` は変更しない
7. 全テストが通る

---

## 実装順
必ずこの順で実装すること。

1. Task A: separate lists
2. Task B: fetched timestamp
3. Task C: テスト追加
4. 必要なら protocol を最小更新

---

## コミット分割
可能なら 2 コミットまで分けてよい。

### Option 1: 1コミット
```text
Add separate lists and fetched timestamp to web summary panel
```

### Option 2: 2コミット
1. `Add recommended and flagged list blocks to summary panel`
2. `Add fetched timestamp to summary panel`

---

## やってはいけないこと
- `/api/directory-summary` の schema を変更すること
- full artifact JSON を UI で読むこと
- multi-domain UI に広げること
- server 側 timestamp を増やすこと

---

## 期待する差分の大きさ
- 中規模だが局所的
- 対象は `static/index.html` と UI テストのみ
- OPUS が 1 回で実装可能な範囲
