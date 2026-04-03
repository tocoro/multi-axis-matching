# Opus 実装指示書: Solution Catalog あり / なし比較実験

この指示書に従って、Solution Catalog を evaluator に渡した場合と渡さない場合で、評価結果がどう変わるかを比較する**ablation 実験**を追加してください。

## 背景
現状の repo では、次が整いました。
- Solution Catalog prototype
- evaluator への optional context 接続
- Solution Catalog 利用規約の prompt / docs / tests 固定

ここまで来たので、次は「契約が整った結果として、実際に何が変わるのか」を観測する段階です。

ただし今回は、catalog を score に直接変換する実装ではなく、
**catalog あり / なしでどのような差が出るかを比較する実験基盤**を作ることが目的です。

---

## 目的
次の4点を実現してください。

1. 同じ query / candidate で catalog あり / なしの評価を並べて比較できる
2. reason / confidence / unknown / ranking の差分を見られる
3. 既存 pipeline を壊さずに比較できる
4. docs または examples として結果の見方を残す

---

## スコープ
### 対象
- comparison helper / script / test fixture の追加
- catalog on/off を切り替えて同条件で評価する仕組み
- 差分サマリー出力
- 必要なら docs / example output の追加

### 非対象
- live LLM の統計評価
- score aggregation の変更
- UI の変更
- catalog 主導 scoring の導入
- cross-domain 比較

---

## 今回の対象ファイル
主な対象:
- `scripts/` または `src/experiments/` に比較用コード
- `tests/` に比較テスト
- 必要なら `examples/` に差分出力例
- 必要なら `docs/solution_catalog_usage_contract.md`
- 必要なら `README.md`

推奨例:
- `scripts/compare_solution_catalog_ablation.py`
- `tests/test_solution_catalog_ablation.py`
- `examples/solution_catalog_ablation_expected.json`

repo 構成に合わせて調整してよいです。

---

## 1. 比較の基本仕様
同じ query に対して、少なくとも次の2条件を比較できるようにしてください。

### Condition A
- Solution Catalog あり

### Condition B
- Solution Catalog なし

この2つについて、同じ mock candidates / same evaluator stub / same pipeline 条件で比較してください。

重要:
- まずは deterministic な mocked LLM でよい
- 実 LLM を必須にしない
- 比較構造そのものを作ることが目的

---

## 2. 比較したい項目
最低限、以下を比較対象にしてください。

### A. ranking order
- 順位が変わったか

### B. total_score
- 候補ごとの total score が変わったか

### C. confidence
- confidence が変わったか

### D. missing_information / unknown
- unknown が減ったか、変わらないか

### E. axis reasons
- reason が catalog を参照する形に変わったか

全部を数値で厳密比較しなくてもよいですが、
少なくとも出力構造として追えるようにしてください。

---

## 3. mocked evaluator の設計
今回は実 LLM の気分で結果が変わると比較しにくいので、
比較用テストでは **catalog の有無を見て挙動を変える mocked evaluator** を使ってよいです。

### 例
- catalog 無し:
  - atmosphere reason = "quiet keyword present"
  - confidence = 0.70
- catalog 有り:
  - atmosphere reason = "quiet keyword + solution catalog quiet_conversation"
  - confidence = 0.78

ただし、やりすぎないでください。

### 方針
- score を大きく変える必要はない
- まずは reason / confidence / unknown の変化を見せる
- ranking が変わらなくてもよい
- catalog による補助がどう現れるかを示せれば十分

---

## 4. 差分サマリーの出力
比較結果として、少なくとも次のようなサマリーを返す形にしてください。

```json
{
  "query": "恵比寿で静かに話せるイタリアン",
  "with_catalog": {...},
  "without_catalog": {...},
  "diff_summary": {
    "ranking_changed": false,
    "confidence_changes": {
      "place_1": {"before": 0.70, "after": 0.78}
    },
    "reason_changes": {
      "place_1": ["atmosphere"]
    },
    "unknown_changes": {
      "place_1": {"before": 1, "after": 1}
    }
  }
}
```

厳密にこの形でなくてもよいですが、
**人が差分を読める構造**にしてください。

---

## 5. 実験ケース
最低限、1〜2ケース用意してください。

推奨:

### Case 1
- quiet conversation 向きの店
- catalog に quiet_conversation claim あり
- reason / confidence に差が出やすい

### Case 2
- limitation が関係するケース
- 例: banquet 向きではない店
- catalog が conflict reason の補助になる

無理に多ケース化しなくてよいです。

---

## 6. docs / examples
必要なら docs か examples に短い説明を追加してください。

書きたいこと:
- この比較は実運用の品質保証ではなく、catalog の寄与を観測するためのもの
- ranking が変わらないことも普通にありうる
- reason や confidence の変化に注目する
- catalog は unknown を魔法のように解消しない

---

## 7. テスト要求
最低限、以下を追加してください。

### A. comparison output test
- with_catalog / without_catalog / diff_summary がある

### B. confidence or reason difference test
- catalog ありで reason または confidence が変化すること

### C. backward compatibility
- 通常 pipeline は壊さない

### D. no overclaim test
- catalog により unknown が不当に 0 にならない
- limitation が即 disqualify にならない

### E. deterministic
- mocked setup で比較結果が再現可能

---

## 8. 実装上の注意
- 今回は ablation 基盤作成に留める
- 実 LLM の統計評価をしない
- catalog の寄与を過大に演出しない
- ranking 不変でも失敗ではない
- reason / confidence の変化を優先して観測する

---

## 9. 成功条件
- catalog あり / なし比較が同条件で走る
- diff summary が得られる
- reason / confidence / unknown / ranking の差が追える
- テストで比較構造が固定される
- 既存 pipeline を壊さない

---

## 10. 今回やらないこと
- live LLM ベンチマーク
- catalog 自動生成
- score rewrite
- UI 比較画面
- CV/ROAS 計測

---

## 最後に出してほしいもの
1. 追加ファイル一覧
2. 比較の実行方法
3. diff summary の例
4. 追加したテスト
5. 観測できること / まだ観測できないこと
