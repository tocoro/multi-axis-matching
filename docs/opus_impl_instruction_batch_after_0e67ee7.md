# OPUS 実装指示書（batch after 0e67ee7）

## この文書の位置づけ
これは**複数タスクをまとめた実装指示書**です。
設計書ではありません。実装対象、変更ファイル、追加関数、追加テストを固定します。

対象コミット: `0e67ee7`
このコミットで以下は完了済み。
- full artifact JSON 保存
- `.index.json` 保存
- `_index_summary.json` 保存
- `trend_summary` / `anomaly_flags`
- `latest_artifact` / `comparison_rows` / `comparison_stats` / `flagged_rows`
- `focus_rows` / `recommended_artifact_paths` / `review_digest`
- `format_directory_summary_text()`
- `--summarize-dir` CLI
- 400 tests passing

したがって、今回の実装対象は **directory summary を review gate として読めるようにする拡張** に限定します。

この指示書は 3 タスクで構成する。
- Task A: `row_status` を comparison_rows に追加
- Task B: `gate_summary` を directory summary に追加
- Task C: text summary に `Gate summary` block を追加

---

## 今回の目的
`_index_summary.json` を見たときに、
- 各 row が stable / review / latest_focus のどれか
- ディレクトリ全体として gate を通過したか
- 人間が追加判断すべき状態か

をすぐ判断できるようにする。

新しい評価意味論は追加しない。
既存の `comparison_rows` / `focus_rows` / `flagged_rows` / `anomaly_flags` / `latest_artifact` だけを再構成する。

---

## 変更してよいファイル
今回変更してよいのは次だけ。

- `scripts/run_solution_catalog_live_ablation.py`
- `tests/test_live_ablation_script.py`
- 必要なら `docs/solution_catalog_live_ablation_protocol.md`

**それ以外は変更しないこと。**

---

## 変更してはいけないもの
- `src/evaluator.py`
- `src/experiments/review_summary.py`
- `diff_summary` の既存キー
- `review_summary` の既存キー
- multi-domain ablation 系コード
- prompt / schema / catalog contract

---

# Task A: `row_status` を comparison_rows に追加

## 目的
各 row のレビューステータスを 1 フィールドで読めるようにする。

## 変更ファイル
- `scripts/run_solution_catalog_live_ablation.py`

## 変更対象
```python
def build_artifact_directory_summary(index_items: list[dict]) -> dict:
    ...
```

## 実装内容
`comparison_rows` を組み立てた後、各 row に `row_status` を追加する。

## 許可される値
- `"review"`
- `"latest_focus"`
- `"stable"`

## 判定ルール
row 単位で次の順に判定する。

1. `manual_review == true` の row
   - `row_status = "review"`
2. `manual_review == false` かつ `latest_artifact.artifact_path` と一致する row
   - `row_status = "latest_focus"`
3. それ以外
   - `row_status = "stable"`

## 注意
- `focus_rows` の `focus_reason` はそのまま残す
- `comparison_rows` の既存キーは変えない
- query は追加しない

## テスト追加
1. `test_comparison_rows_have_row_status`
2. `test_row_status_review_for_manual_review_rows`
3. `test_row_status_latest_focus_for_latest_non_flagged_row`
4. `test_row_status_stable_for_other_rows`

---

# Task B: `gate_summary` を directory summary に追加

## 目的
directory 全体の gate 状態を 1 オブジェクトで読めるようにする。

## 変更ファイル
- `scripts/run_solution_catalog_live_ablation.py`

## 変更対象
```python
def build_artifact_directory_summary(index_items: list[dict]) -> dict:
    ...
```

## 追加するキー
返り値に `gate_summary` を追加する。

## フォーマット（固定）
```json
"gate_summary": {
  "gate_status": "pass",
  "manual_review_required": false,
  "flagged_run_count": 0,
  "recommended_run_count": 1
}
```

## 許可される `gate_status`
- `"pass"`
- `"review_required"`
- `"empty"`

## 判定ルール
1. `total_runs == 0`
   - `gate_status = "empty"`
   - `manual_review_required = false`
2. `flagged_rows` が 1 件以上
   - `gate_status = "review_required"`
   - `manual_review_required = true`
3. それ以外
   - `gate_status = "pass"`
   - `manual_review_required = false`

追加フィールド:
- `flagged_run_count = len(flagged_rows)`
- `recommended_run_count = len(recommended_artifact_paths)`

## 注意
- anomaly の意味を変更しない
- gate は review 用の要約であり、fail/exit code には使わない

## テスト追加
5. `test_directory_summary_has_gate_summary`
6. `test_gate_summary_review_required_when_flagged_rows_present`
7. `test_gate_summary_pass_when_no_flagged_rows`
8. `test_gate_summary_empty_when_no_runs`

---

# Task C: text summary に `Gate summary` block を追加

## 目的
人間向け text summary に gate 状態を明示する。

## 変更ファイル
- `scripts/run_solution_catalog_live_ablation.py`

## 変更対象
```python
def format_directory_summary_text(summary: dict) -> str:
    ...
```

## 追加する block
header の直後、`Total runs:` の後に `Gate summary:` block を追加する。

## 出力形式
```text
Gate summary:
- gate_status: pass
- manual_review_required: no
- flagged_run_count: 0
- recommended_run_count: 1
```

## 配置
- `Total runs:` の次
- `Models:` より前
- 空行を1つ入れてから既存 block に続ける

## 実装ルール
- `manual_review_required` は yes/no 表記
- 他はそのまま表示
- 順序は固定
  1. gate_status
  2. manual_review_required
  3. flagged_run_count
  4. recommended_run_count

## テスト追加
9. `test_format_directory_summary_text_includes_gate_summary_header`
10. `test_format_directory_summary_text_shows_gate_status`
11. `test_format_directory_summary_text_shows_manual_review_required_yes_no`

---

## 受け入れ条件
次を満たしたら完了。

1. `comparison_rows` に `row_status` が追加される
2. `gate_summary` が summary に追加される
3. flagged rows がある場合は `gate_status == "review_required"`
4. flagged rows がない場合は `gate_status == "pass"`
5. runs がない場合は `gate_status == "empty"`
6. text summary に `Gate summary` block が出る
7. full JSON は一切読まない
8. 既存 `--out` / `--summarize-dir` フローは壊さない
9. 新規テストが追加され、全テストが通る

---

## 実装順
必ずこの順で実装すること。

1. Task A: `row_status`
2. Task B: `gate_summary`
3. Task C: `format_directory_summary_text()` 更新
4. テスト追加
5. 必要なら protocol を最小更新

---

## コミット分割
可能なら 2 コミットまで分けてよい。

### Option 1: 1コミット
```text
Add row status and gate summary to directory summary
```

### Option 2: 2コミット
1. `Add row status and gate summary`
2. `Show gate summary in directory summary text`

---

## やってはいけないこと
- exit code 判定を変えること
- CSV 出力を足すこと
- `review_summary.py` を変更すること
- multi-domain 側にこの summary 拡張を広げること
- full artifact JSON を読むこと
- gate_status に free-form 文を使うこと

---

## 期待する差分の大きさ
- 中規模だが局所的
- 対象は live script とテストのみ
- OPUS が 1 回で実装可能な範囲
