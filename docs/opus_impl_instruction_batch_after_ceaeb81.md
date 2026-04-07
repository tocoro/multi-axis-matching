# OPUS 実装指示書（batch after ceaeb81）

## この文書の位置づけ
これは**複数タスクをまとめた実装指示書**です。
設計書ではありません。実装対象、変更ファイル、追加関数、追加テストを固定します。

対象コミット: `ceaeb81`
このコミットで以下は完了済み。
- `Compare summary`
- `Changed candidates`
- `Quick jump`
- candidate compare anchors
- `Candidate compare index`
- 517 tests passing

したがって、今回の実装対象は **candidate ごとの変化内容をその場で読み取れるようにすること** に限定します。

この指示書は 4 タスクで構成する。
- Task A: per-candidate delta summary を追加
- Task B: changed-only filter を candidate compare index に追加
- Task C: active candidate focus header を追加
- Task D: web UI テストを追加

---

## 今回の目的
Compare 実行後に、
- 各 candidate で何が変わったかをすぐ読める
- 変化した candidate だけに絞って見られる
- 今どの candidate を見ているか迷わない

状態にする。

新しい評価意味論は追加しない。
既存 `diff_summary` と既存 candidate compare navigation を再構成するだけにする。

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
- `/api/pipeline` の schema
- `/api/ablation` の schema
- `_index_summary.json` の schema
- multi-domain ablation 系コード
- evaluator / prompt / catalog contract

---

# Task A: per-candidate delta summary を追加

## 目的
candidate compare block の先頭で、その candidate にどの diff が出ているかを固定形式で表示する。

## 変更ファイル
- `static/index.html`

## 表示位置
- 各 `candidateCompare-{id}` block の先頭
- with / without のカード列より上

## 固定見出し
- `Candidate delta`

## 表示項目（固定順）
1. `score: changed/unchanged`
2. `reason: changed/unchanged`
3. `confidence: changed/unchanged`
4. `unknown: changed/unchanged`

## 計算ルール
candidate id を `cid` として、
- `score`: `cid in Object.keys(score_changes || {})`
- `reason`: `cid in Object.keys(reason_changes || {})`
- `confidence`: `cid in Object.keys(confidence_changes || {})`
- `unknown`: `cid in Object.keys(unknown_changes || {})`

## 表示ルール
- 文言は固定
- yes/no ではなく `changed/unchanged`
- free-form explanation は追加しない

## テスト追加
1. `Candidate delta` 見出しが出る
2. score changed/unchanged が計算される
3. reason/confidence/unknown も同様に計算される
4. 既存 diff_summary キー以外を参照しない

---

# Task B: changed-only filter を candidate compare index に追加

## 目的
index から changed candidate だけに絞って見られるようにする。

## 変更ファイル
- `static/index.html`

## 実装内容
`Candidate compare index` の近くに toggle を追加する。

## 固定ラベル
- `Show changed candidates only`

## 状態
- client-side state: `showChangedCandidatesOnly`
- 初期値は `false`

## 動作仕様
- `false`: full union set を index に表示
- `true`: changed candidate subset のみ表示
- changed subset は既存 `Changed candidates` と同じ集合・同じ順序
- empty の場合は `Candidate compare index: none`

## 注意
- `Changed candidates` block 自体は残す
- 既存 `Candidate compare index` を置き換えるだけ
- auto-scroll は不要

## テスト追加
5. 初期は full union を表示
6. filter on で changed subset のみ表示
7. changed subset の順序は既存 changed order と一致する
8. empty subset で `none`

---

# Task C: active candidate focus header を追加

## 目的
リンクジャンプ後に、今見ている candidate を上部で明示する。

## 変更ファイル
- `static/index.html`

## 実装内容
小さな focus header を compare result area の上部に追加する。

## 固定ラベル
- `Candidate focus`

## 表示ルール
### デフォルト
```text
Candidate focus: none
```

### changed candidate link または compare index link を押した後
```text
Candidate focus: place_1
```
または
```text
Candidate focus: clinic_3
```

## 状態管理
- client-side state: `currentCandidateFocus`
- 初期値は `null`
- candidate navigation link click 時に candidate id をセット
- 新しい Compare 実行時は `null` に戻してよい

## 注意
- Intersection observer などは不要
- click ベースで十分
- scenario/manual の区別は不要

## テスト追加
9. 初期表示が `Candidate focus: none`
10. candidate link click 後に id が表示される前提になる
11. 新しい Compare 実行で `none` に戻る前提になる

---

# Task D: web UI テストを追加

## 目的
candidate-focused compare UI が壊れないようにする。

## 変更ファイル
- `tests/test_web_summary_panel.py`

## 必須検証項目
12. per-candidate delta は candidate id ごとに diff_summary から導出される
13. changed-only filter は changed set と full union set を区別する
14. active candidate focus は click 起点で更新される
15. 新規 Compare 実行で focus はリセットされる

### テスト方針
- 既存同様 lightweight でよい
- DOM 完全 E2E は不要
- set logic / state / string generation 中心でよい

---

## 受け入れ条件
次を満たしたら完了。

1. 各 candidate compare block に `Candidate delta` が追加される
2. `Candidate compare index` に changed-only filter が付く
3. `Candidate focus` header が追加される
4. changed set と full union set が UI 上で区別される
5. 既存 `Changed candidates` / `Quick jump` / `Candidate compare index` は壊さない
6. API schema は変更しない
7. 全テストが通る

---

## 実装順
必ずこの順で実装すること。

1. Task A: per-candidate delta summary
2. Task B: changed-only filter
3. Task C: active candidate focus header
4. Task D: テスト追加
5. 必要なら protocol を最小更新

---

## コミット分割
可能なら 2 コミットまで分けてよい。

### Option 1: 1コミット
```text
Add per-candidate delta summaries and focus state to compare UI
```

### Option 2: 2コミット
1. `Add per-candidate delta summaries to compare blocks`
2. `Add changed-only index filter and candidate focus header`

---

## やってはいけないこと
- new diff semantics を追加すること
- `/api/ablation` の schema を変更すること
- full artifact JSON を UI で読むこと
- multi-domain evaluator 側に手を入れること
- candidate 表示名を新規解決すること

---

## 期待する差分の大きさ
- 中規模だが局所的
- 対象は `static/index.html` と UI テストのみ
- OPUS が 1 回で実装可能な範囲
