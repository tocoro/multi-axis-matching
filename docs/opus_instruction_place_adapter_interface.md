# Opus 実装指示書: Place Adapter Interface 化

この指示書に従って、restaurant 候補収集パイプラインを、将来的に Google Places 等の実 API に差し替えやすい構造へ整理してください。

## 背景
現状の pipeline は以下の段階までできています。
- query understanding
- search (mock, 条件ベースフィルタ + fallback)
- retrieve (mock)
- normalize
- evaluate
- fallback diagnostics / strict mode

ただし `place_searcher.py` と `place_retriever.py` は mock 実装に直接結びついています。
このままでも動きますが、実 API に差し替える段階で
- mock 実装
- 実 API 実装
- テスト用実装

を切り替えにくくなります。

そのため今回は、**PlaceSearcher / PlaceRetriever の adapter interface を先に固定する** ことが目的です。

---

## 目的
次の2点を実現してください。

1. search / retrieve の責務を interface と実装に分ける
2. Mock 実装を維持しつつ、将来的に `GooglePlacesSearcher` / `GooglePlacesRetriever` を追加できる構造にする

今回は **Google Places 本体の接続実装までは不要** です。
まずは interface と mock adapter への置き換えまでを行ってください。

---

## 今回の対象
主な対象ファイル:
- `src/searchers/place_searcher.py`
- `src/retrievers/place_retriever.py`
- `src/pipeline/restaurant_pipeline.py`
- `tests/test_restaurant_pipeline.py`
- 必要なら `scripts/run_restaurant_pipeline.py`
- 必要なら `README.md`

必要なら新規ディレクトリを追加してよいです。

推奨例:
```text
src/
  adapters/
    places/
      base.py
      mock_places.py
```

---

## 1. interface を定義
以下のような構造を作ってください。

### 推奨構造
- `PlaceSearcher`
- `PlaceRetriever`

Python では abstract base class か Protocol でよいです。

### 例
```python
class PlaceSearcher(Protocol):
    def search_places(self, conditions: dict, enable_fallback: bool = True) -> dict:
        ...

class PlaceRetriever(Protocol):
    def retrieve_place(self, source: str, source_id: str) -> dict:
        ...
```

ここでの返り値は、**いまの mock 実装が返している形を維持**して構いません。

---

## 2. mock 実装を adapter に移動
現在の `search_places()` と `retrieve_place()` の実ロジックを、mock adapter 実装に移してください。

推奨例:
- `MockPlaceSearcher`
- `MockPlaceRetriever`

現状のロジックはできるだけ変えないでください。
- 条件ベースフィルタ
- fallback
- diagnostics
- deterministic

は維持してください。

---

## 3. pipeline で interface 経由にする
`run_restaurant_pipeline()` は、直接モジュール関数を呼ぶのではなく、adapter を受け取れるようにしてください。

推奨シグネチャ例:
```python
run_restaurant_pipeline(
    request_id: str,
    user_query: str,
    enable_fallback: bool = True,
    place_searcher: PlaceSearcher | None = None,
    place_retriever: PlaceRetriever | None = None,
) -> dict
```

### 仕様
- 指定がない場合は mock adapter を使う
- テストでは明示的に mock adapter を渡してもよい
- 将来 GooglePlacesSearcher / GooglePlacesRetriever を渡せる構造にする

---

## 4. 実API接続用のスタブを用意してよい
今回は実接続は不要ですが、将来用に空クラスや NotImplementedError ベースのスタブを置いても構いません。

例:
- `GooglePlacesSearcher`
- `GooglePlacesRetriever`

ただし、API キーがなくてもテストが通る状態を保ってください。

もしスタブを作るなら、以下を明記してください。
- 未実装であること
- どの環境変数が必要になる想定か

---

## 5. テスト要求
以下を追加または更新してください。

### A. pipeline が default で mock adapter を使って通ること
- 既存テストを維持

### B. explicit adapter injection ができること
- `run_restaurant_pipeline(..., place_searcher=..., place_retriever=...)`
- 注入した adapter が使われること

### C. search / retrieve interface の責務が分離されていること
- 少なくともテストコードや構造から見て明確であること

### D. diagnostics が維持されること
- interface 化後も `search_diagnostics` が消えないこと

### E. deterministic が維持されること
- mock adapter で結果順が変わらないこと

---

## 6. 設計上の注意
- 今回は adapter interface 化が目的であり、実API実装は目的ではない
- evaluate の責務は変えない
- normalize の責務も変えない
- mock のテスト容易性を壊さない
- API接続前に構造を固めることを優先する

---

## 7. README 更新
必要なら README に以下を追記してください。
- place search / retrieve は adapter 経由になったこと
- デフォルト実装は mock であること
- 将来的に Google Places などへ差し替え可能な設計にしたこと

---

## 成功条件
- search / retrieve が interface と実装に分離される
- pipeline が adapter injection を受け付ける
- mock 実装で既存動作が維持される
- diagnostics / strict mode / fallback が壊れない
- テストが通る

---

## 今回はやらないこと
- Google Places API の本接続
- 実際の HTTP 通信
- API キー必須のテスト
- product / clinic への展開

---

## 最後に出してほしいもの
1. 変更ファイル一覧
2. interface 構造の説明
3. default mock と将来 adapter 差し替えの使い分け説明
4. 実行コマンド例
5. まだ未実装の実 API 接続部分
