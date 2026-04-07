# OPUS 実装指示書（batch after bfbffa8）

## この文書の位置づけ
これは**複数タスクをまとめた実装指示書**です。
設計書ではありません。実装対象、変更ファイル、追加関数、追加テストを固定します。

対象コミット: `bfbffa8`
このコミットで以下は完了済み。
- demo presets（restaurant / clinic）
- compare-first copy
- demo scenario cards 6本
- `Compare this scenario`
- scenario-driven `What to notice`
- domain filter tabs
- visible counts
- `Demo context`
- 490 tests passing

したがって、今回の実装対象は **Compare 結果をプレゼン向けにさらに読みやすくすること** に限定します。

この指示書は 4 タスクで構成する。
- Task A: compare result summary strip を追加
- Task B: changed candidates list を追加
- Task C: quick jump links を追加
- Task D: web UI テストを追加

---

## 今回の目的
Compare 実行後に、
- 何が変わったかを1行で把握できる
- どの candidate を見ればよいかすぐ分かる
- with / without の詳細に素早く移動できる

状態にする。

新しい評価意味論は追加しない。
既存 `diff_summary` と既存表示要素を再構成するだけにする。

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

# Task A: compare result summary strip を追加

## 目的
Compare 結果の最上部に、現在の差分の要約を固定形式で表示する。

## 変更ファイル
- `static/index.html`

## 表示位置
- diff card の最上部
- `What to notice` がある場合はその下、diff highlights の上

## 固定見出し
- `Compare summary`

## 表示項目（固定順）
1. `ranking: changed/unchanged`
2. `scores: N changed`
3. `reasons: N changed`
4. `confidence: N changed`
5. `unknown: reduced/no reduction`

## 計算ルール
- `ranking`: `data.diff_summary.ranking_changed`
- `scores`: `Object.keys(score_changes || {}).length`
- `reasons`: `Object.keys(reason_changes || {}).length`
- `confidence`: `Object.keys(confidence_changes || {}).length`
- `unknown`: `Object.keys(unknown_changes || {}).length > 0`

## 注意
- 既存 diff highlight badges は残す
- 文言は固定
- free-form summary を生成しない

## テスト追加
1. `Compare summary` 見出しが表示される
2. `ranking: changed/unchanged` が表示される
3. `scores/reasons/confidence` の count が表示される
4. `unknown: reduced/no reduction` が表示される

---

# Task B: changed candidates list を追加

## 目的
どの candidate に diff が出たかをまとめて見せる。

## 変更ファイル
- `static/index.html`

## 表示位置
- `Compare summary` の下
- diff highlights の上または下のどちらでもよい

## 固定見出し
- `Changed candidates`

## 表示ルール
- 対象 candidate ids は次の union
  - `score_changes` の keys
  - `reason_changes` の keys
  - `confidence_changes` の keys
  - `unknown_changes` の keys
- 重複は先勝ちで除去
- 順序は次で固定
  1. `score_changes` 由来
  2. `reason_changes` 由来
  3. `confidence_changes` 由来
  4. `unknown_changes` 由来
- 表示形式
  - `- place_1`
  - `- clinic_3`
- 1件もなければ `Changed candidates: none`

## 注意
- candidate 名は解決しない
- id のままでよい
- free-form 理由は足さない

## テスト追加
5. union が正しく作られる
6. 重複除去が維持される
7. 空なら `none`

---

# Task C: quick jump links を追加

## 目的
with / without の詳細に素早く移動できるようにする。

## 変更ファイル
- `static/index.html`

## 実装内容
with / without の card に anchor id を振り、diff card 上部に quick links を追加する。

## 固定見出し
- `Quick jump`

## 固定リンク文言
- `Go to with-catalog results`
- `Go to without-catalog results`

## 動作仕様
- `href="#withCatalogResults"`
- `href="#withoutCatalogResults"`
- 対応する card 側に `id="withCatalogResults"`, `id="withoutCatalogResults"`

## 注意
- スムーススクロールは不要
- 見た目は通常 link でよい
- 既存 card 構造は壊さない

## テスト追加
8. quick jump 見出しが表示される
9. with / without のリンク文言が存在する
10. 対応 anchor id が存在する前提になっている

---

# Task D: web UI テストを追加

## 目的
Compare 結果のプレゼン導線が壊れないようにする。

## 変更ファイル
- `tests/test_web_summary_panel.py`

## 必須検証項目
11. summary strip は既存 diff_summary キーだけから導出される
12. changed candidates list は union + dedupe 規則を守る
13. quick jump は with / without 両方を指す
14. scenario Compare / manual Compare のどちらでも compare result summary は使える

### テスト方針
- 既存同様 lightweight でよい
- DOM 完全 E2E は不要
- string generation / set logic / anchor existence 中心でよい

---

## 受け入れ条件
次を満たしたら完了。

1. `Compare summary` が追加される
2. `Changed candidates` が追加される
3. `Quick jump` が追加される
4. with / without 詳細 card に anchor id が付く
5. 既存 `What to notice` / diff highlights は壊さない
6. API schema は変更しない
7. 全テストが通る

---

## 実装順
必ずこの順で実装すること。

1. Task A: compare result summary strip
2. Task B: changed candidates list
3. Task C: quick jump links
4. Task D: テスト追加
5. 必要なら protocol を最小更新

---

## コミット分割
可能なら 2 コミットまで分けてよい。

### Option 1: 1コミット
```text
Add compare result summary and quick jumps to web UI
```

### Option 2: 2コミット
1. `Add compare summary and changed candidates list`
2. `Add quick jump links for compare results`

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
