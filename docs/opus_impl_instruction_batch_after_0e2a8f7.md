# OPUS 実装指示書（batch after 0e2a8f7）

## この文書の位置づけ
これは**複数タスクをまとめた実装指示書**です。
設計書ではありません。実装対象、変更ファイル、追加関数、追加テストを固定します。

対象コミット: `0e2a8f7`
このコミットで以下は完了済み。
- full artifact JSON 保存
- `.index.json` 保存
- `_index_summary.json` 保存
- `trend_summary` / `anomaly_flags`
- `latest_artifact` / `comparison_rows` / `review_digest`
- `format_directory_summary_text()`
- `--summarize-dir` CLI
- 381 tests passing

したがって、今回の実装対象は **directory summary からレビュー対象を選びやすくする拡張** に限定します。

この指示書は 3 タスクで構成する。
- Task A: comparison stats を追加
- Task B: flagged_rows を追加
- Task C: text summary に flagged section を追加

---

## 今回の目的
`_index_summary.json` を見たときに、
- 何件が manual review 対象か
- どの run が flag 対象か
- どの程度の割合で signal が出ているか

をすぐ判断できるようにする。

新しい評価意味論は追加しない。
既存の `comparison_rows` / `anomaly_flags` / `verdict_counts` だけを再構成する。

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

# Task A: comparison_stats を追加

## 目的
comparison_rows 全体の簡潔な件数情報を summary に持たせる。

## 変更ファイル
- `scripts/run_solution_catalog_live_ablation.py`

## 変更対象関数
```python
def build_artifact_directory_summary(index_items: list[dict]) -> dict:
    ...
```

## 追加するキー
返り値に `comparison_stats` を追加する。

## フォーマット（固定）
```json
"comparison_stats": {
  "total_rows": 3,
  "manual_review_rows": 1,
  "reason_changed_rows": 3,
  "score_changed_rows": 3,
  "confidence_changed_rows": 1,
  "ranking_changed_rows": 0,
  "unknown_reduced_rows": 0,
  "disqualified_changed_rows": 0
}
```

## 計算ルール
- `comparison_rows` から数えること
- 各項目は bool が true の row 件数
- `total_rows` は `len(comparison_rows)`
- `manual_review_rows` は row の `manual_review`
- `verdict_counts` を流用してもよいが、`comparison_rows` と整合すること

## テスト追加
1. `test_directory_summary_has_comparison_stats`
2. `test_comparison_stats_total_rows_matches_comparison_rows`
3. `test_comparison_stats_manual_review_rows_counted`

---

# Task B: flagged_rows を追加

## 目的
manual review が必要な rows だけを summary からすぐ取り出せるようにする。

## 変更ファイル
- `scripts/run_solution_catalog_live_ablation.py`

## 変更対象関数
```python
def build_artifact_directory_summary(index_items: list[dict]) -> dict:
    ...
```

## 追加するキー
返り値に `flagged_rows` を追加する。

## フォーマット（固定）
```json
"flagged_rows": [
  {
    "timestamp": "2026-04-06T15:00:00Z",
    "model": "gemini-2.5-flash",
    "artifact_path": "artifacts/case1.json",
    "manual_review": true,
    "reason_changed": false,
    "confidence_changed": true,
    "ranking_changed": false,
    "unknown_reduced": false,
    "disqualified_changed": false
  }
]
```

## 計算ルール
- `comparison_rows` のうち `manual_review == true` のものだけを抽出
- 行の順序は `comparison_rows` と同じ
- `score_changed` は含めない
- `manual_review` は必ず含める
- query は含めない

## テスト追加
4. `test_directory_summary_has_flagged_rows`
5. `test_flagged_rows_subset_of_comparison_rows`
6. `test_flagged_rows_only_manual_review_true`

---

# Task C: text summary に flagged section を追加

## 目的
人間向け text summary に「要確認 run 一覧」を表示する。

## 変更ファイル
- `scripts/run_solution_catalog_live_ablation.py`

## 変更対象
```python
def format_directory_summary_text(summary: dict) -> str:
    ...
```

## 追加する block
`Artifacts:` の前に `Flagged rows:` block を追加する。

## 出力形式
manual review rows がある場合:
```text
Flagged rows:
- 2026-04-06T15:00:00Z | gemini-2.5-flash | artifacts/case1.json
```

manual review rows がない場合:
```text
Flagged rows: none
```

## 配置
- `Review digest:` block の後
- 空行を1つ入れてから出す
- `Artifacts:` より前に置く

## 実装ルール
- 行の順序は `flagged_rows` の順
- 1行の形式は固定
  - `- {timestamp} | {model} | {artifact_path}`
- reason や ranking の内訳は text に出さない

## テスト追加
7. `test_format_directory_summary_text_includes_flagged_rows_header`
8. `test_format_directory_summary_text_flagged_rows_none_when_empty`
9. `test_format_directory_summary_text_lists_flagged_rows_when_present`

---

## 受け入れ条件
次を満たしたら完了。

1. `comparison_stats` が summary に追加される
2. `flagged_rows` が summary に追加される
3. flagged rows は `manual_review == true` の rows のみ
4. text summary に `Flagged rows:` block が出る
5. `comparison_rows` の順序は壊れない
6. full JSON は一切読まない
7. 既存 `--out` / `--summarize-dir` フローは壊さない
8. 新規テストが追加され、全テストが通る

---

## 実装順
必ずこの順で実装すること。

1. Task A: `comparison_stats`
2. Task B: `flagged_rows`
3. Task C: `format_directory_summary_text()` 更新
4. テスト追加
5. 必要なら protocol を最小更新

---

## コミット分割
可能なら 2 コミットまで分けてよい。

### Option 1: 1コミット
```text
Add comparison stats and flagged rows to directory summary
```

### Option 2: 2コミット
1. `Add comparison stats and flagged rows`
2. `Show flagged rows in directory summary text`

---

## やってはいけないこと
- CSV 出力を足すこと
- `review_summary.py` を変更すること
- multi-domain 側にこの summary 拡張を広げること
- full artifact JSON を読むこと
- flagged rows に free-form reason を入れること
- text summary に bool テーブルをそのまま出すこと

---

## 期待する差分の大きさ
- 中規模だが局所的
- 対象は live script とテストのみ
- OPUS が 1 回で実装可能な範囲
