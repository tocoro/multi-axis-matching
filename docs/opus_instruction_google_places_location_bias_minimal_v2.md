# Opus 実装指示書: Google Places locationBias 最小実装

この指示書に従って、`GooglePlacesSearcher` に **locationBias の最小実装** を追加してください。

## 目的
現状の `GooglePlacesSearcher` は `textQuery` だけで Text Search API を呼んでいます。
restaurant 検索では location の効きが強いため、今回は **location がある場合のみ** Google Places API に `locationBias` を付けられるようにしてください。

今回は最小実装に限定します。

対象:
- `location` がある場合に `locationBias` を request body に追加する
- diagnostics に `location_bias_applied` を正しく反映する
- まずは少数の地名だけ fixed mapping で対応する
- テストを追加する

非対象:
- Geocoding API の実接続
- 汎用的な地名解決
- radius の最適化
- locationRestriction の導入
- fallback query の多段API呼び出し

---

## 背景
現状の `GooglePlacesSearcher`:
- `build_text_query(conditions)` で textQuery を生成
- `places:searchText` を呼ぶ
- `location_bias_applied` は実質未使用
- location は textQuery 内の文字列にしか反映されていない

この状態でも動くが、restaurant では location の絞りが弱い可能性が高いです。

そのため、今回は **fixed mapping による locationBias** を最小導入します。

---

## 今回の対象ファイル
主な対象:
- `src/adapters/places/google_places.py`
- 必要なら `src/adapters/places/config.py`
- `tests/test_google_places.py`
- 必要なら `README.md`

---

## 1. 実装方針
### 1-1. locationBias は fixed mapping でよい
最初は少数の地名のみ対応してください。

例:
```python
_LOCATION_BIAS_CIRCLES = {
    "恵比寿": {"latitude": 35.6467, "longitude": 139.7100, "radius": 1500.0},
    "渋谷": {"latitude": 35.6580, "longitude": 139.7016, "radius": 2000.0},
    "新宿": {"latitude": 35.6900, "longitude": 139.7000, "radius": 2500.0},
    "六本木": {"latitude": 35.6628, "longitude": 139.7310, "radius": 2000.0}
}
```

値は厳密でなくてよいですが、明らかに不自然な値は避けてください。

### 1-2. location が fixed mapping にある場合のみ付与
- `conditions["location"]` が存在
- かつ fixed mapping にある

このときだけ request body に `locationBias` を追加してください。

### 1-3. location が未知なら付与しない
- `location` がない
- `location` はあるが fixed mapping にない

この場合は `locationBias` を付けず、従来どおり textQuery のみで検索してください。

---

## 2. request body の形
Google Places Text Search API に送る body に、次のような `locationBias` を追加してください。

例:
```json
{
  "textQuery": "italian restaurant in 恵比寿",
  "maxResultCount": 5,
  "locationBias": {
    "circle": {
      "center": {
        "latitude": 35.6467,
        "longitude": 139.7100
      },
      "radius": 1500.0
    }
  }
}
```

---

## 3. 補助関数の追加
実装を分かりやすくするため、必要なら補助関数を追加してください。

推奨例:
- `build_location_bias(location: str) -> dict | None`
- `_build_search_body(text_query: str, conditions: dict, max_results: int) -> tuple[dict, bool]`

責務を分け、テストしやすくしてください。

---

## 4. diagnostics の更新
`search_diagnostics` の `location_bias_applied` を、実際の request に応じて true/false で返してください。

推奨:
- マッピングに成功して request body に `locationBias` を入れた → `true`
- 入れていない → `false`

任意で次も追加してよいです。
- `location_bias_source`: `"fixed_mapping"` / `null`
- `location_bias_location`: `"恵比寿"` / `null`

ただし、既存の schema やテストを壊さない範囲で行ってください。

---

## 5. ついでに直してよい軽修正
今回の実装にあわせて、次の軽修正を入れてよいです。

### A. `strict_result_count` の意味を明確化
現状は fallback 未実装なのに `strict_result_count` に API結果件数をそのまま入れています。
今の段階では実害は小さいですが、将来のために変数名・コメント・docstring のいずれかで
「strict 1回目の API 結果件数」であることを明確にしてください。

### B. snippet の軽整形
`primaryType` が `italian_restaurant` のような API 生値のまま出ています。
最低限、snippet 表示用に `_` を空白へ変換する程度の整形を入れてよいです。
意味を勝手に推測して翻訳しなくてよいです。

---

## 6. テスト要求
最低限、以下を追加してください。

### A. locationBias 生成の unit test
- `"恵比寿"` → `locationBias` が返る
- 未知地名 → `None`

### B. request body に locationBias が入ること
- `conditions={"genre": "italian", "location": "恵比寿"}`
- API 呼び出し時の body に `locationBias` が含まれること

### C. diagnostics に反映されること
- known location → `location_bias_applied == true`
- unknown location → `location_bias_applied == false`

### D. 既存動作を壊さないこと
- location なしでも検索できる
- mock adapter のテストは壊れない
- `GooglePlacesRetriever` は未実装のまま

### E. deterministic
- 同じ location では同じ bias が生成される

---

## 7. README 更新
必要なら以下を追記してください。
- Google Places Search は locationBias の最小対応を持つこと
- まだ fixed mapping であり、汎用地名解決ではないこと
- 未知地名では bias を付けず textQuery のみで検索すること

---

## 8. 実装上の注意
- 今回は fixed mapping で十分
- Geocoding API を勝手に追加しない
- locationBias を付けられない場合でも失敗にしない
- diagnostics には実際の挙動を正しく残す
- `textQuery` のロジックはなるべく壊さない

---

## 9. 成功条件
- known location で `locationBias` が request body に入る
- diagnostics に `location_bias_applied` が反映される
- unknown location では bias なしで動く
- 既存の最小実装方針を壊さない
- テストが通る

---

## 10. 今回やらないこと
- Geocoding API 接続
- locationRestriction
- fallback の多段実API呼び出し
- Place Details 実装
- nearest_station 推定

---

## 最後に出してほしいもの
1. 変更ファイル一覧
2. fixed mapping の地名一覧
3. known/unknown location での挙動差
4. diagnostics の例
5. まだ未実装の部分
