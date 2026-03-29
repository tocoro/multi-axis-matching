# Opus 実装指示書: Restaurant 候補収集パイプライン

この指示書に従って、restaurant 用の候補収集パイプラインを段階的に実装してください。

## 目的
既存の `evaluate()` は「候補が与えられている前提の評価器」です。
ここに restaurant 用の候補収集パイプラインを追加し、最終的に

- query understanding
- search
- retrieve
- normalize
- evaluate

の流れで動くようにしてください。

今回はまず restaurant のみ対象にします。

---

## 今回のスコープ
実装対象:
1. query understanding
2. mock search
3. mock retrieve
4. normalize
5. 既存 evaluate との接続
6. mock ベースの end-to-end テスト

今回の非対象:
- 実際の Google Maps API 接続
- 実際の Web 検索 API 接続
- ベクトル DB 接続
- clinic / legal / product への展開

---

## 実装したいパイプライン

```text
user query
  ↓
query understanding
  ↓
mock search
  ↓
mock retrieve
  ↓
normalize
  ↓
evaluate
```

---

## 追加してほしいモジュール

```text
/src
  /pipeline
    restaurant_pipeline.py
  /services
    infer_search_conditions.py
  /searchers
    place_searcher.py
  /retrievers
    place_retriever.py
  /normalizers
    restaurant_normalizer.py
```

必要なら `__init__.py` も追加してください。

---

## 1. query understanding
### 目的
ユーザーの自然文クエリから、restaurant 候補収集に必要な検索条件を抽出する。

### 抽出対象
- location
- genre
- max_price
- atmosphere

### 入力例
```json
{
  "query": "恵比寿で静かに話せるイタリアン。予算は3000円以内"
}
```

### 出力例
```json
{
  "location": "恵比寿",
  "genre": "italian",
  "max_price": 3000,
  "atmosphere": "quiet"
}
```

### 実装要求
- まずは LLM ベースでも、簡易ルールベースでもよい
- ただし restaurant 用に最低限上記4項目を返せるようにする
- 不明な項目は推測で埋めない

---

## 2. mock search
### 目的
検索条件から候補サマリを返す。

### 入力
検索条件オブジェクト

### 出力例
```json
[
  {
    "source": "place_search",
    "source_id": "place_1",
    "title": "Trattoria A",
    "snippet": "静かな雰囲気のイタリアン"
  },
  {
    "source": "place_search",
    "source_id": "place_2",
    "title": "Bar B",
    "snippet": "賑やかでカジュアル"
  }
]
```

### 実装要求
- 最初は完全 mock でよい
- location / genre / budget に応じて固定候補セットを返してよい
- 少なくとも 2〜3 件返す

---

## 3. mock retrieve
### 目的
search で得た source_id に対して、詳細情報を返す。

### 出力例
```json
{
  "source": "place_search",
  "source_id": "place_1",
  "raw_record": {
    "name": "Trattoria A",
    "address": "東京都渋谷区...",
    "nearest_station": "恵比寿",
    "price_text": "￥2,000〜￥3,000",
    "category": "イタリアン",
    "atmosphere_text": "静かで落ち着いた雰囲気",
    "review_summary": "会話しやすいという評価が多い"
  }
}
```

### 実装要求
- source_id ごとに固定の raw_record を返してよい
- 不明な情報がある候補も混ぜる
- あとで normalize で unknown になるケースを含める

---

## 4. normalize
### 目的
source ごとの raw_record を、既存 evaluate() に渡せる candidate 形式に変換する。

### 出力目標
```json
{
  "candidate_id": "place_1",
  "title": "Trattoria A",
  "description": "恵比寿駅徒歩5分の落ち着いたイタリアン。平均予算2500円。",
  "structured_attributes": {
    "domain": "restaurant",
    "genre": "italian",
    "nearest_station": "恵比寿",
    "price_min": 2000,
    "price_max": 3000,
    "atmosphere_tags": ["quiet", "calm"],
    "review_summary": "会話しやすいという評価が多い",
    "source": "place_search"
  },
  "source_metadata": {
    "raw_source": "place_search"
  }
}
```

### 実装要求
- 不明な情報は埋めない
- `description` は自然文でまとめる
- `structured_attributes` をできるだけ埋める
- `source_metadata` を残す
- restaurant 以外の汎用化は不要

---

## 5. pipeline orchestrator
### 目的
全段をつないで、最終的に既存の `evaluate()` に渡す。

### 追加ファイル
- `src/pipeline/restaurant_pipeline.py`

### 入力
```json
{
  "request_id": "restaurant-pipeline-1",
  "user_query": "恵比寿で静かに話せるイタリアン。予算は3000円以内"
}
```

### 出力
既存 `evaluate()` の response schema に準拠した JSON。

### 実装要求
- query understanding
- search
- retrieve
- normalize
- evaluate
を順につなぐ
- intermediate data を必要に応じてログに出す
- 例外時にどの段階で失敗したか分かるようにする

---

## 6. テスト
追加してほしいテスト:

### A. query understanding
- location, genre, budget, atmosphere が抽出される

### B. normalize
- 価格文字列から price_min / price_max が取れる
- ジャンル正規化が行われる
- 欠損時は unknown 扱い前提で属性未設定になる

### C. pipeline e2e
- query → search → retrieve → normalize → evaluate が通る
- response schema を満たす
- ranking が返る
- 少なくとも1件は disqualified=false
- 条件に合う候補が条件不一致候補より上位

### D. 情報欠落ケース
- location 不明や price 不明の候補があると missing_information に反映されること

---

## 7. 追加してよいファイル
例:
```text
examples/restaurant_pipeline_input.json
examples/restaurant_pipeline_expected.json
tests/test_restaurant_pipeline.py
scripts/run_restaurant_pipeline.py
```

---

## 8. README 更新
README には最低限以下を追記してください。

- restaurant pipeline の概要
- 実行方法
- まだ mock 実装であること
- 実 API 連携は未実装であること

---

## 9. 実装方針
- 既存 evaluator の責務は壊さない
- 候補収集は evaluator の外側に追加する
- 今回は restaurant だけでよい
- 最初は mock でよい
- 実 API を勝手に追加しない
- 不明は不明として残す

---

## 10. 最後に出してほしいもの
作業完了時に以下をまとめてください。

1. 追加・変更したファイル一覧
2. 実行コマンド
3. mock pipeline の出力例
4. テスト結果
5. 未実装のもの

---

## 成功条件
- restaurant query から mock 候補収集が通る
- normalize 後に既存 evaluate() を呼べる
- e2e テストが通る
- 段階ごとの責務が分離されている
