# OPUS 実装指示書（batch after e617d19）

## この文書の位置づけ
これは**複数タスクをまとめた実装指示書**です。
設計書ではありません。実装対象、変更ファイル、追加関数、追加テストを固定します。

対象コミット: `e617d19`
このコミットで以下は完了済み。
- full artifact JSON 保存
- `.index.json` 保存
- `_index_summary.json` 保存
- `trend_summary` 保存
- `anomaly_flags` 保存
- `format_directory_summary_text()`
- `--summarize-dir` CLI
- 372 tests passing

したがって、今回の実装対象は **directory summary を review 用にさらに圧縮すること** に限定します。

この指示書は 3 タスクで構成する。
- Task A: latest artifact pointer を追加
- Task B: compact comparison rows を追加
- Task C: review digest を追加し text summary に出す

---

## 今回の目的
`_index_summary.json` を見たときに、
- 最新 run がどれか
- 各 run を1行で比較できる
- directory 全体のレビューポイントを短く読める

状態にする。

新しい評価意味論は追加しない。
既存の `verdict_counts` / `trend_summary` / `anomaly_flags` だけを再構成する。

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

# Task A: latest artifact pointer を追加

## 目的
summary を見たときに「最後に生成された run」がすぐ分かるようにする。

## 変更ファイル
- `scripts/run_solution_catalog_live_ablation.py`

## 変更対象関数
```python
def build_artifact_directory_summary(index_items: list[dict]) -> dict:
    ...
```

## 追加するキー
返り値に `latest_artifact` を追加する。

## フォーマット（固定）
```json
"latest_artifact": {
  "artifact_path": "artifacts/case2.json",
  "timestamp": "2026-04-06T15:01:00Z",
  "model": "gemini-2.5-flash"
}
```

## 計算ルール
- `artifacts` 配列の最後の要素を使う
- `artifacts` が空なら `null`
- 追加するのは `artifact_path`, `timestamp`, `model` のみ
- query は入れない
- quick_verdict は入れない

## テスト追加
1. `test_directory_summary_has_latest_artifact`
2. `test_latest_artifact_matches_last_sorted_artifact`
3. `test_latest_artifact_none_when_no_artifacts`

---

# Task B: compact comparison rows を追加

## 目的
各 artifact を 1 行で比較できる、機械可読な軽量表現を summary に持たせる。

## 変更ファイル
- `scripts/run_solution_catalog_live_ablation.py`

## 変更対象関数
```python
def build_artifact_directory_summary(index_items: list[dict]) -> dict:
    ...
```

## 追加するキー
返り値に `comparison_rows` を追加する。

## フォーマット（固定）
```json
"comparison_rows": [
  {
    "timestamp": "2026-04-06T15:00:00Z",
    "model": "gemini-2.5-flash",
    "artifact_path": "artifacts/case1.json",
    "reason_changed": true,
    "score_changed": true,
    "confidence_changed": false,
    "ranking_changed": false,
    "unknown_reduced": false,
    "disqualified_changed": false,
    "manual_review": false
  }
]
```

## 計算ルール
- `artifacts` 配列の順序に合わせて rows を作る
- bool 値は各 artifact の `quick_verdict` から取る
- `manual_review` は artifact 単位で次の式
  - `ranking_changed or unknown_reduced or disqualified_changed or (confidence_changed and not reason_changed)`
- directory-level anomaly flag を流用しない
- top_candidates は入れない
- query は入れない

## テスト追加
4. `test_directory_summary_has_comparison_rows`
5. `test_comparison_rows_align_with_artifacts_order`
6. `test_comparison_rows_manual_review_rule`

---

# Task C: review digest を追加し text summary に出す

## 目的
directory 全体としてのレビューポイントを短文ではなく**固定 phrase の箇条書き**で持つ。

## 変更ファイル
- `scripts/run_solution_catalog_live_ablation.py`

## 変更対象
```python
def build_artifact_directory_summary(index_items: list[dict]) -> dict:
    ...

def format_directory_summary_text(summary: dict) -> str:
    ...
```

## 追加するキー
返り値に `review_digest` を追加する。

## フォーマット（固定）
```json
"review_digest": [
  "ranking remained stable across runs",
  "reason changes are present",
  "score changes are present",
  "no unknown reduction observed",
  "no manual-review anomaly detected"
]
```

## 生成ルール
以下の fixed phrase のみ使うこと。

### ranking
- `verdict_counts["ranking_changed"] == 0`
  - `"ranking remained stable across runs"`
- それ以外
  - `"ranking changes detected across runs"`

### reason
- `verdict_counts["reason_changed"] > 0`
  - `"reason changes are present"`
- それ以外
  - `"no reason changes observed"`

### score
- `verdict_counts["score_changed"] > 0`
  - `"score changes are present"`
- それ以外
  - `"no score changes observed"`

### unknown
- `verdict_counts["unknown_reduced"] == 0`
  - `"no unknown reduction observed"`
- それ以外
  - `"unknown reduction detected"`

### anomaly
- `anomaly_flags["needs_manual_review"]`
  - `"manual-review anomaly detected"`
- それ以外
  - `"no manual-review anomaly detected"`

## `format_directory_summary_text()` の変更
既存 text summary に次の block を追加する。

### 出力形式
```text
Review digest:
- ranking remained stable across runs
- reason changes are present
- score changes are present
- no unknown reduction observed
- no manual-review anomaly detected
```

### 配置
- `Manual review:` 行の後
- 空行を1つ入れてから `Review digest:` を出す
- `Artifacts:` より前に置く

## テスト追加
7. `test_directory_summary_has_review_digest`
8. `test_review_digest_contains_fixed_phrases`
9. `test_format_directory_summary_text_includes_review_digest`

---

## 受け入れ条件
次を満たしたら完了。

1. `latest_artifact` が summary に追加される
2. `comparison_rows` が summary に追加される
3. `review_digest` が summary に追加される
4. text summary に `Review digest:` block が出る
5. comparison rows は artifact 順と一致する
6. latest artifact は最後の sorted artifact を指す
7. full JSON は一切読まない
8. 既存 `--out` / `--summarize-dir` フローは壊さない
9. 新規テストが追加され、全テストが通る

---

## 実装順
必ずこの順で実装すること。

1. Task A: `latest_artifact`
2. Task B: `comparison_rows`
3. Task C: `review_digest`
4. `format_directory_summary_text()` 更新
5. テスト追加
6. 必要なら protocol を最小更新

---

## コミット分割
可能なら 2 コミットまで分けてよい。

### Option 1: 1コミット
```text
Add latest pointer, comparison rows, and review digest to directory summary
```

### Option 2: 2コミット
1. `Add latest artifact pointer and comparison rows`
2. `Add review digest to directory summary text`

---

## やってはいけないこと
- CSV 出力を足すこと
- `review_summary.py` を変更すること
- multi-domain 側にこの summary 拡張を広げること
- full artifact JSON を読むこと
- free-form 自然文の digest を生成すること
- fixed phrase 以外の文言を混ぜること

---

## 期待する差分の大きさ
- 中規模だが局所的
- 対象は live script とテストのみ
- OPUS が 1 回で実装可能な範囲
