# Opus 実装指示書: Restaurant Fallback Diagnostics と Strict モード追加

この指示書に従って、restaurant 候補収集パイプラインに fallback の診断情報と strict モードを追加してください。

## 背景
現在の search は以下のように改善されています。
- genre / location による hard filter
- max_price による soft sort
- `genre+location → genreのみ → locationのみ → 全件` の fallback

この設計自体は有用ですが、fallback が入ると
- 検索が本当に正常に機能したのか
- 条件を外して救済しただけなのか

が見えにくくなります。

今回は、fallback の有無を可視化し、strict 検索と fallback 検索を分離して確認できるようにしてください。

---

## 目的
次の2点を実現することです。

1. `search_places()` が fallback したかどうかを、結果に診断情報として残す
2. fallback を無効化できる strict モードを追加する

---

## 今回の対象
主な対象ファイル:
- `src/searchers/place_searcher.py`
- `src/pipeline/restaurant_pipeline.py`
- `scripts/run_restaurant_pipeline.py`
- `tests/test_restaurant_pipeline.py`
- 必要なら `README.md`

---

## 1. search_places の返り値を拡張
### 現状
現在 `search_places()` は `list[dict]` を返しています。

### 変更後
`search_places()` は検索結果本体に加えて、diagnostics を返してください。

推奨返却形式:
```json
{
  "results": [
    {
      "source": "place_search",
      "source_id": "place_1",
      "title": "Trattoria A",
      "snippet": "静かな雰囲気のイタリアン。恵比寿駅徒歩5分"
    }
  ],
  "search_diagnostics": {
    "strict_conditions": {
      "genre": "italian",
      "location": "恵比寿",
      "max_price": 3000
    },
    "matched_stage": "genre+location",
    "fallback_applied": false,
    "fallback_steps": [],
    "strict_result_count": 2,
    "final_result_count": 2
  }
}
```

fallback が発生した場合の例:
```json
{
  "results": [...],
  "search_diagnostics": {
    "strict_conditions": {
      "genre": "sushi",
      "location": "六本木"
    },
    "matched_stage": "all",
    "fallback_applied": true,
    "fallback_steps": [
      "genre+location",
      "genre_only",
      "location_only",
      "all"
    ],
    "strict_result_count": 0,
    "final_result_count": 4
  }
}
```

---

## 2. strict モード追加
`search_places()` に以下の引数を追加してください。

```python
search_places(conditions: dict, enable_fallback: bool = True)
```

### 仕様
- `enable_fallback=True` のときは現行通り fallback を有効にする
- `enable_fallback=False` のときは strict 条件での結果のみ返す
- strict 条件で0件なら、そのまま0件を返す
- diagnostics には strict モードだったことが分かる情報を含める

例:
```json
{
  "search_diagnostics": {
    "fallback_enabled": false,
    "fallback_applied": false,
    "matched_stage": "strict_only",
    "strict_result_count": 0,
    "final_result_count": 0
  }
}
```

---

## 3. pipeline 側への反映
`run_restaurant_pipeline()` にも、fallback 制御と diagnostics を通してください。

推奨シグネチャ例:
```python
run_restaurant_pipeline(request_id: str, user_query: str, enable_fallback: bool = True) -> dict
```

### 要件
- search の diagnostics を pipeline 内で保持する
- 最終 response に `search_diagnostics` を追加してよい
- あるいは `pipeline_diagnostics` という形でもよい
- ただし response schema を壊すなら、既存 schema の外側で optional に扱うか、schema を更新すること

ここでは、実装の一貫性を優先してください。

---

## 4. run スクリプトの改善
`scripts/run_restaurant_pipeline.py` に strict 実行オプションを追加してください。

例:
- `--mock`
- `--live`
- `--strict`

仕様:
- `--strict` が指定された場合、`enable_fallback=False` で pipeline を実行
- mock / live どちらでも使えるようにしてよい

実行例:
```bash
uv run scripts/run_restaurant_pipeline.py --mock --strict
```

---

## 5. テスト要求
以下を追加または更新してください。

### A. strict 検索で0件になるケース
- `genre=sushi, location=六本木` で strict 実行
- `results == []`
- `fallback_enabled == false`
- `strict_result_count == 0`
- `final_result_count == 0`

### B. fallback 検索で救済されるケース
- 同じ条件で fallback 有効
- `final_result_count > 0`
- `fallback_applied == true`
- `matched_stage == all` などが分かる

### C. strict hit と fallback hit を区別できること
- `恵比寿 + italian` は strict でヒット
- `fallback_applied == false`
- `matched_stage == genre+location` など

### D. pipeline response に diagnostics が残ること
- `run_restaurant_pipeline()` の戻り値から、検索段階の情報が追えること

### E. deterministic
- 同じ query, 同じ mode では同じ diagnostics と結果順になること

---

## 6. 追加したい診断項目
最低限、以下のどれかを残してください。

- `fallback_enabled`
- `fallback_applied`
- `matched_stage`
- `strict_result_count`
- `final_result_count`
- `fallback_steps`

任意で追加してよいもの:
- `relaxed_fields`
- `search_reason`
- `candidate_count_before_sort`

---

## 7. 実装上の注意
- fallback は UX のための救済であり、検索品質評価とは分ける
- evaluate 側の責務は変えない
- fallback したからといって search 結果を偽装しない
- diagnostics は内部監査やデバッグ用として意味が通るようにする

---

## 8. README 更新
必要なら以下を追記してください。
- strict モードの存在
- fallback の有無が diagnostics に残ること
- fallback は検索救済であり、strict hit とは区別されること

---

## 成功条件
- strict 検索と fallback 検索を切り替えられる
- fallback の有無が結果から分かる
- pipeline でも検索診断が追える
- テストが通る
- 既存の評価ロジックを壊さない

---

## 最後に出してほしいもの
1. 変更ファイル一覧
2. diagnostics のデータ構造の説明
3. strict / fallback の挙動差の例
4. 実行コマンド例
5. まだ mock のまま残っている部分
