# Opus 実装指示書: Google Places Place Details 最小実装

この指示書に従って、`GooglePlacesRetriever` に **Place Details の最小実装** を追加してください。

## 目的
現状の Google Places 連携は Search と locationBias まで入っていますが、Retrieve は未実装です。
そのため候補の詳細情報が薄く、normalizer と評価器に渡せる情報が限定されています。

今回は **Place Details の最小実装** を入れて、Google Places の候補について最低限の詳細取得ができるようにしてください。

対象:
- `GooglePlacesRetriever.retrieve_place()` を実装する
- Google Places Place Details API (New) を呼ぶ
- 必要フィールドだけ field mask で取得する
- 返り値を既存 `PlaceRetriever` interface 形式に合わせる
- テストを追加する

非対象:
- nearest_station 推定
- review の高度要約
- atmosphere の高度推定
- fallback の多段実API呼び出し
- pipeline 全体の完全 Google 化

---

## 背景
現状の Google Places 連携:
- `GooglePlacesSearcher` は Text Search API まで実装済み
- `locationBias` 最小実装済み
- `GooglePlacesRetriever` はまだ `NotImplementedError`

この状態だと、Search は実データだが Retrieve は未実装のため、
Google 検索結果をそのまま既存 pipeline に深く流し込みにくいです。

そこでまず、Place Details を最小実装して
- URL
- 営業時間
- editorialSummary
- rating系
- types
などを取れるようにします。

---

## 今回の対象ファイル
主な対象:
- `src/adapters/places/google_places.py`
- 必要なら `src/adapters/places/config.py`
- `tests/test_google_places.py`
- 必要なら `README.md`

---

## 1. 実装対象
### 1-1. `GooglePlacesRetriever.retrieve_place()` を実装
想定 endpoint:
- `GET https://places.googleapis.com/v1/places/{place_id}`

最低限使う想定 field mask:
- `id`
- `displayName`
- `formattedAddress`
- `primaryType`
- `types`
- `priceLevel`
- `rating`
- `userRatingCount`
- `regularOpeningHours`
- `editorialSummary`
- `websiteUri`
- `googleMapsUri`

必要なら field mask 文字列は定数にしてください。

### 1-2. `source` を確認する
`retrieve_place(source, source_id)` の `source` が `google_places` 以外なら、
明示的エラーにして構いません。

例:
- `ValueError("GooglePlacesRetriever only supports source='google_places'")`

---

## 2. 返り値仕様
既存 interface に合わせて、次の形で返してください。

```json
{
  "source": "google_places",
  "source_id": "ChIJ...",
  "raw_record": {
    "name": "Trattoria Test",
    "address": "東京都渋谷区恵比寿...",
    "category": "italian_restaurant",
    "types": ["italian_restaurant", "restaurant", "food"],
    "price_level": "PRICE_LEVEL_MODERATE",
    "rating": 4.2,
    "user_rating_count": 128,
    "opening_hours_text": "Mon-Sun 11:30-22:00",
    "editorial_summary": "落ち着いた雰囲気のイタリアン",
    "website_url": "https://...",
    "maps_url": "https://maps.google.com/..."
  }
}
```

### 注意
- 不明な項目は推測で埋めない
- 欠損項目は未設定または `None` でよい
- `opening_hours_text` は最小実装では簡易文字列化でよい

---

## 3. opening hours の扱い
`regularOpeningHours` は構造がやや複雑なので、今回は最小実装でよいです。

推奨:
- `weekdayDescriptions` があれば、それを `" / "` で連結して `opening_hours_text` にする
- なければ未設定でよい

例:
```python
"Mon: 11:30-22:00 / Tue: 11:30-22:00 / ..."
```

---

## 4. 補助関数
必要なら以下のような補助関数を追加してください。

推奨例:
- `_extract_opening_hours_text(place: dict) -> str | None`
- `_place_details_to_raw_record(place: dict) -> dict`

責務を分け、テストしやすくしてください。

---

## 5. HTTP 実装方針
### 要件
- API キーは `GooglePlacesConfig` から取得
- timeout を使う
- field mask をヘッダで指定する
- `GET /v1/places/{place_id}` を使う
- エラー時は明示的例外または interface に沿った最小限の返り値にする

### 方針
今回は retriever なので、searcher のように diagnostics を無理に持たなくてもよいです。
ただし、最低限ログは入れてよいです。

### 例外
- API キー未設定 → `ValueError`
- timeout → `httpx.TimeoutException` をそのまま上げるか、分かる例外に包む
- 非200 → `httpx.HTTPStatusError` をそのまま上げるか、分かる例外に包む

今回は無理に吸収しなくてよいです。まず実装を明確にしてください。

---

## 6. normalizer との接続
今回は retriever 単体実装が主目的ですが、raw_record のキー名は既存 normalizer と極力合わせてください。

特に次は揃えたほうがよいです。
- `name`
- `address`
- `category`
- `price_level`
- `rating`
- `opening_hours_text`
- `editorial_summary`
- `website_url`
- `maps_url`

必要なら normalizer 側に軽微な対応を入れてよいですが、
今回は **retriever 単体の完成を優先**してください。

---

## 7. テスト要求
最低限、以下を追加してください。

### A. mocked Place Details response の unit test
- モックした API 応答から `raw_record` が正しく組まれること

### B. opening hours 文字列化
- `weekdayDescriptions` がある場合に `opening_hours_text` が作られること
- 無い場合に落ちないこと

### C. source の検証
- `source != google_places` なら期待通りに失敗すること

### D. API キー未設定
- `ValueError` になること

### E. HTTP エラー系
- timeout
- 非200

### F. 既存動作を壊さないこと
- `GooglePlacesSearcher` のテストは維持
- mock adapter のテストは維持
- 全体テストが通る

重要:
- 実際の Google API を叩くテストは不要
- すべて mocked response で deterministic にする

---

## 8. README 更新
必要なら以下を追記してください。
- Google Places Retrieve (Place Details) が最小実装されたこと
- Search と Retrieve の両方があること
- まだ atmosphere 推定や nearest_station は未実装であること

---

## 9. 実装上の注意
- 不明は推測で埋めない
- API field を勝手に意味変換しすぎない
- `editorialSummary` はそのまま使う
- `types` は raw のまま保持してよい
- opening hours は簡易整形で十分
- 今回は pipeline 全体の Google end-to-end 完成を目指さない

---

## 10. 成功条件
- `GooglePlacesRetriever.retrieve_place()` が実装される
- Place Details API の mocked test が通る
- raw_record に最低限の詳細項目が入る
- 不明項目は推測で埋めない
- 既存検索・評価系を壊さない

---

## 11. 今回やらないこと
- nearest_station 推定
- review 要約の LLM 化
- atmosphere の意味抽出強化
- fallback 多段実API呼び出し
- 広告主側カタログAPI
- CV/ROAS 計測

---

## 最後に出してほしいもの
1. 変更ファイル一覧
2. field mask の一覧
3. raw_record の例
4. 追加テスト内容
5. まだ未実装の部分
