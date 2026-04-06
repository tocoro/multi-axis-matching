# Live Ablation Readability 改善設計書

## 目的
live ablation の出力を、人間が短時間でレビューしやすい形に改善する。

ranking だけではなく、以下の変化を読みやすくすることを目的とする。
- reason
- total_score
- confidence
- unknown / missing_information
- disqualified
- catalog 参照の有無

この改善は**表示と要約の改善**であり、evaluator の意味論そのものを変更しない。

---

## 対象範囲
今回の対象は、live ablation 結果の出力整形と差分要約である。

主な対象:
- `scripts/run_solution_catalog_live_ablation.py`
- `src.experiments.catalog_ablation`
- `src.experiments.multi_domain_catalog_ablation`
- 必要に応じて `tests/test_live_ablation_script.py`
- 必要に応じて ablation 系テスト

対象外:
- score aggregation ロジックの変更
- evaluator の prompt 意味論変更
- unknown 判定ロジック変更
- ranking ロジック変更
- catalog usage contract の変更

---

## 背景認識
現状でも catalog on/off の diff は取れているが、live review では次の問題がある。

1. 差分が構造として存在していても、人間が一目で読み取りにくい
2. reason / score / confidence / unknown が散在し、レビュー観点ごとの整理が弱い
3. ranking が不変な場合でも「何が変わったのか」が把握しづらい
4. cross-domain で比較する場合、どの domain で何が起きたかを素早く掴みにくい

よって、**diff の情報量を増やすのではなく、解釈しやすい形に再構成すること**が必要。

---

## 改善方針

### 1. diff summary を観点別に再構成する
現在の差分情報を維持しつつ、レビュー観点別に整理した summary を追加する。

追加したい観点:
- ranking 変化
- score 変化
- confidence 変化
- reason 変化
- unknown / missing_information 変化
- disqualified 変化

重要なのは、**既存の machine-readable な差分を壊さずに、review 用 summary を別レイヤーで追加すること**。

### 2. 「変化なし」も明示的に読めるようにする
live 実験では、ranking 不変 / unknown 不変 がむしろ自然な場合がある。

したがって、
- 変化した項目だけを出す
のではなく、
- 重要観点について「変化なし」も分かる構造
にする。

### 3. catalog の寄与を過大解釈させない
summary 表現は、catalog によって unknown が解決されたように見せてはならない。

表現ポリシー:
- reason change は「補強」または「補助説明の変化」として扱う
- score change は差分量を出してよい
- unknown は reduced / unchanged を区別する
- ranking unchanged は正常ケースとして扱う

---

## 追加する出力構造

### A. single-domain live ablation result
既存の結果 JSON に、`review_summary` を追加する。

想定形:

```json
{
  "query": "...",
  "model": "...",
  "with_catalog": { ... },
  "without_catalog": { ... },
  "diff_summary": { ... },
  "review_summary": {
    "ranking": {
      "changed": false,
      "note": "ranking unchanged"
    },
    "score": {
      "changed_candidates": [
        {"candidate_id": "place_1", "delta": 0.03},
        {"candidate_id": "place_3", "delta": -0.02}
      ]
    },
    "confidence": {
      "changed_candidates": []
    },
    "reason": {
      "changed_candidates": [
        {
          "candidate_id": "place_1",
          "axes": ["atmosphere"],
          "catalog_reference_added": true
        }
      ]
    },
    "unknown": {
      "reduced_candidates": [],
      "unchanged": true,
      "note": "catalog does not resolve unknowns"
    },
    "disqualified": {
      "changed_candidates": []
    }
  }
}
```

### B. multi-domain ablation result
既存の `cross_domain_summary` に加え、`cross_domain_review_summary` を追加する。

想定形:

```json
{
  "runs": [...],
  "cross_domain_summary": { ... },
  "cross_domain_review_summary": {
    "ranking_changed_domains": [],
    "reason_changed_domains": ["restaurant", "clinic"],
    "score_changed_domains": ["restaurant", "clinic"],
    "confidence_changed_domains": [],
    "unknown_reduced_domains": [],
    "disqualified_changed_domains": [],
    "interpretation_notes": [
      "ranking unchanged is normal",
      "reason changes are still meaningful",
      "catalog should not reduce unknown by itself"
    ]
  }
}
```

---

## 計算ルール

### 1. ranking
- `with_catalog.ranking` と `without_catalog.ranking` の candidate order を比較
- 順位変化があれば `changed=true`
- 順位変化がなければ `changed=false`

### 2. score
- candidate 単位で `total_score` の差分を計算
- 差分が 0 でない candidate のみ `changed_candidates` に列挙
- delta は `with - without`

### 3. confidence
- candidate 単位で `confidence` の差分を計算
- score と同様に `with - without`
- 存在しない場合は変化なし扱い

### 4. reason
- 既存 `diff_summary.reason_changes` をそのまま利用してよい
- 追加で、reason 内に `catalog:` などの catalog 参照が増えたかを簡易判定してもよい
- ただし判定に失敗しても本質ではないため、catalog 参照検出は best effort でよい

### 5. unknown
- `unknown_changes` を基に reduced / unchanged を判定
- reduced が空なら `unchanged=true`
- note には `catalog does not resolve unknowns` を固定文で入れてよい

### 6. disqualified
- candidate ごとに `disqualified` の真偽が変わったか比較
- 変わった candidate のみ列挙

---

## CLI 出力改善
`run_solution_catalog_live_ablation.py` の標準出力は、JSON 全体とは別に、人が読みやすい要約を先に表示する。

想定出力:

```text
=== Live Ablation Review Summary ===
Query: 恵比寿で静かに話せるイタリアン。予算は3000円以内
Model: gemini-2.5-flash

Ranking:
- unchanged

Score changes:
- place_1: +0.03
- place_3: -0.02

Confidence changes:
- none

Reason changes:
- place_1: atmosphere reason strengthened by catalog reference
- place_3: location limitation reason changed

Unknown:
- unchanged

Disqualified:
- unchanged
```

要件:
- stdout で人間向け summary を表示してよい
- `--out` の JSON 保存は従来どおり行う
- 既存利用を壊さないよう、JSON 保存内容は後方互換を維持する

---

## 実装ステップ

### Step 1. review summary builder を追加
追加候補:
- `src.experiments.review_summary.py`
または
- `src.experiments.catalog_ablation` 内 helper

責務:
- single-domain 結果から `review_summary` を構築
- multi-domain 結果から `cross_domain_review_summary` を構築

方針:
- diff 計算ロジックそのものとは分離する
- review 用の派生要約レイヤーとして実装する

### Step 2. single-domain live script に組み込む
- `diff_summary` の後に `review_summary` を追加
- CLI summary を表示
- `--out` の JSON にも保存

### Step 3. multi-domain 側にも同様の review summary を追加
- `cross_domain_summary` の上に review 用 summary を追加
- 既存 summary は残す

### Step 4. テスト追加
最低限追加するテスト:
- review_summary が生成される
- ranking unchanged が明示される
- unknown unchanged が明示される
- score delta の符号が正しい
- disqualified change が正しく検出される
- multi-domain review summary が両 domain を正しく集約する

---

## テスト方針

### 新規テスト候補
- `tests/test_live_ablation_review_summary.py`
- あるいは既存 `tests/test_live_ablation_script.py` に追加
- multi-domain は `tests/test_multi_domain_catalog_ablation.py` に追加でもよい

### 必須検証項目
1. `review_summary` キーの存在
2. ranking unchanged の場合に `changed=false`
3. reason 変化候補が `diff_summary.reason_changes` と整合
4. unknown reduction がない場合に `unchanged=true`
5. confidence 変化がない場合に空配列
6. cross-domain review summary の domain 集約整合

---

## 非目標
今回やらないこと:
- prompt の全面改稿
- score 計算式の変更
- new domain 追加
- catalog on/off 実行方式の抽象化
- live 実験の自動反復実行
- statistical significance 判定

---

## 実装時の注意
- 既存 `diff_summary` を壊さない
- 既存 JSON consumer がある前提で、追記ベースで設計する
- mock の意味論を変えない
- live の揺れを考慮し、断定的 wording を避ける
- no overclaim を最優先する

---

## 完了条件
以下を満たせば完了。

- live ablation JSON に `review_summary` が追加される
- CLI 出力で主要差分が一目で読める
- unknown unchanged が明示される
- ranking unchanged の場合でもレビュー価値が残る
- multi-domain 側でも domain ごとの差分が素早く読める
- 既存テストを壊さず、新規テストが追加される
