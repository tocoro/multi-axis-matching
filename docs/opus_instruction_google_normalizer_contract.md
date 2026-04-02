# Opus 実装指示書: Google normalizer 変換規約の整理

この指示書に従って、Google Places 系の `raw_record` を `normalized candidate` に落とす際の**変換規約を整理・明文化**してください。

## 目的
現状の pipeline は
- Google Places search
- Google Places retrieve
- normalize
- evaluate

まで一応通っています。

ただし、いまは normalizer が評価結果に強く効いており、特に以下の変換が暗黙に効いています。

- `price_level -> price_min / price_max`
- `primaryType -> genre`
- `editorial_summary -> atmosphere_tags / review_summary`
- `website_url / maps_url -> source_metadata`

この段階では、機能追加よりも先に、
**どこまでを構造化し、どこからを unknown にするか**
を固定したほうが安全です。

---

## 今回の目的
次の3点を行ってください。

1. Google raw_record → normalized candidate の変換規約をコード上・テスト上で明確化する
2. 推測で埋めてよい範囲と、unknown にすべき範囲を分ける
3. source data と normalized data の関係を追跡しやすくする

---

## 今回の対象ファイル
主な対象:
- `src/normalizers/restaurant_normalizer.py`
- `tests/test_restaurant_pipeline.py`
- 必要なら `tests/test_google_places.py`
- 必要なら `README.md`
- 必要なら `docs/` に変換規約メモを追加

---

## 1. 変換規約を明文化する
少なくともコードコメント、docstring、または docs で、以下を明記してください。

### 明記したい項目
- 直接マッピングする項目
- 軽い構造変換をする項目
- 推測を避ける項目
- unknown のまま残す項目

推奨表現:
- `name -> title` は直接マッピング
- `price_level -> (price_min, price_max)` は近似変換
- `editorial_summary -> review_summary` は直接転写
- `editorial_summary -> atmosphere_tags` は軽い語彙ベース推定
- `nearest_station` は未設定
- `atmosphere_tags` は語彙ヒットがなければ未設定

---

## 2. source-aware mapping を整理
normalizer 内で、Google path と mock path の違いを見通しよくしてください。

推奨:
- `_resolve_price(raw)` のように、source ごとの差を吸収する補助関数を使う
- 必要なら `_extract_review_summary(raw)`、`_extract_source_metadata(raw)` のような関数に分ける

目的は、ロジックを複雑化することではなく、
**どの変換がどこで行われているか見えるようにすること**です。

---

## 3. unknown の扱いを保守的にする
以下は、初期実装では保守的に扱ってください。

### A. nearest_station
- Google Places から直接取れない
- 推測しない
- 未設定のままにする

### B. atmosphere_tags
- `editorial_summary` や `atmosphere_text` に明示語があるときのみ付与
- 明示語がないなら未設定
- 無理に quiet / stylish を推定しない

### C. genre
- `primaryType` から軽い正規化はしてよい
- ただし意味変換を広げすぎない
- 不明な type はそのまま低加工で残すか、最低限の整形にとどめる

### D. price
- `priceLevel` は近似レンジでよい
- ただし厳密価格ではないことが分かるようにコメントを残す

---

## 4. source_metadata をもう少し追跡可能にする
現在の `source_metadata` は有用ですが、もう少し追えると良いです。

最低限、次のどれかを追加してください。

推奨候補:
- `source_metadata.place_category_raw`
- `source_metadata.price_level_raw`
- `source_metadata.editorial_summary_raw`
- `source_metadata.address_raw`

全部でなくてよいですが、
**normalized candidate が何を元に作られたか**が少し見えるようにしてください。

ただし raw 全文ダンプのような冗長化は不要です。

---

## 5. テスト要求
最低限、以下を追加または更新してください。

### A. price_level の近似変換
- `PRICE_LEVEL_MODERATE -> (1500, 3500)` のような規約が固定されること
- 未知の enum は `(None, None)` になること

### B. editorial_summary の扱い
- review_summary へは転写される
- atmosphere_tags は語彙ヒット時のみ付く
- 語彙がなければ atmosphere_tags は未設定または空

### C. nearest_station を推測しないこと
- Google raw_record に駅情報が無い場合、normalized candidate に nearest_station 相当を作らないこと

### D. genre 正規化
- `italian_restaurant -> italian`
- ただし未知 type の過剰変換をしないこと

### E. source_metadata
- raw 由来のどの情報が残るか、テストで固定すること

### F. mock path を壊さないこと
- 既存 mock テストが通ること

---

## 6. docs 追加は任意
必要なら `docs/` に短いメモを追加してもよいです。

推奨タイトル例:
- `docs/google_normalizer_contract.md`

書くなら以下だけで十分です。
- direct mapping
- approximate mapping
- lexical inference
- unknown / not inferred

---

## 7. 実装上の注意
- 機能拡張より規約固定を優先
- 推測を増やしすぎない
- Google path だけ特別扱いしすぎて mock path を壊さない
- evaluate 側の責務は変えない
- atmosphere は軽い語彙ベースまでで止める

---

## 8. 成功条件
- 変換規約がコードまたは docs で追える
- unknown の扱いが保守的になる
- source_metadata から元情報を少し辿れる
- テストで規約が固定される
- mock path を壊さない

---

## 9. 今回やらないこと
- LLM による review 意味抽出強化
- nearest_station 推定
- price の高精度推定
- Google fallback 多段実API
- 広告主カタログ
- CV/ROAS 計測

---

## 最後に出してほしいもの
1. 変更ファイル一覧
2. direct / approximate / lexical / unknown の分類説明
3. source_metadata に残した項目
4. 追加・更新したテスト
5. まだ未実装の部分
