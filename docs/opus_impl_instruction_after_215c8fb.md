# OPUS 実装指示書（after 215c8fb）

## この文書の位置づけ
これは設計書ではなく、**次の実装差分を書くための実装指示書** です。

対象コミット: `215c8fb`
このコミットで以下は完了済み。
- `review_summary` の追加
- `cross_domain_review_summary` の追加
- CLI 表示の review_summary 化
- review_summary 系テスト追加

したがって、今回の実装対象は **review_summary を live 実験運用に使いやすくするための最小改善** に限定する。

---

## 今回の実装目的
live 実験結果を複数回保存・比較・レビューしやすくする。

具体的には次を達成すること。
1. 保存 JSON に review 用メタ情報を追加する
2. 単発 run の再現条件が後で読めるようにする
3. review_summary の主要変化を artifacts 収集時に見失わないようにする
4. 既存意味論を一切変えない

---

## 変更してよいファイル
今回変更してよいのは次のファイルのみ。

- `scripts/run_solution_catalog_live_ablation.py`
- `src/experiments/review_summary.py`
- `tests/test_live_ablation_script.py`
- `tests/test_review_summary.py`
- 必要なら `docs/solution_catalog_live_ablation_protocol.md`

**上記以外は触らないこと。**

---

## 変更してはいけないもの
以下は変更禁止。

- `src/evaluator.py`
- score aggregation の式
- unknown の扱い
- ranking ロジック
- `diff_summary` の既存キー
- `run_multi_domain_ablation()` の catalog off 実装
- prompt 契約

---

## 実装タスク

### Task 1: live 保存 JSON に `run_metadata` を追加

#### 変更ファイル
- `scripts/run_solution_catalog_live_ablation.py`

#### 変更内容
`run_live_ablation()` の返り値に `run_metadata` キーを追加する。

#### 追加するキー
```json
"run_metadata": {
  "query": "<query>",
  "model": "<model>",
  "timestamp": "<timestamp>",
  "catalog_mode": "with_vs_without",
  "candidate_source": "unknown",
  "is_live_llm": true,
  "review_summary_version": 1
}
```

#### 実装ルール
- `query`, `model`, `timestamp` は既存値を再利用する
- `catalog_mode` は固定文字列 `with_vs_without`
- `candidate_source` は現時点では固定で `unknown` とする
- `is_live_llm` は固定で `true`
- `review_summary_version` は固定で `1`

#### 注意
- 既存 top-level の `query`, `model`, `timestamp` は残す
- `run_metadata` は追記のみ
- 既存 consumer を壊さない

---

### Task 2: `review_summary` に `quick_verdict` を追加

#### 変更ファイル
- `src/experiments/review_summary.py`

#### 変更内容
`build_review_summary()` の返り値に `quick_verdict` を追加する。

#### 追加フォーマット
```json
"quick_verdict": {
  "ranking_changed": false,
  "reason_changed": true,
  "score_changed": true,
  "confidence_changed": false,
  "unknown_reduced": false,
  "disqualified_changed": false
}
```

#### 実装ルール
- bool 値のみで構成する
- 各値は既存 review_summary の中間計算から導出する
- 新しい判定ロジックを作らない

#### 具体ルール
- `ranking_changed` → `ranking.changed`
- `reason_changed` → `len(reason.changed_candidates) > 0`
- `score_changed` → `len(score.changed_candidates) > 0`
- `confidence_changed` → `len(confidence.changed_candidates) > 0`
- `unknown_reduced` → `len(unknown.reduced_candidates) > 0`
- `disqualified_changed` → `len(disqualified.changed_candidates) > 0`

---

### Task 3: CLI summary の末尾に one-line verdict を追加

#### 変更ファイル
- `src/experiments/review_summary.py`
- `scripts/run_solution_catalog_live_ablation.py`

#### 変更内容
`format_review_summary_text()` の末尾に 1 行の verdict を追加する。

#### 追加形式
```text
Verdict: reason_changed=yes, score_changed=yes, ranking_changed=no, unknown_reduced=no
```

#### 実装ルール
- `quick_verdict` を利用して生成する
- yes/no 表記を使う
- 順序は固定する
  1. reason_changed
  2. score_changed
  3. confidence_changed
  4. ranking_changed
  5. unknown_reduced
  6. disqualified_changed

#### 注意
- 既存の人間向け summary を消さない
- 末尾に 1 行足すだけ

---

### Task 4: multi-domain の `cross_domain_review_summary` に `quick_verdict` を追加しない

#### 理由
今回の変更は single-run 保存と人間レビュー補助に限定する。
`cross_domain_review_summary` に派生キーを増やすのは次段階に回す。

#### 指示
- `build_cross_domain_review_summary()` は今回変更しない

---

## テスト追加指示

### 変更ファイル
- `tests/test_live_ablation_script.py`
- `tests/test_review_summary.py`

### 追加するテスト

#### A. `tests/test_live_ablation_script.py`
以下のテストを追加すること。

1. `test_result_has_run_metadata`
- `run_live_ablation()` の結果に `run_metadata` があること

2. `test_run_metadata_has_required_keys`
- `query`, `model`, `timestamp`, `catalog_mode`, `candidate_source`, `is_live_llm`, `review_summary_version` を確認

3. `test_run_metadata_catalog_mode_fixed`
- `catalog_mode == "with_vs_without"`

#### B. `tests/test_review_summary.py`
以下のテストを追加すること。

4. `test_quick_verdict_exists`
- `review_summary` に `quick_verdict` があること

5. `test_quick_verdict_matches_existing_sections`
- `reason_changed` などが既存 section と整合すること

6. `test_format_includes_verdict_line`
- `format_review_summary_text()` の出力に `Verdict:` が含まれること

7. `test_verdict_shows_unknown_reduced_no_for_mock_case`
- 既存 mock case で `unknown_reduced=no` が出ること

---

## 受け入れ条件
次を満たしたら完了。

1. `run_live_ablation()` の JSON に `run_metadata` が追加される
2. `review_summary.quick_verdict` が追加される
3. CLI 出力に `Verdict:` 行が出る
4. 既存 `diff_summary` は変わらない
5. 既存 review_summary テストを壊さない
6. 新規テストが追加される
7. 全テストが通る

---

## 実装順
必ずこの順に実装すること。

1. `src/experiments/review_summary.py` に `quick_verdict` 追加
2. `format_review_summary_text()` に verdict 行追加
3. `scripts/run_solution_catalog_live_ablation.py` に `run_metadata` 追加
4. テスト追加
5. 必要なら protocol 文書を最小更新

---

## コミットメッセージ案
```text
Add live ablation run metadata and quick verdict
```

---

## やってはいけないこと
- `cross_domain_review_summary` を今回いじること
- score / confidence の意味を変えること
- unknown 判定を変えること
- review_summary の既存キー名を変えること
- docs だけ更新して実装を変えないこと

---

## 期待する差分の大きさ
- 追加コードは小規模
- ロジック追加は `review_summary.py` と live script に限定
- 1コミットで十分
