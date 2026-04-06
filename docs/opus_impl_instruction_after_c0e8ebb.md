# OPUS 実装指示書（after c0e8ebb）

## この文書の位置づけ
これは**次の 1 コミット分の実装指示書**です。
設計書ではありません。実装対象、変更ファイル、追加関数、追加テストを固定します。

対象コミット: `c0e8ebb`
このコミットで以下は完了済み。
- `run_metadata` 追加
- `quick_verdict` 追加
- CLI verdict 行追加
- 345 tests passing

したがって、今回の実装対象は **saved artifacts を後で一覧・比較しやすくするための最小インデックス生成** に限定します。

---

## 今回の目的
`run_solution_catalog_live_ablation.py --out ...` で保存した JSON を、あとからディレクトリ単位で見返しやすくする。

今回達成すること:
1. artifact 保存時に軽量 index JSON を同時生成する
2. index には review に必要な最小情報だけを入れる
3. 元の full JSON は変えない
4. live 実験の比較起点を作る

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

### Task 1: artifact index writer を live script に追加

#### 変更ファイル
- `scripts/run_solution_catalog_live_ablation.py`

#### 追加する関数
```python
def build_artifact_index(result: dict) -> dict:
    ...
```

#### この関数の責務
full result から、比較に必要な最小情報だけを抜き出した index dict を作る。

#### 返り値の固定フォーマット
```json
{
  "query": "...",
  "model": "...",
  "timestamp": "...",
  "artifact_path": "...",
  "catalog_mode": "with_vs_without",
  "quick_verdict": {
    "ranking_changed": false,
    "reason_changed": true,
    "score_changed": true,
    "confidence_changed": false,
    "unknown_reduced": false,
    "disqualified_changed": false
  },
  "top_candidates": {
    "with_catalog": ["place_1", "place_2", "place_3"],
    "without_catalog": ["place_1", "place_2", "place_3"]
  }
}
```

#### 実装ルール
- `query`, `model`, `timestamp` は top-level の既存値を使う
- `catalog_mode` は `run_metadata.catalog_mode` を使う
- `quick_verdict` は `review_summary.quick_verdict` をそのまま使う
- `top_candidates.with_catalog` は `with_catalog.ranking[:3]` の `candidate_id` 配列
- `top_candidates.without_catalog` は `without_catalog.ranking[:3]` の `candidate_id` 配列
- ranking が 3 件未満なら存在分だけでよい
- 新しい意味論を導入しない

---

### Task 2: `--out` 保存時に `.index.json` を同時生成

#### 変更ファイル
- `scripts/run_solution_catalog_live_ablation.py`

#### 実装内容
既存の full JSON 保存ロジックの直後に、index JSON を保存する処理を追加する。

#### 保存ルール
- 既存 `--out artifacts/live_case_1.json` のとき
- 追加で `artifacts/live_case_1.index.json` を生成する

#### 追加処理の流れ
1. `result = run_live_ablation(...)`
2. full JSON を既存どおり保存
3. `index = build_artifact_index(result)` を作る
4. `index["artifact_path"] = str(out_path)` を設定
5. `<stem>.index.json` に保存

#### 注意
- full JSON 保存を壊さない
- index 保存失敗で full JSON を消さない
- ただし今回はシンプルに、例外はそのまま出してよい

---

### Task 3: CLI 出力に index 保存先を 1 行追加

#### 変更ファイル
- `scripts/run_solution_catalog_live_ablation.py`

#### 実装内容
`--out` 指定時、保存完了後に 2 行出す。

#### 出力形式
```text
Saved full result to: artifacts/live_case_1.json
Saved index to: artifacts/live_case_1.index.json
```

#### 注意
- 既存 summary 出力はそのまま残す
- 末尾に 2 行追加するだけ

---

## テスト追加指示

### 変更ファイル
- `tests/test_live_ablation_script.py`

### 追加するテスト

#### 1. `test_build_artifact_index_has_required_keys`
確認項目:
- `query`
- `model`
- `timestamp`
- `artifact_path`
- `catalog_mode`
- `quick_verdict`
- `top_candidates`

#### 2. `test_build_artifact_index_uses_quick_verdict`
- `index["quick_verdict"] == result["review_summary"]["quick_verdict"]`

#### 3. `test_build_artifact_index_top_candidates_are_candidate_ids`
- `with_catalog` / `without_catalog` が candidate_id 配列であること

#### 4. `test_out_save_creates_index_file`
- temp path を使い、full JSON と `.index.json` の両方ができることを確認

#### 5. `test_index_file_contains_artifact_path`
- 保存された `.index.json` の `artifact_path` が full JSON の path を指すこと

---

## 受け入れ条件
次を満たしたら完了。

1. `build_artifact_index()` が追加される
2. `--out` 保存時に `.index.json` が作られる
3. index に quick_verdict が入る
4. index に top 3 candidate IDs が入る
5. CLI に保存先 2 行が出る
6. full JSON 保存の既存挙動は変わらない
7. 新規テストが追加され、全テストが通る

---

## 実装順
必ずこの順で実装すること。

1. `build_artifact_index()` を追加
2. `--out` 保存時の `.index.json` 生成を追加
3. CLI の保存先表示を追加
4. テスト追加
5. 必要なら protocol を最小更新

---

## コミットメッセージ案
```text
Add artifact index for live ablation outputs
```

---

## やってはいけないこと
- `review_summary.py` を今回いじること
- multi-domain 側に index 機能を広げること
- CSV 出力を足すこと
- artifact 一覧集計まで始めること
- 保存形式の既存キー名を変えること

---

## 期待する差分の大きさ
- 小規模
- 1 コミットで十分
- 主変更は live script とそのテストのみ
