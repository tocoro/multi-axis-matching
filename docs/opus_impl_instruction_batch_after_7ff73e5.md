# OPUS 実装指示書（batch after 7ff73e5）

## この文書の位置づけ
これは**複数タスクをまとめた実装指示書**です。
設計書ではありません。実装対象、変更ファイル、追加関数、追加テストを固定します。

対象コミット: `7ff73e5`
このコミットで以下は完了済み。
- full artifact JSON 保存
- `.index.json` 保存
- `_index_summary.json` 保存
- `trend_summary` 保存
- `anomaly_flags` 保存
- 365 tests passing

したがって、今回の実装対象は **live ablation artifacts を review しやすくする最終整理** に限定します。

この指示書は 3 タスクで構成する。
- Task A: artifact list の安定並び順
- Task B: directory summary の human-readable text 生成
- Task C: `--summarize-dir` CLI 追加

---

## 今回の目的
保存済み artifact ディレクトリに対して、
- 毎回同じ順で見える
- JSON を開かなくても概要を読める
- 既存 artifact 群をあとから再集計できる

状態にする。

新しい評価意味論は追加しない。

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

# Task A: artifact list の安定並び順

## 目的
`_index_summary.json` の `artifacts` 配列を、毎回同じ規則で並ぶようにする。

## 変更ファイル
- `scripts/run_solution_catalog_live_ablation.py`

## 変更対象関数
```python
def build_artifact_directory_summary(index_items: list[dict]) -> dict:
    ...
```

## 実装内容
`artifacts` 配列を作る前に、入力 index items を以下のキーでソートすること。

### ソート優先順
1. `timestamp` 昇順
2. `model` 昇順
3. `artifact_path` 昇順

### 実装ルール
- 空文字はそのまま比較してよい
- timestamp は文字列比較でよい
- `models` と `queries` の集約ロジックはそのまま維持
- `artifacts` 配列だけ順序を安定化すればよい

## テスト追加
### `tests/test_live_ablation_script.py`
1. `test_directory_summary_artifacts_sorted_by_timestamp_model_path`
- unsorted な index_items を与え、`artifacts` の順が固定されること

---

# Task B: directory summary の human-readable text 生成

## 目的
`_index_summary.json` と同じ情報を、人間がすぐ読める text に変換できるようにする。

## 変更ファイル
- `scripts/run_solution_catalog_live_ablation.py`

## 追加する関数
```python
def format_directory_summary_text(summary: dict) -> str:
    ...
```

## 出力フォーマット（固定）
以下のような複数行文字列を返すこと。

```text
=== Live Ablation Directory Summary ===
Total runs: 3
Models: gemini-2.5-flash
Queries: 2

Dominant changes: reason_changed, score_changed
Stable signals: ranking_changed, unknown_reduced, disqualified_changed
Manual review: no

Artifacts:
- 2026-04-06T15:00:00Z | gemini-2.5-flash | artifacts/case1.json
- 2026-04-06T15:01:00Z | gemini-2.5-flash | artifacts/case2.json
```

## 実装ルール
- `Models:` は `summary["models"]` を `, `.join
- `Queries:` は `len(summary["queries"])`
- `Dominant changes:` は `trend_summary.dominant_changes`、空なら `none`
- `Stable signals:` は `trend_summary.stable_signals`、空なら `none`
- `Manual review:` は `anomaly_flags.needs_manual_review` を `yes/no`
- `Artifacts:` 以下は summary の `artifacts` 配列順で 1 行ずつ
- 各行の形式は固定
  - `- {timestamp} | {model} | {artifact_path}`
- query は artifact 行に含めない
- top_candidates は表示しない

## テスト追加
### `tests/test_live_ablation_script.py`
2. `test_format_directory_summary_text_has_header`
3. `test_format_directory_summary_text_shows_manual_review`
4. `test_format_directory_summary_text_lists_artifacts`

---

# Task C: `--summarize-dir` CLI 追加

## 目的
保存済みディレクトリをあとから再集計し、summary text を表示できるようにする。

## 変更ファイル
- `scripts/run_solution_catalog_live_ablation.py`

## CLI 仕様追加
既存引数に加えて、以下を追加すること。

```text
--summarize-dir <path>
```

## 動作仕様
`--summarize-dir` が指定された場合:
1. そのディレクトリ内の `*.index.json` を列挙
2. 各 index JSON を読む
3. `build_artifact_directory_summary()` を作る
4. `format_directory_summary_text()` を stdout に出す
5. `_index_summary.json` を同ディレクトリに保存する
6. exit code 0 で終了する

## 制約
- このモードでは `--query` は不要
- `--summarize-dir` がある場合、通常の live 実行はしない
- 読み込むのは `.index.json` のみ
- 壊れた JSON はスキップしてよい
- full JSON は読まない

## 保存ルール
- 出力先は `<dir>/_index_summary.json`

## CLI 出力
`format_directory_summary_text(summary)` のあとに 1 行追加すること。

```text
Saved directory summary to: artifacts/_index_summary.json
```

## テスト追加
### `tests/test_live_ablation_script.py`
5. `test_summarize_dir_writes_index_summary`
- tmp dir に index files を置き、`_index_summary.json` ができること

6. `test_summarize_dir_uses_only_index_json`
- full JSON が存在しても `.index.json` のみ読んで summary できること

7. `test_summarize_dir_text_output_contains_header`
- 出力 text に `=== Live Ablation Directory Summary ===` が含まれること

---

## 受け入れ条件
次を満たしたら完了。

1. `artifacts` 配列の順序が安定化される
2. `format_directory_summary_text()` が追加される
3. `--summarize-dir` で既存ディレクトリを再集計できる
4. `_index_summary.json` が再生成される
5. text summary が stdout に出る
6. full JSON は一切読まない
7. 既存 `--out` フローは壊さない
8. 新規テストが追加され、全テストが通る

---

## 実装順
必ずこの順で実装すること。

1. Task A: `artifacts` の並び順を安定化
2. Task B: `format_directory_summary_text()` を追加
3. Task C: `--summarize-dir` を追加
4. テスト追加
5. 必要なら protocol を最小更新

---

## コミット分割
可能なら 2 コミットまで分けてよい。

### Option 1: 1コミット
```text
Add directory summary text and summarize-dir CLI
```

### Option 2: 2コミット
1. `Stabilize artifact ordering and add directory summary text`
2. `Add summarize-dir CLI for live ablation artifacts`

---

## やってはいけないこと
- CSV 出力を足すこと
- `review_summary.py` を変更すること
- multi-domain 側にこの CLI を広げること
- full artifact JSON を読むこと
- summary text に candidate 詳細を出すこと
- query を artifact 行に混ぜること

---

## 期待する差分の大きさ
- 中規模だが局所的
- 対象は live script とテストのみ
- OPUS が 1 回で実装可能な範囲
