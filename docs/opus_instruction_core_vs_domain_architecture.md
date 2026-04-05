# Opus 実装指示書: Core vs Domain Architecture を整理する設計文書

この指示書に従って、multi-axis-matching における **共通カーネル** と **ドメイン依存部分** の境界を整理する設計文書を追加してください。

## 背景
現状の repo は restaurant ドメインの実装が最も進んでいます。
そのため、実際には evaluator の枠組みが比較的共通であっても、外から見ると

- restaurant 専用システム
- 他ドメインへ拡張可能か不明
- 多軸評価が本当に対象ごとに切り替わるのか見えにくい

という状態になっています。

この曖昧さを解消するために、今回は実装追加ではなく、
**どこが共通カーネルで、どこが domain-specific adapter なのか**
を見える化する設計文書を作ってください。

---

## 目的
次の4点を実現してください。

1. evaluator の共通部分を明示する
2. ドメインごとに差し替わる部分を明示する
3. restaurant はその一実装例にすぎないことを示す
4. 将来 clinic / legal / product へ拡張する見取り図を示す

---

## スコープ
### 対象
- `docs/` に設計文書を追加
- 必要なら README にリンクを足す
- 必要なら簡単な ASCII 図や表を入れる

### 非対象
- 実コードの大規模リファクタ
- interface の全面変更
- clinic / legal / product の実装追加
- evaluator のロジック変更

---

## 今回の対象ファイル
主な対象:
- `docs/core_vs_domain_architecture.md`
- 必要なら `README.md`

---

## 1. 文書で明示したいこと
少なくとも次を整理してください。

### A. 共通カーネルとは何か
候補:
- user problem structuring の枠組み
- axis-based evaluation の枠組み
- unknown / conflict / hard violation の区別
- score aggregation
- ranking
- explanation / missing information の返し方

重要なのは、restaurant 固有の軸が固定で埋め込まれているのではなく、
**評価の枠組み自体が共通**であることが伝わることです。

### B. domain-specific とは何か
候補:
- search condition extraction
- candidate source adapters
- retriever
- normalizer
- solution catalog vocabulary
- domain examples / mock data

### C. 何が切り替わるのか
少なくとも次を明示してください。
- problem type
- axes
- hard/soft の意味
- candidate source
- normalization rules
- solution catalog patterns

---

## 2. 1枚で分かる図を入れる
ASCII で十分なので、少なくとも概念図を入れてください。

例の方向性:

```text
User Query
   ↓
Problem Structuring  ← (core)
   ↓
Candidate Collection ← (domain adapter)
   ↓
Normalization        ← (domain adapter)
   ↓
Multi-Axis Evaluation ← (core)
   ↓
Aggregation / Ranking ← (core)
   ↓
Explanation / Output  ← (core)
```

または、Core / Domain を2列に分けた表でもよいです。

目的は、**一目で境界が分かること**です。

---

## 3. ドメイン別の例を最小で入れる
最低限、次の3例を短く入れてください。

### Restaurant
- axes 例: cuisine, budget, atmosphere, location
- candidate source 例: Google Places
- normalizer 例: place → restaurant attributes

### Clinic
- axes 例: specialty_fit, urgency, distance, hours, insurance
- candidate source 例: clinic directory / map / medical DB
- normalizer 例: clinic listing → care-related attributes

### Legal / Product のどちらか1つ
例: Legal
- axes 例: issue_fit, jurisdiction, fee_structure, responsiveness
- candidate source 例: lawyer directory
- normalizer 例: profile → legal service attributes

ここでは実装済みである必要はなく、**拡張イメージ**として書けば十分です。

---

## 4. 「汎用」と言ってよい範囲を慎重に書く
ここが重要です。

文書では、過大に一般化しないでください。

書きたいこと:
- 現状は restaurant 実装が中心
- ただし evaluator の設計は domain-specific data を差し替えられる形を目指している
- まだ fully generic system ではない
- 現段階では「共通評価カーネル + restaurant adapter の1実装例」と表現するのが適切

避けたいこと:
- すでに多ドメイン対応済みであるかのような書き方
- 実装済みでない部分を確定口調で書くこと

---

## 5. 将来の拡張ポイントを短く示す
少なくとも以下を短く書いてください。

- DomainProfile / ProblemTypeSpec の明示化
- adapter registry
- domain-specific normalizer registry
- solution catalog taxonomy のドメイン別化
- candidate source abstraction

ただし、詳細設計に入りすぎなくてよいです。

---

## 6. README 更新は任意
必要なら README に 1 行だけリンクを足してよいです。

例:
- `See docs/core_vs_domain_architecture.md for the separation between the core evaluator and domain-specific adapters.`

---

## 7. テストは不要
今回は docs 追加が中心なので、テスト追加は不要です。
必要なら docs の存在確認程度は可ですが、原則不要です。

---

## 8. 実装上の注意
- 実装済みと将来構想を混同しない
- restaurant 依存の現状を隠さない
- それでも evaluator の共通性が伝わるように書く
- 1枚で読める程度に収める
- 長すぎる一般論にしない

---

## 9. 成功条件
- 共通カーネルとドメイン依存部分の境界が文書化される
- restaurant 以外への拡張イメージが見える
- 現状の限界も明記される
- 「汎用」と言ってよい範囲が慎重に整理される

---

## 10. 今回やらないこと
- clinic / legal / product の実装
- evaluator refactor
- adapter registry 実装
- taxonomy 実装
- UI 変更

---

## 最後に出してほしいもの
1. 追加したファイル一覧
2. core / domain の切り分け要約
3. ドメイン例の要約
4. 現状の限界の要約
5. 将来の拡張ポイントの要約
