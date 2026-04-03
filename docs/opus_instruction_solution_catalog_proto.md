# Opus 実装指示書: Solution Catalog Prototype

この指示書に従って、multi-axis-matching における**候補側の意味記述**の原型として、Solution Catalog の最小プロトタイプを追加してください。

## 背景
現状の system は、
- user problem の構造化
- candidate collection
- normalization
- multi-axis evaluation

まで進んでいます。

しかし現状の候補表現は、まだ主に
- 店舗属性
- Google Places の raw data
- 軽い正規化

に依存しています。

そのため、通常の parametric search との差は主に評価関数側にあり、
**候補側が「どんな悩みをどの条件で解決できるか」を表現する層**が未整備です。

このギャップを埋める最初の一歩として、今回は Solution Catalog の最小プロトタイプを作ってください。

---

## 目的
次の3点を実現してください。

1. 候補側が「解決できる問題」を持てる構造を定義する
2. その構造を restaurant の mock / sample データで試せるようにする
3. 現行 pipeline を壊さず、将来の candidate-side semantics 層の土台にする

今回は **本格実装ではなく prototype** です。

---

## 今回の位置づけ
これは広告主カタログや provider-side catalog の前段です。

まだやらないこと:
- UI 完成
- DB 永続化
- 自動生成
- 複数ドメイン展開
- marketplace / pricing / conversion measurement

今回は、**候補側意味記述のスキーマと最小サンプル** を repo に置くことが目的です。

---

## 今回の対象ファイル
主な対象:
- `docs/` に設計メモ
- `schemas/` または `src/contracts/` にスキーマ定義
- `examples/` または `data/` に restaurant サンプル catalog
- 必要なら `tests/` に最小テスト
- 必要なら `README.md`

ファイル名は repo 構成に合わせて調整してよいです。

推奨例:
- `docs/solution_catalog_proto.md`
- `schemas/solution_catalog.schema.json`
- `examples/restaurant_solution_catalog.json`
- `tests/test_solution_catalog_schema.py`

---

## 1. Solution Catalog の最小スキーマを定義
少なくとも以下の概念を持つ構造にしてください。

### 必須概念
- `candidate_id`
- `domain`
- `solution_claims`
- `hard_limitations`
- `evidence`
- `metadata`

### イメージ
```json
{
  "candidate_id": "place_1",
  "domain": "restaurant",
  "solution_claims": [
    {
      "problem_pattern": "quiet_conversation",
      "strength": "strong",
      "conditions": ["weekday_evening", "small_group"],
      "reason": "静かで落ち着いた雰囲気、会話向き"
    },
    {
      "problem_pattern": "date_night",
      "strength": "medium",
      "conditions": ["dinner"],
      "reason": "雰囲気がよく、価格帯も中程度"
    }
  ],
  "hard_limitations": [
    {
      "problem_pattern": "large_group_party",
      "reason": "席数と雰囲気の面で不向き"
    }
  ],
  "evidence": {
    "source_type": "mock",
    "source_fields": ["atmosphere_text", "review_summary", "price_text"]
  },
  "metadata": {
    "version": "proto-v1"
  }
}
```

---

## 2. スキーマ設計の方針
以下を守ってください。

### A. claim は「できること」を書く
例:
- quiet_conversation
- casual_lunch
- budget_dinner
- quick_meal

### B. limitation は「向かないこと」を書く
例:
- large_group_party
- luxury_dining
- late_night

### C. evidence を分ける
claim 自体と、その根拠データを分けてください。

### D. 推測を増やしすぎない
いきなり高度な意味推定をしないでください。
prototype なので、**手書きサンプルでよい**です。

---

## 3. restaurant サンプルを作る
少なくとも 2〜3 件、restaurant 用の solution catalog サンプルを追加してください。

推奨:
- 既存 mock restaurant 候補に対応するもの
- quiet / lively / budget / cuisine などの差が出るもの

目的は、
**候補側が「単なる店舗属性」ではなく「どんな問題解決に向くか」を持つ**
状態を可視化することです。

---

## 4. 既存 pipeline とは疎結合にする
今回は pipeline に無理に組み込まなくてよいです。

やってよいこと:
- 将来 integration しやすいよう、candidate_id を合わせる
- docs に「どこで使う想定か」を書く

やらなくてよいこと:
- evaluate に直接組み込む
- searcher / retriever を書き換える

今回は、**新しい層を repo に置くこと**が目的です。

---

## 5. docs を追加
少なくとも docs に以下を説明してください。

### 必須項目
1. なぜ Solution Catalog が必要か
2. 通常の店舗属性と何が違うか
3. `solution_claims` / `hard_limitations` / `evidence` の意味
4. 今回は手書きプロトタイプであること
5. 将来的には provider-side / advertiser-side catalog に拡張する想定であること

---

## 6. テスト要求
最低限、以下のどれかを追加してください。

### A. schema validation test
- サンプル JSON がスキーマを満たす

### B. field presence test
- 必須項目が存在する
- `solution_claims` が list である
- `hard_limitations` が list である

### C. example consistency test
- `candidate_id` が既存 mock 候補の ID と一致する

本格的な意味評価テストは不要です。

---

## 7. 実装上の注意
- 今回は prototype に留める
- 自動生成を急がない
- semantics を書きすぎない
- evidence を切り離す
- 既存 pipeline を壊さない
- restaurant 限定でよい

---

## 8. 成功条件
- Solution Catalog の最小スキーマが repo に追加される
- restaurant の sample catalog が 2〜3 件以上ある
- docs で役割が説明される
- 最小限の schema / example テストがある
- 現行 pipeline を壊さない

---

## 9. 今回やらないこと
- evaluator との直接統合
- LLM による catalog 自動生成
- UI 編集機能
- provider portal
- cross-domain 拡張
- economic layer

---

## 最後に出してほしいもの
1. 追加したファイル一覧
2. Solution Catalog のスキーマ要約
3. サンプル候補ごとの claim / limitation の例
4. 追加したテスト
5. 将来どう pipeline に接続する想定か
