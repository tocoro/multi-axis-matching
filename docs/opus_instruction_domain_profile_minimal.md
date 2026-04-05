# Opus 実装指示書: DomainProfile / ProblemTypeSpec を最小導入する

この指示書に従って、multi-axis-matching に **DomainProfile / ProblemTypeSpec の最小構造** を導入してください。

## 背景
現状の repo では、restaurant と clinic の2ドメインが存在し、
共通 evaluator / aggregation カーネルが再利用できることは実証されました。

ただし、現時点では
- `run_restaurant_pipeline()`
- `run_clinic_pipeline()`

が並列に存在しているだけで、
**「あるドメインが何を持つか」をコード上で表す object / contract** がまだありません。

そのため、設計文書では Core / Domain の境界が見えていても、
コード上ではまだ domain-specific 構造が散在して見えます。

このギャップを埋めるため、今回は **最小限の DomainProfile / ProblemTypeSpec** を追加してください。

---

## 目的
次の5点を実現してください。

1. 各ドメインの基本情報を表す `DomainProfile` を定義する
2. 問題タイプの最小情報を表す `ProblemTypeSpec` を定義する
3. restaurant / clinic の profile を 2 件用意する
4. 既存 pipeline が profile を参照できるようにする（ただし大規模リファクタは不要）
5. 将来の adapter registry / normalizer registry の足場にする

---

## スコープ
### 対象
- `DomainProfile` / `ProblemTypeSpec` の最小 dataclass / typed dict / pydantic などの導入
- restaurant / clinic profile 定義
- pipeline からの軽い参照
- tests
- 必要なら docs 更新

### 非対象
- full adapter registry 実装
- pipeline の全面抽象化
- dynamic domain dispatch の完全実装
- 3ドメイン目追加
- evaluator ロジック変更

---

## 今回の対象ファイル
主な対象:
- `src/domain/` か `src/contracts/` 配下に profile 定義
- `src/domain/profiles.py` のような profile 登録ファイル
- `src/pipeline/restaurant_pipeline.py`
- `src/pipeline/clinic_pipeline.py`
- `tests/test_domain_profiles.py`
- 必要なら `docs/core_vs_domain_architecture.md`

repo 構成に合わせて調整してよいです。

---

## 1. ProblemTypeSpec を最小定義
まず、問題タイプの最小構造を定義してください。

最低限ほしい項目:
- `problem_type`: 例 `local.restaurant`, `local.clinic`
- `risk_level`: 例 `normal`, `high`
- `example_axes`: list[str]
- `notes` または `description`（任意）

例:
```python
ProblemTypeSpec(
    problem_type="local.clinic",
    risk_level="high",
    example_axes=["specialty_fit", "distance", "hours", "insurance", "availability"],
)
```

ここで重要なのは、
**軸が固定されることではなく、ドメインごとに想定軸の例を持てること**です。

---

## 2. DomainProfile を最小定義
次に DomainProfile を定義してください。

最低限ほしい項目:
- `domain_name`: 例 `restaurant`, `clinic`
- `default_problem_type`: ProblemTypeSpec またはその参照
- `candidate_source_kind`: 例 `places`, `clinic_directory_mock`
- `normalizer_name`
- `supports_solution_catalog`: bool
- `notes` または `description`（任意）

可能なら将来のために、文字列レベルでよいので以下も含めてください。
- `search_adapter_name`
- `retriever_name`

例:
```python
DomainProfile(
    domain_name="clinic",
    default_problem_type=CLINIC_PROBLEM,
    candidate_source_kind="clinic_mock",
    normalizer_name="clinic_normalizer",
    search_adapter_name="MockClinicSearcher",
    retriever_name="MockClinicRetriever",
    supports_solution_catalog=False,
)
```

---

## 3. restaurant / clinic の profile を定義
少なくとも次の 2 件を用意してください。

### restaurant
- problem_type: `local.restaurant`
- risk_level: `normal`
- example_axes: cuisine, budget, atmosphere, location
- source kind: `places`
- supports_solution_catalog: true

### clinic
- problem_type: `local.clinic`
- risk_level: `high`
- example_axes: specialty_fit, distance, hours, insurance, availability
- source kind: `clinic_mock`
- supports_solution_catalog: false でも true でも可（現状実装に合わせる）

---

## 4. 既存 pipeline で軽く参照する
今回は大規模リファクタ不要です。

最低限、pipeline 内で profile を読み、
- domain 名
- default problem type
- risk level

のどれかがログや response 補助情報に見えるようにしてください。

やってよい例:
- `response["domain_profile"] = {...minimal info...}` を入れる
- pipeline 内部ログに profile を出す
- test で profile と実際の problem_type が整合することを確認する

やらなくてよい例:
- pipeline を generic `run_pipeline(profile, ...)` に全面変更

---

## 5. 登録・参照方法
profile の参照は最小でよいです。

推奨:
- `DOMAIN_PROFILES = {"restaurant": RESTAURANT_PROFILE, "clinic": CLINIC_PROFILE}`
- `get_domain_profile(name: str) -> DomainProfile`

存在しないドメインは `KeyError` か `None` でよいですが、
テストで挙動を固定してください。

---

## 6. テスト要求
最低限、以下を追加してください。

### A. profile 定義テスト
- restaurant / clinic profile が取得できる
- default problem type が正しい
- risk_level が正しい

### B. pipeline 整合性テスト
- restaurant pipeline の problem_type が restaurant profile と整合
- clinic pipeline の problem_type が clinic profile と整合

### C. example axes テスト
- restaurant profile の axes 例に cuisine がある
- clinic profile の axes 例に specialty_fit がある

### D. missing profile test
- unknown domain の取得挙動を固定

### E. backward compatibility
- 既存 restaurant / clinic tests を壊さない

---

## 7. docs 更新（任意だが推奨）
必要なら `docs/core_vs_domain_architecture.md` に短く追記してください。

書きたいこと:
- code 上でも DomainProfile / ProblemTypeSpec の最小構造を導入した
- まだ full registry ではないが、ドメイン構造が object として見えるようになった

---

## 8. 実装上の注意
- 最小導入に留める
- 過度に抽象化しない
- 既存 pipeline を壊さない
- evaluator の自由な axis selection は維持する
- example axes は制約ではなく説明用の profile 情報であることを明確にする

---

## 9. 成功条件
- DomainProfile / ProblemTypeSpec が追加される
- restaurant / clinic profile が定義される
- pipeline が最小限それを参照する
- テストで構造が固定される
- 既存動作を壊さない

---

## 10. 今回やらないこと
- full generic pipeline
- adapter registry 本実装
- dynamic routing
- third domain
- prompt の自動切り替え

---

## 最後に出してほしいもの
1. 追加ファイル一覧
2. DomainProfile / ProblemTypeSpec の項目要約
3. restaurant / clinic profile の要約
4. pipeline でどこを参照したか
5. 追加したテスト
