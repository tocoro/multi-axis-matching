# OPUS 実装指示書（after c7bf18d）

## この文書の位置づけ
これは**次の 1 コミット分の実装指示書**です。
設計書ではありません。実装対象、変更ファイル、追加関数、追加テストを固定します。

対象コミット: `c7bf18d`
このコミットで以下は完了済み。
- full artifact JSON 保存
- `.index.json` 保存
- `_index_summary.json` 保存
- 355 tests passing

したがって、今回の実装対象は **directory summary に最小 trend 情報を追加すること** に限定します。

---

## 今回の目的
`_index_summary.json` を見たときに、個別 artifact を開かずとも「このディレクトリでは何が主に変化しているか」が一目で分かるようにする。

今回達成すること:
1. `verdict_counts` から派生する trend 情報を追加する
2. 新しい意味論は導入しない
3. 既存 summary を壊さない
4. index 群だけを見て計算する

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

## 実装タスク

### Task 1: directory summary に `trend_summary` を追加

#### 変更ファイル
- `scripts/run_solution_catalog_live_ablation.py`

#### 変更対象関数
```python
def build_artifact_directory_summary(index_items: list[dict]) -> dict:
    ...
```

#### 追加するキー
返り値に `trend_summary` を追加する。

#### 固定フォーマット
```json
"trend_summary": {
  "dominant_changes": ["reason_changed", "score_changed"],
  "stable_signals": ["ranking_changed", "unknown_reduced", "disqualified_changed"],
  "run_coverage": {
    "reason_changed": 3,
    "score_changed": 3,
    "confidence_changed": 1,
    "ranking_changed": 0,
    "unknown_reduced": 0,
    "disqualified_changed": 0
  }
}
```

#### 計算ルール
- `run_coverage` は `verdict_counts` をそのまま再利用する
- `dominant_changes` は count > 0 のキーを、count 降順・キー名昇順 tie-break で並べた配列
- `stable_signals` は count == 0 のキーを、元の verdict key 順で並べた配列
- verdict key 順は固定:
  1. `reason_changed`
  2. `score_changed`
  3. `confidence_changed`
  4. `ranking_changed`
  5. `unknown_reduced`
  6. `disqualified_changed`

#### 注意
- 割合は出さない
- `%` 表示は作らない
- dominant は top1 ではなく「count > 0 を全部」
- 新しい意味づけを足さない

---

### Task 2: CLI 出力に trend 1 行を追加

#### 変更ファイル
- `scripts/run_solution_catalog_live_ablation.py`

#### 実装内容
`--out` 保存時、directory summary 更新後に 1 行だけ追加する。

#### 出力形式
```text
Directory trends: dominant=reason_changed,score_changed stable=ranking_changed,unknown_reduced,disqualified_changed
```

#### 実装ルール
- `trend_summary` から生成する
- 配列が空の場合は `none` を使う
  - 例: `dominant=none`
- 既存 3 行は残す
- 末尾に 1 行追加するだけ

---

## テスト追加指示

### 変更ファイル
- `tests/test_live_ablation_script.py`

### 追加するテスト

#### 1. `test_directory_summary_has_trend_summary`
- `trend_summary` キーが存在すること

#### 2. `test_trend_summary_run_coverage_matches_verdict_counts`
- `trend_summary["run_coverage"] == summary["verdict_counts"]`

#### 3. `test_trend_summary_stable_signals_include_zero_count_keys`
- count == 0 の verdict keys が `stable_signals` に入ること

#### 4. `test_trend_summary_dominant_changes_include_positive_count_keys`
- count > 0 の verdict keys が `dominant_changes` に入ること

#### 5. `test_cli_trend_line_format`
- 生成文字列に `Directory trends:` が含まれること

---

## 受け入れ条件
次を満たしたら完了。

1. `_index_summary.json` に `trend_summary` が追加される
2. `run_coverage` が `verdict_counts` と一致する
3. `dominant_changes` が count > 0 を表す
4. `stable_signals` が count == 0 を表す
5. CLI に trend 1 行が出る
6. 既存 summary のキーは維持される
7. 新規テストが追加され、全テストが通る

---

## 実装順
必ずこの順で実装すること。

1. `build_artifact_directory_summary()` に `trend_summary` を追加
2. CLI の trend 1 行を追加
3. テスト追加
4. 必要なら protocol を最小更新

---

## コミットメッセージ案
```text
Add trend summary to live ablation directory summary
```

---

## やってはいけないこと
- 比率や統計を入れること
- CSV 出力を足すこと
- `review_summary.py` を変更すること
- multi-domain 側に trend 集計を広げること
- full artifact JSON を trend 計算時に読むこと

---

## 期待する差分の大きさ
- 小規模
- 1 コミットで十分
- 主変更は live script とそのテストのみ
