# Core vs Domain Architecture

## 概要
multi-axis-matching は「共通評価カーネル + ドメイン adapter」の構成を目指している。
現段階では restaurant adapter の1実装例が中心であり、fully generic system ではない。

## アーキテクチャ図

```
User Query
   ↓
Problem Structuring       ← CORE: problem type 推定、制約抽出
   ↓
Candidate Collection      ← DOMAIN: search adapter, retrieve adapter
   ↓
Normalization             ← DOMAIN: raw → candidate 変換
   ↓
Solution Catalog (optional) ← DOMAIN: 候補側意味記述
   ↓
Axis Selection            ← CORE: LLM 動的選定 (問題タイプ依存)
   ↓
Multi-Axis Evaluation     ← CORE: 軸別 score / status / reason
   ↓
Aggregation / Ranking     ← CORE: unknown 除外、hard violation 失格
   ↓
Explanation / Output      ← CORE: missing_information, diagnostics
```

## Core（共通カーネル）

| コンポーネント | 役割 | ドメイン非依存か |
|---|---|---|
| `evaluator.py` | 多軸評価パイプライン | はい — axes は LLM が動的選定 |
| `aggregate_scores()` | unknown 除外、重み付き集約 | はい |
| `check_disqualification()` | hard_constraint_violation 判定 | はい |
| Problem type 推定 | LLM ベース | はい — 5 type 定義済み |
| 制約抽出 | LLM ベース | はい |
| Prompts | LLM 指示テンプレート | はい (軸別例はドメイン示唆を含む) |
| Schema (request/response) | 入出力構造 | はい |
| Score gradient guide | スコア帯域 prompt | はい |
| Catalog usage contract | catalog 利用規約 | はい |

**Core が保証すること:**
- unknown / conflict / hard_constraint_violation の区別
- unknown を分母から除外
- conflict を低スコアとして集計 (失格にしない)
- hard_constraint_violation のみ失格
- 高リスク領域の保守的ペナルティ
- 軸別 reason、missing_information の返却

## Domain（ドメイン依存部分）

| コンポーネント | Restaurant 実装 | 差し替え対象 |
|---|---|---|
| Search adapter | `MockPlaceSearcher`, `GooglePlacesSearcher` | ドメイン別 source |
| Retrieve adapter | `MockPlaceRetriever`, `GooglePlacesRetriever` | ドメイン別 source |
| Normalizer | `restaurant_normalizer.py` | ドメイン別変換ルール |
| Query understanding | `infer_search_conditions.py` | ドメイン別条件抽出 |
| Solution Catalog | `restaurant_solution_catalog.json` | ドメイン別 vocabulary |
| Mock data | `place_searcher._MOCK_PLACES` | ドメイン別テストデータ |

## ドメインごとに何が切り替わるか

| 項目 | Restaurant | Clinic | Legal |
|---|---|---|---|
| **problem_type** | `local.restaurant` | `local.clinic` | `professional.legal` |
| **axes 例** | cuisine, budget, atmosphere, location | specialty_fit, urgency, distance, hours, insurance | issue_fit, jurisdiction, fee_structure, responsiveness |
| **hard constraint 例** | 予算上限、エリア | 保険適用、専門科 | 管轄地域、取扱分野 |
| **soft preference 例** | 雰囲気、ジャンル | 待ち時間、口コミ | 費用感、対応速度 |
| **candidate source** | Google Places | clinic directory, 医療 DB | 弁護士名簿 |
| **normalizer** | place → restaurant attributes | listing → care attributes | profile → legal service attributes |
| **catalog patterns** | quiet_conversation, budget_dinner | chronic_care, emergency | contract_dispute, family_law |

**注意: Clinic と Legal は拡張イメージであり、現時点では未実装。**

## 現状の限界

- **restaurant のみ実装済み** — 他ドメインの adapter / normalizer / catalog は存在しない
- **axes は LLM 依存** — ドメイン別の axis 品質保証はプロンプト設計に依存
- **adapter registry なし** — ドメイン切り替えはコード上の手動指定
- **normalizer は restaurant 専用** — Google Places / mock の両方とも restaurant のみ
- **catalog vocabulary 未標準化** — problem_pattern は手書き、taxonomy なし
- **高リスクペナルティは evaluator に埋め込み** — clinic / legal で自動適用されるが、ドメイン別チューニングは未実装

## 将来の拡張ポイント

1. **DomainProfile / ProblemTypeSpec** — ドメインごとの axes 候補、hard/soft の意味定義を構造化
2. **Adapter registry** — `domain → (searcher, retriever, normalizer)` の登録・切り替え機構
3. **Normalizer registry** — ドメイン別 raw → candidate 変換ルールの差し替え
4. **Solution Catalog taxonomy** — ドメイン別の problem_pattern 語彙を定義
5. **Candidate source abstraction** — Google Places 以外の source (医療 DB、弁護士名簿等) への対応
6. **Domain-specific prompt tuning** — ドメイン別の score gradient / axis 例をプロンプトに注入
