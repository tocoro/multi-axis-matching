# Opus 実装指示書: Google Places Adapter 設計

この指示書に従って、restaurant 候補収集パイプラインに将来的に Google Places を接続するための具体設計を追加してください。

## 背景
現状の project は以下の段階まで進んでいます。
- evaluator 完成
- restaurant 用 mock pipeline 完成
- 条件ベース search + fallback 完成
- fallback diagnostics / strict mode 完成
- Place adapter interface 化に着手する段階

ここから先は、実 API 接続の前に、**Google Places を接続する場合の設計を先に固定**したいです。

今回は **設計文書とスタブ寄りの実装準備** が目的です。
本番の HTTP 接続や API キー必須の動作までは不要です。

---

## 目的
次の3点を明確にしてください。

1. Google Places を search / retrieve のどこにどう接続するか
2. Google Places のレスポンスを、現在の normalize / evaluate とどう接続するか
3. 実装時に必要な環境変数、フィールド、エラーハンドリング、制約を明文化すること

---

## 今回の対象
主な対象ファイル:
- `docs/` に新しい設計文書
- 必要なら `src/adapters/places/` 配下のスタブ
- 必要なら `README.md`

推奨追加例:
```text
src/
  adapters/
    places/
      google_places.py
      types.py
      config.py
```

ただし、今回は **実HTTP通信の完成までは不要** です。

---

## 1. 設計文書を追加
最低でも次を含む設計文書を `docs/` に追加してください。

### 必須セクション
1. Google Places を使う理由
2. どの API / endpoint を使う想定か
3. search と retrieve の責務分割
4. query understanding の出力をどう request に変換するか
5. Google Places のレスポンスから何を抽出するか
6. normalize へどう渡すか
7. 欠損や rate limit の扱い
8. diagnostics をどう残すか
9. コスト・制限・注意点
10. 今回未実装のもの

---

## 2. search / retrieve の想定接続
Google Places では概念的に以下の対応で考えてください。

### Search step
- Text Search / SearchText 系 API
- クエリ例: `italian restaurant in Ebisu`
- location bias の利用可否
- strict / fallback とどう接続するか

### Retrieve step
- Place Details 系 API
- 取得対象フィールドの明示
- 例:
  - displayName
  - formattedAddress
  - primaryType / types
  - regularOpeningHours
  - priceLevel
  - rating
  - userRatingCount
  - editorialSummary
  - websiteUri
  - googleMapsUri

ここでは、Google Places で**何が取れる前提にするか**を具体的に書いてください。

---

## 3. query understanding → Google request の対応表
現在の query understanding の出力は概ね以下です。
- location
- genre
- max_price
- atmosphere

これを Google Places 側でどう使うかを整理してください。

例:
- `genre` → textQuery に埋め込む
- `location` → textQuery + location bias
- `max_price` → 直接 hard filter できない場合は後段処理
- `atmosphere` → query 文に含めるか、review / summary 解釈に回す

ここは曖昧にせず、**どの項目が API の検索条件に使えるか / 使えないか** を分けて書いてください。

---

## 4. normalize 用の対応表
Google Places のレスポンスから、現在の candidate 構造にどう落とすかを表にしてください。

最低限、次の対応は明記してください。

- `candidate_id`
- `title`
- `description`
- `structured_attributes.genre`
- `structured_attributes.nearest_station` または `location_text`
- `structured_attributes.price_*`
- `structured_attributes.review_summary`
- `structured_attributes.source`
- `source_metadata.raw_source`
- `source_metadata.place_id`
- `source_metadata.google_maps_url`

不明なものは不明でよいですが、埋め方を推測しないでください。

---

## 5. config と環境変数の設計
今回は実装は不要ですが、少なくとも以下を想定してください。

例:
- `GOOGLE_PLACES_API_KEY`
- `GOOGLE_PLACES_USE_NEW_API=true|false`
- `GOOGLE_PLACES_TIMEOUT_SECONDS`
- `GOOGLE_PLACES_MAX_RESULTS`

必要なら config モジュールや dataclass のスタブを置いてよいです。

---

## 6. adapter スタブ
今回は本接続不要ですが、将来接続しやすいようにスタブを置いてよいです。

推奨:
- `GooglePlacesSearcher`
- `GooglePlacesRetriever`

仕様:
- constructor で config を受ける
- 現時点では `NotImplementedError` でもよい
- docstring に「どの endpoint / field を使う想定か」を書く

重要:
- テストを壊さないこと
- デフォルトは mock adapter のままにすること

---

## 7. diagnostics 設計
Google Places 接続時にも、現在の `search_diagnostics` の思想を維持してください。

最低限、残したい情報:
- strict / fallback の区別
- textQuery
- location bias の有無
- API result count
- final normalized candidate count
- API error / timeout の有無

これを docs に書いてください。

---

## 8. エラーハンドリング設計
次のケースを最低限設計してください。

- API キー未設定
- timeout
- rate limit
- zero results
- partial fields only
- details fetch failure

それぞれについて、
- search でどう返すか
- retrieve でどう返すか
- pipeline をどう継続 / 中断するか

を明記してください。

---

## 9. 今回やらないこと
今回は以下は不要です。
- 実際の Google Places HTTP 通信
- API キー必須のテスト
- 実レスポンスを用いた完成実装
- clinic / product への展開

---

## 10. README 更新
必要なら README に以下を追記してください。
- Google Places 接続は設計段階まで入ったこと
- 実接続はまだ未実装であること
- mock adapter が引き続きデフォルトであること

---

## 成功条件
- Google Places 接続の設計が docs に明文化される
- どの endpoint / field を使うかが具体化される
- normalize との接続方針が定まる
- config / adapter スタブの方向性が決まる
- 現行の mock テストは壊れない

---

## 最後に出してほしいもの
1. 追加した設計ファイル一覧
2. Google Places の search / retrieve の責務分割説明
3. normalize へのマッピング表の要約
4. 想定環境変数一覧
5. まだ未実装の実接続部分
