# Opus 実装指示書: Google Places Search 最小実装

この指示書に従って、Google Places 接続の**最小実装**を追加してください。

## 目的
今回は Google Places の **Search のみ** を最小実装してください。

対象:
- `GooglePlacesSearcher` を実装する
- Text Search API を呼ぶ
- 返り値を既存の `PlaceSearcher` interface 形式に合わせる
- strict / fallback / diagnostics の思想を壊さない

非対象:
- `GooglePlacesRetriever` の実装
- nearest_station 推定
- atmosphere_tags の高度抽出
- Place Details 実通信
- geocoding の本実装

---

## 背景
現状は以下ができています。
- mock pipeline
- search filtering
- fallback diagnostics
- strict mode
- adapter interface
- Google Places 設計書

次は、Google Places を **search 段階だけ** 実接続して、
mock ではない候補取得ができる最小形を作ります。

---

## 今回の対象ファイル
主な対象:
- `src/adapters/places/google_places.py`
- 必要なら `src/adapters/places/config.py`
- `src/pipeline/restaurant_pipeline.py`
- `scripts/run_restaurant_pipeline.py`
- `tests/` に新しいテストまたは最小スタブテスト
- 必要なら `README.md`

---

## 1. 実装対象
### 1-1. `GooglePlacesSearcher.search_places()` を実装
対象 endpoint:
- `POST https://places.googleapis.com/v1/places:searchText`

最低限使う想定 field:
- `places.id`
- `places.displayName`
- `places.formattedAddress`
- `places.primaryType`
- `places.priceLevel`
- `places.rating`

### 1-2. `GooglePlacesRetriever` は未実装のままでよい
今回は `NotImplementedError` のままでよいです。

---

## 2. search の返り値仕様
既存 interface に合わせて次の形で返してください。

```json
{
  "results": [
    {
      "source": "google_places",
      "source_id": "place_id",
      "title": "店名",
      "snippet": "住所やジャンルを含む簡易説明"
    }
  ],
  "search_diagnostics": {
    "strict_conditions": {...},
    "fallback_enabled": true,
    "fallback_applied": false,
    "matched_stage": "text_search",
    "fallback_steps": [],
    "strict_result_count": 5,
    "final_result_count": 5,
    "text_query": "italian restaurant in 恵比寿",
    "location_bias_applied": false,
    "api_result_count": 5,
    "api_error": null
  }
}
```

---

## 3. query → Google textQuery
### 方針
現在の `conditions` から、まずは単純な `textQuery` を生成してください。

推奨例:
- genre + location → `"italian restaurant in 恵比寿"`
- genre only → `"italian restaurant"`
- location only → `"restaurant in 恵比寿"`
- atmosphere がある場合は末尾に追加してもよいが、必須ではない

### 注意
- `max_price` は Google API の直接 filter に使わない
- `atmosphere` は初期実装では query に入れなくてもよい
- location bias は今回は未実装でもよい。その場合 `location_bias_applied=false`

---

## 4. fallback の扱い
今回は Google Places Search の最小実装なので、fallback は**簡易版**で構いません。

### 推奨
- strict query をまず1回投げる
- 0件で `enable_fallback=True` の場合のみ、条件を緩めた query を再試行してよい

最小 fallback 例:
1. genre + location
2. genre only
3. location only

ただし、Google API 呼び出し回数が増えるため、
まずは **strict のみ実装し、fallback は diagnostics 上未使用でもよい** です。

その場合:
- `fallback_enabled` は true/false を保持
- `fallback_applied` は false のまま
- `matched_stage` は `text_search`

としてください。

重要なのは、**嘘の fallback を書かないこと** です。

---

## 5. snippet の作り方
`results[].snippet` は最低限でよいです。

例:
- `"東京都渋谷区恵比寿 / italian / PRICE_LEVEL_MODERATE / rating 4.2"`

ここでは自然文の品質よりも、
**retriever や normalizer に渡す前の軽い候補要約**として意味が通れば十分です。

---

## 6. HTTP 実装方針
### ライブラリ
- `requests` でも `httpx` でもよい
- 既存依存に合わせやすいものを選ぶ

### 要件
- API キーは `GooglePlacesConfig` から取得
- timeout を使う
- field mask をヘッダで指定する
- エラー時は diagnostics に反映する

### 例外
- API キー未設定 → 明示的例外
- timeout → `api_error="timeout"`
- 非200 → `api_error="http_error"` など

---

## 7. normalize / pipeline との接続
今回は search のみなので、pipeline 全体を Google searcher で動かしたときに問題になるのは retrieve です。

### ここでの方針
最低限どちらかを実装してください。

#### 方針A（推奨）
GooglePlacesSearcher を単体で使う範囲に留め、pipeline の default は変えない。
テストでは searcher 単体または adapter injection で search 結果だけ確認する。

#### 方針B
pipeline で Google searcher を使うとき、retrieve が未実装なら明示的に失敗する。

今回は無理に pipeline end-to-end を完成させなくてよいです。
**search 実装を先に切り出して確認することを優先**してください。

---

## 8. テスト要求
以下のどれか、または複数を追加してください。

### A. textQuery 生成のテスト
- conditions → textQuery が期待通りになる

### B. API 呼び出しをモックした unit test
- HTTP レスポンス JSON をモック
- `results` と `search_diagnostics` が正しいことを検証

### C. API エラー時のテスト
- timeout
- 非200
- API キー未設定

### D. adapter injection の継続確認
- mock は壊れない
- GooglePlacesSearcher は別注入で使える

重要:
- 実際の Google API を叩くテストは不要
- テストは deterministic にする

---

## 9. README 更新
必要なら以下を追記してください。
- Google Places Search は最小実装されたこと
- Retrieve はまだ未実装であること
- 実行には `GOOGLE_PLACES_API_KEY` が必要なこと
- 現時点では pipeline 全体の default は mock のままであること

---

## 10. 成功条件
- `GooglePlacesSearcher.search_places()` が実装される
- API キー・timeout・エラー処理が最低限ある
- `results + search_diagnostics` 形式で返る
- mock 実装は壊れない
- テストが通る
- retrieve 未実装であることが明確なまま保たれる

---

## 11. 今回やらないこと
- Place Details 実装
- nearest_station 推定
- atmosphere 抽出の高度化
- geocoding 本実装
- pipeline 完全 end-to-end の Google 化

---

## 最後に出してほしいもの
1. 変更ファイル一覧
2. textQuery 生成ルールの説明
3. diagnostics の出力例
4. テスト内容
5. まだ未実装の部分
