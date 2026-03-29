# Opus 実装指示書: Restaurant Search Filtering 強化

この指示書に従って、restaurant 候補収集パイプラインの次段階を実装してください。

## 目的
現状の `search_places()` は検索条件を受け取っていますが、実際には固定候補プールを全件返しています。
次段階では、mock のままでよいので、検索条件に応じて候補をある程度絞り込めるようにしてください。

今回の重点は以下です。
- search step に最低限の意味を持たせる
- location / genre / price 条件を使って候補を絞り込む
- normalize / evaluate は大きく壊さない
- mock 実装のまま deterministic に保つ

---

## 今回の対象
対象ファイルの中心:
- `src/searchers/place_searcher.py`
- 必要に応じて `tests/test_restaurant_pipeline.py`
- 必要に応じて `README.md`

必要なら補助関数や小さなデータ構造を追加してよいです。

---

## 現状の問題
`search_places(conditions)` は `conditions` を受け取っているが、
実際には候補プールを全件返しているだけです。

そのため、現状は
- query understanding
- search

が構造上は分離されていても、検索としてはまだ機能していません。

---

## 今回やってほしいこと

### 1. `search_places()` に簡易フィルタを実装
少なくとも以下を使って候補を絞り込んでください。

- `location`
- `genre`
- `max_price`

`atmosphere` はあってもよいですが、必須ではありません。

### 2. フィルタは hard filter と soft filter を分ける
初期版として、以下の方針で構いません。

#### hard filter 候補
- genre が明確に一致しない候補は落としてよい
- location が明確に遠い候補は落としてよい

#### soft filter 候補
- budget は厳密除外ではなく、優先度に使ってもよい
- atmosphere は search 段階では軽めでよい

ただし restaurant の用途上、結果が 0 件になりやすい実装にはしないでください。

### 3. 候補が 0 件になる場合のフォールバック
絞り込みすぎて 0 件になる場合は、段階的に条件を緩めてください。

推奨フォールバック順:
1. genre + location で絞る
2. genre のみ or location のみ
3. 全件返す

### 4. 検索結果にスコアまたは理由を持たせてもよい
任意ですが、search 段階で
- why matched
- matched_fields
- preliminary_score

のような情報を持たせてもよいです。
ただし evaluate の責務を奪わないでください。

### 5. deterministic に保つ
mock 検索なので、同じ入力では常に同じ出力にしてください。

---

## データの扱い
現在 `_MOCK_PLACES` には `_tags` が入っています。
この `_tags` を使ってフィルタしてよいです。

必要なら `_tags` に以下のような属性を増やしてよいです。
- `atmosphere`
- `approx_max_price`
- `station_group`

ただし、過剰な複雑化は不要です。

---

## 推奨仕様

### 入力例
```json
{
  "location": "恵比寿",
  "genre": "italian",
  "max_price": 3000,
  "atmosphere": "quiet"
}
```

### 出力イメージ
```json
[
  {
    "source": "place_search",
    "source_id": "place_1",
    "title": "Trattoria A",
    "snippet": "静かな雰囲気のイタリアン。恵比寿駅徒歩5分"
  },
  {
    "source": "place_search",
    "source_id": "place_3",
    "title": "Osteria C",
    "snippet": "中目黒の隠れ家イタリアン。リーズナブル"
  }
]
```

この場合、Bar B のような
- genre 不一致
- atmosphere 不一致

候補は search 段階で落ちてもよいです。

---

## テスト要求
以下を追加または更新してください。

### A. genre + location が一致する候補が優先される
- `恵比寿で静かに話せるイタリアン` なら place_1 は残る
- place_2 は genre 不一致で除外されてよい

### B. location 違いの候補の扱い
- place_3 は中目黒なので、条件次第で残る / 落ちる を明示
- 少なくともテストで意図を固定してください

### C. 条件が強すぎるときのフォールバック
- 0 件になる条件を入れたときに、全件返却または条件緩和が起きること

### D. deterministic
- 同じ conditions で同じ search 結果順が返ること

### E. pipeline E2E の調整
- これまで ranking が4件前提だったテストは、必要なら修正してください
- 新しい検索仕様に沿って、候補件数の期待値を更新してください

---

## 実装方針
- search はまだ mock のままでよい
- retrieve / normalize / evaluate は可能な限りそのまま使う
- 責務分離を保つ
- 検索段階でスコアリングしすぎない
- ranking は最終的に evaluate に任せる

---

## README 更新
必要なら、以下を README に追記してください。
- mock search が全件返却ではなく、条件ベースの簡易フィルタになったこと
- まだ実 API ではないこと
- 条件が強すぎる場合はフォールバックすること

---

## 成功条件
- `search_places()` が conditions を実際に使う
- query に応じて候補数や候補集合が変わる
- 0 件時のフォールバックがある
- テストが通る
- pipeline 全体が壊れない

---

## 最後に出してほしいもの
1. 変更ファイル一覧
2. search の新ルールの説明
3. 追加・更新したテストの説明
4. 実行結果の例
5. まだ mock のまま残っている部分
