# Google Places Adapter 設計書

## 1. Google Places を使う理由
- restaurant 検索で最も広いカバレッジ (日本国内含む)
- 住所、ジャンル、価格帯、評価、営業時間が構造化データで取れる
- location bias による地理的絞り込みが API レベルで可能

## 2. 使用 API / Endpoint

### Search: Text Search (New)
- **Endpoint**: `POST https://places.googleapis.com/v1/places:searchText`
- **用途**: query understanding の出力からテキストクエリを構築し候補を取得
- **Field mask**: `places.id,places.displayName,places.formattedAddress,places.primaryType,places.priceLevel,places.rating`

### Retrieve: Place Details (New)
- **Endpoint**: `GET https://places.googleapis.com/v1/places/{place_id}`
- **用途**: search で得た place_id から詳細情報を取得
- **Field mask**: `displayName,formattedAddress,primaryType,types,regularOpeningHours,priceLevel,rating,userRatingCount,editorialSummary,websiteUri,googleMapsUri`

## 3. Search / Retrieve の責務分割

| ステージ | 責務 | 取得する情報 |
|---|---|---|
| Search | 候補リストの取得 | place_id, 名前, 住所, ジャンル, 価格帯, 評価 (概要) |
| Retrieve | 個別候補の詳細取得 | 営業時間, 口コミ要約, Web サイト, Google Maps URL |

Search で十分な情報が取れる場合、Retrieve をスキップする最適化も将来的に可能。

## 4. Query Understanding → Google Request 対応表

| query understanding | Google Places での使い方 | API パラメータ |
|---|---|---|
| `genre` | textQuery に埋め込む (`"italian restaurant"`) | `textQuery` |
| `location` | textQuery に追加 + locationBias | `textQuery` + `locationBias.circle` |
| `max_price` | **API では直接 filter 不可**。後段 (normalize/evaluate) で処理 | — |
| `atmosphere` | **API では直接 filter 不可**。textQuery に含めるか、editorialSummary で判定 | `textQuery` (optional) |

### textQuery 構築例
```
conditions = {"genre": "italian", "location": "恵比寿"}
→ textQuery = "italian restaurant in 恵比寿"
```

### locationBias
```json
{
  "locationBias": {
    "circle": {
      "center": {"latitude": 35.6467, "longitude": 139.7100},
      "radius": 1000.0
    }
  }
}
```
location → 座標変換は Geocoding API または固定マッピングで対応。

## 5. Google Places レスポンス → normalize 対応表

| Google Places field | candidate field | 備考 |
|---|---|---|
| `places[].id` | `candidate_id` | `gp_` prefix を付与 |
| `displayName.text` | `title` | |
| `formattedAddress` | `description` (一部) | |
| `primaryType` | `structured_attributes.genre` | type → genre マッピングが必要 |
| nearest station | `structured_attributes.nearest_station` | **API から直接取得不可**。初期実装では未設定とする |
| `priceLevel` | `structured_attributes.price_min/max` | PRICE_LEVEL_* → 金額レンジのマッピング |
| `editorialSummary.text` | `structured_attributes.review_summary` | |
| `rating` | (evaluate 用参考値) | structured_attributes に追加可 |
| `userRatingCount` | (evaluate 用参考値) | |
| `googleMapsUri` | `source_metadata.google_maps_url` | |
| `id` | `source_metadata.place_id` | |
| — | `source_metadata.raw_source` | `"google_places"` 固定 |

### 不明項目
- `nearest_station`: Google Places から直接取得できないため、初期実装では未設定とする。必要なら将来的に駅データベースや Geocoding を用いた別処理で補う
- `atmosphere_tags`: editorialSummary が存在する場合はキーワード抽出を試みる。editorialSummary が無い場合は unknown として扱い、推測で埋めない

## 6. priceLevel マッピング

| Google priceLevel | 推定価格帯 | price_min | price_max |
|---|---|---|---|
| PRICE_LEVEL_FREE | 0 | 0 | 0 |
| PRICE_LEVEL_INEXPENSIVE | ~1000 | 500 | 1500 |
| PRICE_LEVEL_MODERATE | ~2000-3000 | 1500 | 3500 |
| PRICE_LEVEL_EXPENSIVE | ~5000-8000 | 3500 | 8000 |
| PRICE_LEVEL_VERY_EXPENSIVE | 10000+ | 8000 | None |
| 未設定 | unknown | None | None |

## 7. Diagnostics 設計

Google Places 使用時の search_diagnostics:

```json
{
  "strict_conditions": {"genre": "italian", "location": "恵比寿"},
  "fallback_enabled": true,
  "fallback_applied": false,
  "matched_stage": "text_search",
  "text_query": "italian restaurant in 恵比寿",
  "location_bias_applied": true,
  "api_result_count": 8,
  "final_result_count": 8,
  "api_error": null
}
```

## 8. エラーハンドリング設計

| エラー | search での扱い | retrieve での扱い | pipeline |
|---|---|---|---|
| API キー未設定 | 即座に例外 | 即座に例外 | stage 2/3 で中断、エラーログ |
| Timeout | `api_error: "timeout"` を diagnostics に記録、空結果 | 該当候補をスキップ | 取得できた候補のみで続行 |
| Rate limit (429) | リトライ 1回、失敗なら空結果 | リトライ 1回、失敗ならスキップ | 取得できた候補のみで続行 |
| Zero results | 正常動作 (fallback へ) | N/A | fallback chain で対応 |
| Partial fields | 取れたフィールドのみ使用 | 取れたフィールドのみ返す | normalize で unknown 扱い |
| Details fetch failure | N/A | 該当候補をスキップ | 他の候補で続行 |

## 9. コスト・制限

- 料金は変動するため、最新の [Google Cloud 価格表](https://cloud.google.com/maps-platform/pricing) を参照すること
- コスト構造: 1 pipeline 実行 = Text Search 1回 + Place Details N回 (N = 候補数)
- 候補数に比例してコストが増えるため、`max_results` で候補数を制限してコスト管理する
- Field mask で取得フィールドを絞ることで SKU を下げ、コスト削減が可能

## 10. 環境変数

| 変数名 | 必須 | デフォルト | 説明 |
|---|---|---|---|
| `GOOGLE_PLACES_API_KEY` | Yes | — | Places API キー |
| `GOOGLE_PLACES_TIMEOUT_SECONDS` | No | `10` | API タイムアウト |
| `GOOGLE_PLACES_MAX_RESULTS` | No | `10` | 最大候補数 |
| `GOOGLE_PLACES_USE_NEW_API` | No | `true` | New API 使用フラグ |

## 11. 今回未実装のもの
- 実際の HTTP 通信
- Geocoding (location → 座標変換)
- primaryType → genre マッピングの完全版
- nearest_station 推定ロジック
- リトライ / rate limit ハンドリング
- Place Photos 取得
