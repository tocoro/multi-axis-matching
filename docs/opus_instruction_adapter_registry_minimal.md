# Opus 実装指示書: adapter registry を最小導入する

この指示書に従って、multi-axis-matching に **adapter registry の最小構造** を導入してください。

## 背景
現状の repo では、
- restaurant / clinic の 2 ドメインが存在する
- evaluator / aggregation は共通カーネルとして再利用されている
- DomainProfile / ProblemTypeSpec も導入済み

ただし現時点では、各 pipeline がまだ直接
- searcher
- retriever
- normalizer

を import / new しており、
**DomainProfile があっても adapter binding はコード上で分散したまま** です。

このギャップを埋めるため、今回は **adapter registry の最小導入** を行ってください。

---

## 目的
次の5点を実現してください。

1. ドメインごとの adapter binding を 1 か所で定義できるようにする
2. pipeline が registry 経由で adapter を取得できるようにする
3. restaurant / clinic の既存動作を壊さない
4. 過度な抽象化を避ける
5. 将来の generic dispatch の足場にする

---

## スコープ
### 対象
- minimal adapter registry の追加
- restaurant / clinic の binding 登録
- pipeline からの最小参照変更
- tests
- 必要なら docs 更新

### 非対象
- full DI container
- generic run_pipeline(profile, ...) の全面導入
- dynamic domain routing 完成
- third domain
- evaluator ロジック変更

---

## 今回の対象ファイル
主な対象:
- `src/domain/adapters.py` または `src/domain/registry.py`
- `src/pipeline/restaurant_pipeline.py`
- `src/pipeline/clinic_pipeline.py`
- `tests/test_adapter_registry.py`
- 必要なら `docs/core_vs_domain_architecture.md`

repo 構成に合わせて調整してよいです。

---

## 1. 最小 registry を定義
少なくとも次の概念を持つ構造を定義してください。

### A. AdapterBinding
最低限ほしい項目:
- `domain_name`
- `searcher_factory`
- `retriever_factory`
- `normalizer` または `normalizer_fn`

実装方法は dataclass / TypedDict / simple dict のどれでもよいですが、
**読みやすいことを優先**してください。

例:
```python
@dataclass(frozen=True)
class AdapterBinding:
    domain_name: str
    searcher_factory: Callable[[], Any]
    retriever_factory: Callable[[], Any]
    normalizer_fn: Callable[..., dict]
```

### B. Registry
推奨:
- `ADAPTER_REGISTRY = {"restaurant": ..., "clinic": ...}`
- `get_adapter_binding(domain_name: str) -> AdapterBinding | None`

---

## 2. restaurant / clinic を登録
少なくとも次の 2 件を登録してください。

### restaurant
- searcher: 既存 restaurant searcher
- retriever: 既存 restaurant retriever
- normalizer: 既存 restaurant normalizer

### clinic
- searcher: MockClinicSearcher
- retriever: MockClinicRetriever
- normalizer: clinic normalizer

重要なのは、
**これまで pipeline にベタ書きだった binding を registry 側に寄せること**です。

---

## 3. pipeline で registry 経由の取得に変える
restaurant / clinic pipeline では、
これまで直接インスタンス化していた部分を、可能な範囲で registry 経由に変えてください。

### 例
現在が
```python
searcher = place_searcher or MockPlaceSearcher()
retriever = place_retriever or MockPlaceRetriever()
```
なら、
```python
binding = get_adapter_binding("restaurant")
searcher = place_searcher or binding.searcher_factory()
retriever = place_retriever or binding.retriever_factory()
normalizer = binding.normalizer_fn
```
のような形に寄せてください。

ただし、今回は **全面共通化は不要** です。

---

## 4. normalizer の扱い
normalizer は domain 差が大きいので、registry に載せる意味があります。

ただし、無理にシグネチャ統一しなくてよいです。
今回の目的は
- registry に normalizer の参照がある
- pipeline がその参照を使える

ところまでで十分です。

---

## 5. DomainProfile との関係
今回は DomainProfile と AdapterBinding を統合しなくてよいです。

ただし docs やコメントで、
- DomainProfile は説明的メタ情報
- AdapterBinding は実行時の binding

という区別が分かるようにしてください。

これは重要です。

---

## 6. テスト要求
最低限、以下を追加してください。

### A. registry definition
- restaurant binding が取得できる
- clinic binding が取得できる

### B. binding content
- restaurant binding に searcher / retriever / normalizer がある
- clinic binding に searcher / retriever / normalizer がある

### C. pipeline uses registry
- restaurant pipeline が registry binding 由来で動く
- clinic pipeline が registry binding 由来で動く

### D. missing binding
- unknown domain で None または固定挙動を返す

### E. backward compatibility
- 既存 restaurant / clinic tests を壊さない

---

## 7. docs 更新（任意）
必要なら 1〜2 行だけ追加してください。

書きたいこと:
- DomainProfile に加えて AdapterBinding registry を導入した
- メタ情報と実行時 binding の区別が見えるようになった

---

## 8. 実装上の注意
- 最小導入に留める
- いきなり full generic pipeline にしない
- DomainProfile と役割を混同しない
- pipeline 可読性を落とさない
- 既存 import パスが少し残ってもよい

---

## 9. 成功条件
- adapter registry が追加される
- restaurant / clinic binding が登録される
- pipeline が最小限 registry 経由で動く
- tests が通る
- 既存動作を壊さない

---

## 10. 今回やらないこと
- full dependency injection
- dynamic routing 完成
- registry から problem_type まで完全統合
- third domain
- evaluator prompt 自動切り替え

---

## 最後に出してほしいもの
1. 追加ファイル一覧
2. AdapterBinding の項目要約
3. restaurant / clinic の binding 要約
4. pipeline のどこを registry 経由にしたか
5. 追加したテスト
