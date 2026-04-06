# OPUS 実装指示書（after ee37c42）

## この文書の位置づけ
これは**次の 1 コミット分の実装指示書**です。
設計書ではありません。実装対象、変更ファイル、追加関数、追加テストを固定します。

対象コミット: `ee37c42`
このコミットで以下は完了済み。
- full artifact JSON 保存
- `.index.json` 保存
- `_index_summary.json` 保存
- `trend_summary` 保存
- 360 tests passing

したがって、今回の実装対象は **directory summary に最小 anomaly flag を追加すること** に限定します。

---

## 今回の目的
`_index_summary.json` を見た時に、正常系か、少なくとも一度は目視確認した方がよい run 群かを、即座に判断できるようにする。

今回達成すること:
1. 既存 `verdict_counts` と `trend_summary` だけから anomaly flag を導出する
2. 新しい意味論は導入しない
3. 既存 summary を壊さない
4. full JSON は読まない

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

### Task 1: directory summary に `anomaly_flags` を追加

#### 変更ファイル
- `scripts/run_solution_catalog_live_ablation.py`

#### 変更対象関数
```python
def build_artifact_directory_summary(index_items: list[dict]) -> dict:
    ...
```

#### 追加するキー
返り値に `anomaly_flags` を追加する。

#### 固定フォーマット
```json
"anomaly_flags": {
  "ranking_changed_present": false,
  "unknown_reduced_present": false,
  "disqualified_changed_present": false,
  "confidence_changed_without_reason_changed": false,
  "needs_manual_review": false
}
```

#### 計算ルール
既存 `verdict_counts` と `trend_summary` だけを使うこと。

- `ranking_changed_present`
  - `verdict_counts["ranking_changed"] > 0`
- `unknown_reduced_present`
  - `verdict_counts["unknown_reduced"] > 0`
- `disqualified_changed_present`
  - `verdict_counts["disqualified_changed"] > 0`
- `confidence_changed_without_reason_changed`
  - `verdict_counts["confidence_changed"] > 0 and verdict_counts["reason_changed"] == 0`
- `needs_manual_review`
  - 上記4つのうち、どれかが `true` なら `true`

#### 注意
- anomaly は「異常断定」ではなく review flag として扱う
- 新しい推定ロジックを作らない
- candidate 単位の解析はしない
- full artifact JSON は読まない

---

### Task 2: CLI 出力に anomaly 1 行を追加

#### 変更ファイル
- `scripts/run_solution_catalog_live_ablation.py`

#### 出力形式
```text
Directory anomaly flags: manual_review=no ranking_changed=no unknown_reduced=no disqualified_changed=no confidence_without_reason=no
```

#### 実装ルール
- `anomaly_flags` から生成する
- yes/no 表記を使う
- 順序は固定:
  1. `manual_review`
  2. `ranking_changed`
  3. `unknown_reduced`
  4. `disqualified_changed`
  5. `confidence_without_reason`
- 既存の trend 行は残す
- 末尾に 1 行追加するだけ

---

## テスト追加指示

### 変更ファイル
- `tests/test_live_ablation_script.py`

### 追加するテスト

#### 1. `test_directory_summary_has_anomaly_flags`
- `anomaly_flags` キーが存在すること

#### 2. `test_anomaly_flags_false_for_normal_mock_summary`
- 既存 mock summary では主要フラグがすべて false であること

#### 3. `test_anomaly_flags_manual_review_true_when_unknown_reduced_present`
- 手で `verdict_counts["unknown_reduced"] = 1` にした summary で `needs_manual_review` が true になること

#### 4. `test_anomaly_flags_manual_review_true_when_ranking_changed_present`
- 手で `verdict_counts["ranking_changed"] = 1` にした summary で `needs_manual_review` が true になること

#### 5. `test_cli_anomaly_line_format`
- 生成文字列に `Directory anomaly flags:` が含まれること

---

## 受け入れ条件
次を満たしたら完了。

1. `_index_summary.json` に `anomaly_flags` が追加される
2. `needs_manual_review` が既定ルールどおり導出される
3. normal mock summary では anomaly flags が false になる
4. CLI に anomaly 1 行が出る
5. 既存 summary / trend_summary のキーは維持される
6. 新規テストが追加され、全テストが通る

---

## 実装順
必ずこの順で実装すること。

1. `build_artifact_directory_summary()` に `anomaly_flags` を追加
2. CLI の anomaly 1 行を追加
3. テスト追加
4. 必要なら protocol を最小更新

---

## コミットメッセージ案
```text
Add anomaly flags to live ablation directory summary
```

---

## やってはいけないこと
- 比率や統計を入れること
- CSV 出力を足すこと
- `review_summary.py` を変更すること
- multi-domain 側に anomaly 集計を広げること
- full artifact JSON を anomaly 計算時に読むこと
- anomaly を説明文に変換すること

---

## 期待する差分の大きさ
- 小規模
- 1 コミットで十分
- 主変更は live script とそのテストのみ
