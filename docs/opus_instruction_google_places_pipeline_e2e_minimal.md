# Opus 実装指示書: Google Places pipeline 最小 end-to-end 接続

この指示書に従って、Google Places の Search + Retrieve を既存の restaurant pipeline に最後まで接続してください。

## 目的
現状は以下まで実装済みです。
- `GooglePlacesSearcher` 実装済み
- `locationBias` 最小実装済み
- `GooglePlacesRetriever` 実装済み
- mock pipeline は既存のまま安定している

しかし現時点では、Google Places の候補を

- search
- retrieve
- normalize
- evaluate

まで一応最後まで通す、という **最小 end-to-end 接続** がまだ弱いです。

今回は **Google Places を使った候補収集から評価までを最小構成で通す** ことを目的にしてください。

---

## スコープ
### 対象
- Google searcher で候補を取得
- 上位 N 件だけ Google retriever で詳細取得
- raw_record を既存 restaurant normalizer に渡す
- 既存 evaluate に流す
- response に candidate_sources が残る
- テストを追加する

### 非対象
- nearest_station 推定
- atmosphere の高度抽出
- review 要約の LLM 強化
- Google fallback の多段実API呼び出し
- Geocoding API
- 広告主カタログAPI
- コンバージョン計測

---

## 今回の対象ファイル
主な対象:
- `src/pipeline/restaurant_pipeline.py`
- 必要なら `src/normalizers/restaurant_normalizer.py`
- `tests/test_restaurant_pipeline.py`
- 必要なら `tests/test_google_places.py`
- 必要なら `README.md`

---

## 1. やること
### 1-1. pipeline で Google adapters を通す
`run_restaurant_pipeline()` において、`place_searcher` と `place_retriever` が Google adapters の場合でも、
最後まで pipeline を通るようにしてください。

想定フロー:
1. query understanding
2. `place_searcher.search_places()`
3. search results の上位 N 件を選ぶ
4. 各候補に対して `place_retriever.retrieve_place(source, source_id)`
5. `raw_record` を `normalize_restaurant()` に流す
6. candidate 配列を `evaluate()` に渡す

---

## 2. 上位 N 件だけ retrieve する
実 API 呼び出しコストと待ち時間を抑えるため、retrieve は検索結果すべてではなく **上位 N 件だけ** にしてください。

### 初期値の提案
- `max_retrieve = 3`

これを pipeline 内部の定数にしてもよいし、引数にしてもよいです。

### 注意
- 今回はまず deterministic test が優先なので、挙動を固定してください
- 後で最適化できるよう、変数名やコメントを残してください

---

## 3. 正規化の最小接続
Google Places Retrieve の `raw_record` は既存 normalizer と完全一致ではない部分があります。

必要なら **最小限だけ** normalizer を調整してください。

重点:
- `name`
- `address`
- `category`
- `price_level`
- `rating`
- `opening_hours_text`
- `editorial_summary`
- `website_url`
- `maps_url`

ただし、
- 推測で埋めない
- 既存 mock データの処理を壊さない

を優先してください。

---

## 4. candidate_sources を残す
最終 response に `candidate_sources` が残るようにしてください。

ここには少なくとも、評価対象になった候補について
- normalized candidate
- または source_id と raw_record

が追えることが望ましいです。

少なくとも、UI の Details から「何を元に評価したか」が追えるようにしてください。

---

## 5. Google pipeline の動作方針
今回は **最小E2E** なので、Google pipeline の挙動は次で十分です。

### 検索段階
- `GooglePlacesSearcher.search_places()` を使う

### 詳細取得段階
- 上位 N 件だけ `GooglePlacesRetriever.retrieve_place()` を使う

### 失敗時の扱い
- retrieve 失敗候補はスキップしてよい
- ただし全部失敗したら分かるようにする
- search_diagnostics は維持する
- 必要なら `pipeline_diagnostics` に retrieve failure count を追加してよい

今回は無理に完全成功を保証しなくてよいです。
まず、**最後まで流れる経路を作る**ことを優先してください。

---

## 6. テスト要求
最低限、以下を追加してください。

### A. mocked Google search + retrieve + pipeline E2E
- searcher を mocked response で動かす
- retriever も mocked response で動かす
- pipeline が最後まで response を返す

### B. ranking が返ること
- `ranking` があり、少なくとも1件返ること

### C. candidate_sources が残ること
- 最終 response に candidate_sources があること
- 候補の source data が追えること

### D. search_diagnostics が残ること
- Google search の diagnostics が response に残ること

### E. retrieve failure を吸収できること
- 1件の retrieve が失敗しても他候補で pipeline が動くこと
  または、現時点の仕様として明示的に失敗するならその仕様をテストで固定すること

### F. mock pipeline を壊さないこと
- 既存の mock tests はそのまま通ること

重要:
- 実際の Google API を叩くテストは不要
- mocked HTTP response で deterministic にする

---

## 7. 実装上の注意
- まずは restaurant ドメインだけ
- retrieve は上位 N 件だけ
- 不明は不明のまま
- evaluation ロジックはなるべく触らない
- Google adapters の失敗が mock path を壊さないようにする
- source データの可観測性を残す

---

## 8. README 更新
必要なら以下を追記してください。
- Google Places の Search + Retrieve を通した pipeline 実行が可能になったこと
- ただし最小実装であり、atmosphere / nearest_station などは未整備であること
- retrieve は上位 N 件のみであること

---

## 9. 成功条件
- Google search + retrieve + normalize + evaluate が最後まで通る
- mocked E2E テストが通る
- candidate_sources が response に残る
- search_diagnostics が残る
- mock path を壊さない

---

## 10. 今回やらないこと
- Google fallback 多段実API呼び出し
- atmosphere 高度抽出
- editorial summary の意味解析強化
- nearest_station 推定
- ROAS / CV 計測
- 課金モデル

---

## 最後に出してほしいもの
1. 変更ファイル一覧
2. Google pipeline の流れの説明
3. 上位 N 件 retrieve の仕様
4. 追加テスト内容
5. まだ未実装の部分
