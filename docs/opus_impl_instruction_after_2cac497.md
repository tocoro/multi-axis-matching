# OPUS 実装指示書（after 2cac497）

## この文書の位置づけ
これは**次の 1 コミット分の実装指示書**です。
設計書ではありません。実装対象、変更ファイル、追加関数、追加テストを固定します。

対象コミット: `2cac497`
このコミットで以下は完了済み。
- full artifact JSON 保存
- `.index.json` 保存
- `quick_verdict` と top candidate IDs の index 化
- 350 tests passing

したがって、今回の実装対象は **同一ディレクトリ内の index 群を一覧化する summary JSON の生成** に限定します。

---

## 今回の目的
`artifacts/` にたまる複数の `.index.json` を、後から一覧・比較しやすくする。

今回達成すること:
1. index 群だけを読んで summary JSON を生成する
2. full artifact JSON は読まない
3. 既存保存フローを壊さない
4. 最小限の横断比較入口を作る

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

### Task 1: summary builder を live script に追加

#### 変更ファイル
- `scripts/run_solution_catalog_live_ablation.py`

#### 追加する関数
```python
def build_artifact_directory_summary(index_items: list[dict]) -> dict:
    ...
```

#### この関数の責務
複数の index dict から、最小一覧 summary を作る。

#### 返り値の固定フォーマット
```json
{
  "total_runs": 3,
  "models": ["gemini-2.5-flash"],
  "queries": ["...", "..."],
  "verdict_counts": {
    "reason_changed": 3,
    "score_changed": 3,
    "confidence_changed": 1,
    "ranking_changed": 0,
    "unknown_reduced": 0,
    "disqualified_changed": 0
  },
  "artifacts": [
    {
      "artifact_path": "artifacts/case1.json",
      "query": "...",
      "model": "...",
      "timestamp": "...",
      "quick_verdict": { ... }
    }
  ]
}
```

#### 実装ルール
- `total_runs` は index 件数
- `models` はユニーク値を昇順で配列化
- `queries` はユニーク値を配列化。順序は入力順維持でよい
- `verdict_counts` は `quick_verdict` 内の各 bool が `true` の件数
- `artifacts` は入力 index を軽く整形した配列
- `top_candidates` は summary には含めない
- 新しい意味論を導入しない

---

### Task 2: `--out` 保存時にディレクトリ summary を更新

#### 変更ファイル
- `scripts/run_solution_catalog_live_ablation.py`

#### 実装内容
`--out` 指定時、保存先ディレクトリ内の `*.index.json` を読んで、summary JSON を 1 つ更新する。

#### 保存ルール
- full JSON: `artifacts/case1.json`
- index JSON: `artifacts/case1.index.json`
- directory summary: `artifacts/_index_summary.json`

#### 追加処理の流れ
1. full JSON 保存
2. `.index.json` 保存
3. `out_path.parent` 内の `*.index.json` を列挙
4. 各 index JSON を読み込む
5. `build_artifact_directory_summary(...)` を作る
6. `artifacts/_index_summary.json` に保存

#### 注意
- 読み込むのは `.index.json` のみ
- `full.json` は読まない
- 破損 JSON があった場合はそのファイルだけスキップしてよい
- スキップした件数を `skipped_files` として summary に入れてよい

#### `skipped_files` を入れる場合の形式
```json
"skipped_files": 1
```

入れても入れなくてもよいが、入れるなら int 固定。

---

### Task 3: CLI 出力に summary 更新先を 1 行追加

#### 変更ファイル
- `scripts/run_solution_catalog_live_ablation.py`

#### 追加形式
```text
Updated directory summary: artifacts/_index_summary.json
```

#### 注意
- 既存の 2 行は残す
- 末尾に 1 行追加するだけ

---

## テスト追加指示

### 変更ファイル
- `tests/test_live_ablation_script.py`

### 追加するテスト

#### 1. `test_build_artifact_directory_summary_has_required_keys`
確認項目:
- `total_runs`
- `models`
- `queries`
- `verdict_counts`
- `artifacts`

#### 2. `test_build_artifact_directory_summary_counts_verdicts`
- `quick_verdict.reason_changed=True` などの件数が正しく集計されること

#### 3. `test_build_artifact_directory_summary_does_not_include_top_candidates`
- summary 内の各 artifact に `top_candidates` を含めないこと

#### 4. `test_out_save_updates_directory_summary`
- temp dir を使い、2 本の index を置いて `_index_summary.json` が生成されること

#### 5. `test_directory_summary_total_runs_matches_index_count`
- summary の `total_runs` が index 件数に一致すること

---

## 受け入れ条件
次を満たしたら完了。

1. `build_artifact_directory_summary()` が追加される
2. `--out` 保存時に `_index_summary.json` が更新される
3. summary は `.index.json` だけを読む
4. `verdict_counts` が正しく集計される
5. CLI に summary 更新先が出る
6. full JSON / `.index.json` の既存挙動は変わらない
7. 新規テストが追加され、全テストが通る

---

## 実装順
必ずこの順で実装すること。

1. `build_artifact_directory_summary()` を追加
2. directory summary 更新処理を追加
3. CLI の 1 行追加
4. テスト追加
5. 必要なら protocol を最小更新

---

## コミットメッセージ案
```text
Add directory summary for live ablation indexes
```

---

## やってはいけないこと
- CSV 出力を足すこと
- `review_summary.py` を変更すること
- multi-domain 側に summary 集計を広げること
- full artifact JSON を summary 生成時に読むこと
- ランキング比較ロジックを新設すること

---

## 期待する差分の大きさ
- 小規模
- 1 コミットで十分
- 主変更は live script とそのテストのみ
