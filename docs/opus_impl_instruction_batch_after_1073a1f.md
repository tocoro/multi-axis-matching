# OPUS 実装指示書（batch after 1073a1f）

## この文書の位置づけ
これは**複数タスクをまとめた実装指示書**です。
設計書ではありません。実装対象、変更ファイル、追加関数、追加テストを固定します。

対象コミット: `1073a1f`
このコミットで以下は完了済み。
- full artifact JSON 保存
- `.index.json` 保存
- `_index_summary.json` 保存
- `trend_summary` / `anomaly_flags`
- `latest_artifact` / `comparison_rows` / `comparison_stats` / `flagged_rows` / `review_digest`
- `format_directory_summary_text()`
- `--summarize-dir` CLI
- 390 tests passing

したがって、今回の実装対象は **directory summary から注目 run を即座に取り出せるようにする拡張** に限定します。

この指示書は 3 タスクで構成する。
- Task A: `focus_rows` を追加
- Task B: `recommended_artifact_paths` を追加
- Task C: text summary に `Recommended artifacts` block を追加

---

## 今回の目的
`_index_summary.json` を見たときに、
- まずどの run を見ればよいか
- flagged がない場合でも何を開けばよいか
- 注目 run が summary 内で明示されているか

をすぐ判断できるようにする。

新しい評価意味論は追加しない。
既存の `flagged_rows` / `latest_artifact` / `comparison_rows` / `comparison_stats` だけを再構成する。

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

# Task A: `focus_rows` を追加

## 目的
summary 内に「今見るべき rows」を明示する。

## 変更ファイル
- `scripts/run_solution_catalog_live_ablation.py`

## 変更対象関数
```python
def build_artifact_directory_summary(index_items: list[dict]) -> dict:
    ...
```

## 追加するキー
返り値に `focus_rows` を追加する。

## フォーマット（固定）
```json
"focus_rows": [
  {
    "timestamp": "2026-04-06T15:00:00Z",
    "model": "gemini-2.5-flash",
    "artifact_path": "artifacts/case1.json",
    "manual_review": true,
    "focus_reason": "flagged"
  },
  {
    "timestamp": "2026-04-06T15:10:00Z",
    "model": "gemini-2.5-flash",
    "artifact_path": "artifacts/case3.json",
    "manual_review": false,
    "focus_reason": "latest"
  }
]
```

## 計算ルール
- `flagged_rows` が 1 件以上ある場合
  - `focus_rows = flagged_rows` に `focus_reason: "flagged"` を付けたもの
- `flagged_rows` が空で、`latest_artifact` がある場合
  - `comparison_rows` の中から `artifact_path == latest_artifact.artifact_path` の row を 1 件選び、`focus_reason: "latest"` を付ける
- `flagged_rows` も `latest_artifact` もない場合
  - 空配列
- `focus_rows` の順序は元 row 順を維持
- `focus_reason` は `flagged` または `latest` のみ
- query は含めない

## テスト追加
1. `test_directory_summary_has_focus_rows`
2. `test_focus_rows_use_flagged_rows_when_present`
3. `test_focus_rows_fall_back_to_latest_when_no_flagged_rows`
4. `test_focus_rows_empty_when_no_rows`

---

# Task B: `recommended_artifact_paths` を追加

## 目的
CLI でも JSON でも、まず開くべき artifact path 群を簡単に取れるようにする。

## 変更ファイル
- `scripts/run_solution_catalog_live_ablation.py`

## 変更対象関数
```python
def build_artifact_directory_summary(index_items: list[dict]) -> dict:
    ...
```

## 追加するキー
返り値に `recommended_artifact_paths` を追加する。

## フォーマット（固定）
```json
"recommended_artifact_paths": [
  "artifacts/case1.json",
  "artifacts/case3.json"
]
```

## 計算ルール
- `focus_rows` の `artifact_path` を順に抜き出す
- 重複があれば先勝ちで重複除去
- `focus_rows` が空なら空配列

## テスト追加
5. `test_directory_summary_has_recommended_artifact_paths`
6. `test_recommended_artifact_paths_follow_focus_rows_order`
7. `test_recommended_artifact_paths_deduplicate_preserving_order`

---

# Task C: text summary に `Recommended artifacts` block を追加

## 目的
人間向け text summary に「まず開くべき artifact」を表示する。

## 変更ファイル
- `scripts/run_solution_catalog_live_ablation.py`

## 変更対象
```python
def format_directory_summary_text(summary: dict) -> str:
    ...
```

## 追加する block
`Flagged rows:` の後、`Artifacts:` の前に `Recommended artifacts:` block を追加する。

## 出力形式
artifact がある場合:
```text
Recommended artifacts:
- artifacts/case1.json
- artifacts/case3.json
```

空の場合:
```text
Recommended artifacts: none
```

## 配置
- `Flagged rows:` block の後
- 空行を1つ入れてから出す
- `Artifacts:` より前に置く

## 実装ルール
- `recommended_artifact_paths` をそのまま使う
- 1行の形式は固定
  - `- {artifact_path}`
- timestamp や model は出さない

## テスト追加
8. `test_format_directory_summary_text_includes_recommended_artifacts_header`
9. `test_format_directory_summary_text_recommended_artifacts_none_when_empty`
10. `test_format_directory_summary_text_lists_recommended_artifacts`

---

## 受け入れ条件
次を満たしたら完了。

1. `focus_rows` が summary に追加される
2. `recommended_artifact_paths` が summary に追加される
3. flagged がある場合は flagged が優先される
4. flagged がない場合は latest row に fallback する
5. text summary に `Recommended artifacts` block が出る
6. full JSON は一切読まない
7. 既存 `--out` / `--summarize-dir` フローは壊さない
8. 新規テストが追加され、全テストが通る

---

## 実装順
必ずこの順で実装すること。

1. Task A: `focus_rows`
2. Task B: `recommended_artifact_paths`
3. Task C: `format_directory_summary_text()` 更新
4. テスト追加
5. 必要なら protocol を最小更新

---

## コミット分割
可能なら 2 コミットまで分けてよい。

### Option 1: 1コミット
```text
Add focus rows and recommended artifacts to directory summary
```

### Option 2: 2コミット
1. `Add focus rows and recommended artifact paths`
2. `Show recommended artifacts in directory summary text`

---

## やってはいけないこと
- CSV 出力を足すこと
- `review_summary.py` を変更すること
- multi-domain 側にこの summary 拡張を広げること
- full artifact JSON を読むこと
- focus_reason に free-form 文を入れること
- text summary に comparison table をそのまま出すこと

---

## 期待する差分の大きさ
- 中規模だが局所的
- 対象は live script とテストのみ
- OPUS が 1 回で実装可能な範囲
