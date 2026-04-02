# Google Normalizer 変換規約

## Direct mapping (直接転写)

| raw field | normalized field | 備考 |
|---|---|---|
| `name` | `title` | |
| `review_summary` | `structured_attributes.review_summary` | mock path |
| `editorial_summary` | `structured_attributes.review_summary` | Google path |
| `nearest_station` | `structured_attributes.nearest_station` | mock path のみ |
| `rating` | `structured_attributes.rating` | |
| `user_rating_count` | `structured_attributes.user_rating_count` | |
| `opening_hours_text` | `structured_attributes.opening_hours` | |
| `website_url` | `source_metadata.website_url` | |
| `maps_url` | `source_metadata.google_maps_url` | |

## Approximate mapping (近似変換)

| raw field | normalized field | 変換方法 |
|---|---|---|
| `price_text` | `price_min`, `price_max` | 正規表現で数値抽出 |
| `price_level` | `price_min`, `price_max` | enum → 概算レンジ (厳密価格ではない) |
| `category` | `genre` | 日本語ジャンル名マッピング or primaryType の軽い正規化 |

## Lexical inference (語彙ベース推定)

| raw field | normalized field | 条件 |
|---|---|---|
| `atmosphere_text` | `atmosphere_tags` | 明示語 (静か, 落ち着, 隠れ家 等) ヒット時のみ |
| `editorial_summary` | `atmosphere_tags` | 同上 |

語彙がなければ `atmosphere_tags` は設定しない。

## Unknown / not inferred (推測しない)

| 項目 | 理由 |
|---|---|
| `nearest_station` | Google Places から直接取得不可。住所からの推測はしない |
| `atmosphere_tags` (語彙なし) | 明示語がなければ設定しない |
| 未知の `primaryType` | 過剰変換せず、`_restaurant` 除去 + `_` → 空白の軽加工のみ |
| 未知の `priceLevel` | `(None, None)` を返す |

## Source metadata 追跡フィールド

| field | 内容 |
|---|---|
| `raw_source` | adapter 名 (`place_search` / `google_places`) |
| `place_category_raw` | raw の category / primaryType そのまま |
| `price_level_raw` | Google の priceLevel enum そのまま |
| `price_text_raw` | mock の price_text そのまま |
| `editorial_summary_raw` | editorial_summary そのまま |
| `website_url` | Web サイト URL |
| `google_maps_url` | Google Maps URL |
