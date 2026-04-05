# Opus 実装指示書: clinic 用 minimal solution catalog prototype

この指示書に従って、multi-axis-matching に **clinic 用の最小 solution catalog prototype** を追加してください。

## 背景
現状の repo では、
- restaurant / clinic の 2 ドメインがある
- evaluator / aggregation は共通カーネルとして再利用されている
- DomainProfile と AdapterBinding registry も導入済み

ただし、solution catalog は実質的に restaurant 側でのみ使われています。
そのため、候補側の意味記述レイヤーが **多ドメインでも成立するか** はまだ弱い状態です。

このギャップを埋めるため、今回は **clinic 用の最小 solution catalog** を追加してください。

目的は本格的な医療知識体系ではなく、
**候補側意味記述もドメインをまたいで成立することを repo 上で示す** ことです。

---

## 目的
次の5点を実現してください。

1. clinic 候補に対応する minimal solution catalog を定義する
2. restaurant と同じ基本構造で clinic でも catalog が持てることを示す
3. unknown と limitation を混同しない原則を保つ
4. 必要なら evaluator に optional context として渡せる状態にする
5. restaurant path を壊さない

---

## スコープ
### 対象
- clinic 用 sample solution catalog の追加
- 必要なら schema / docs の確認または軽微更新
- 必要なら clinic pipeline で catalog を optional attach
- tests

### 非対象
- 医療知識ベースの本格設計
- 症状 triage
- 保険制度の詳細モデル化
- 実 LLM による大規模 live 比較
- provider authoring UI

---

## 今回の対象ファイル
主な対象:
- `examples/clinic_solution_catalog.json` または `data/clinic_solution_catalog.json`
- 必要なら `src/catalog/loader.py`
- 必要なら `src/pipeline/clinic_pipeline.py`
- `tests/test_clinic_solution_catalog.py`
- 必要なら `docs/solution_catalog_proto.md`

repo 構成に合わせて調整してよいです。

---

## 1. 基本方針
restaurant catalog と同じ思想を clinic にも適用してください。

### 持たせたい概念
- `candidate_id`
- `domain`
- `solution_claims`
- `hard_limitations`
- `evidence`
- `metadata`

ただし今回は **clinic 用の problem pattern 語彙** を使ってください。

---

## 2. clinic problem patterns の最小語彙
最小で十分です。3〜5 個程度に抑えてください。

推奨例:
- `after_work_visit`
- `same_day_consultation`
- `general_internal_medicine`
- `insurance_covered_visit`
- `family_medicine`

limitation 例:
- `no_pediatrics`
- `not_for_emergency`
- `not_for_specialized_cardiology`

重要:
- pattern 名は clinic 候補データと整合する範囲に留める
- 未知の高度な医療概念を増やしすぎない

---

## 3. mock clinic 候補に対応づける
既存の clinic mock 候補 (`clinic_1` など) に対応する catalog entry を 2〜4 件作ってください。

推奨:
- `clinic_1`: after_work_visit, general_internal_medicine, insurance_covered_visit
- `clinic_2`: specialty は合うが遠い、営業時間制約がある
- `clinic_3`: specialty mismatch を limitation として部分的に表現
- `clinic_4`: 情報不足が多いので claim を控えめにするか最小にする

目的は、
- clinic にも候補側意味記述が置ける
- unknown がそのまま残る
- limitation は evidence があるものだけにする

ことです。

---

## 4. unknown と limitation を混同しない
ここは restaurant と同じ原則を維持してください。

### 守ること
- 情報が無いだけなら `hard_limitations` に入れない
- limitation は evidence ベースで書く
- `claim` が無いことは否定ではない
- catalog 未記載は中立

例:
- 「救急対応情報が無い」→ limitation にしない
- 「小児科は扱っていないと明示」→ `no_pediatrics` limitation は可

---

## 5. clinic pipeline への接続は最小でよい
ここは段階を選べます。

### 最低限
- sample catalog が repo にある
- schema / tests が通る

### できれば
- clinic pipeline でも candidate_id に応じて catalog entry を optional attach する
- evaluator に optional context として渡せる

ただし、今回は **catalog の存在を示すことが優先** です。
既存 clinic pipeline を大きく崩さないでください。

---

## 6. schema の扱い
既存 solution catalog schema がそのまま使えるなら、それを流用してください。

もし restaurant 固有の説明が強すぎるなら、
- docs の文言だけ軽く一般化する
- schema 自体はそのまま使う

程度で十分です。

今回は schema rewrite を主目的にしません。

---

## 7. テスト要求
最低限、以下を追加してください。

### A. clinic catalog schema validation
- clinic sample entries が既存 schema を満たす

### B. content sanity
- `clinic_1` に 1 つ以上の solution claim がある
- `clinic_4` は claim が少ないか weak である
- evidence が空でない

### C. no unknown as limitation
- 不明ベースの limitation が無い

### D. optional pipeline attachment（実装した場合）
- clinic candidate に catalog が付く
- catalog が無くても pipeline は壊れない

### E. backward compatibility
- restaurant catalog tests を壊さない

---

## 8. docs 更新（任意）
必要なら短く追記してください。

書きたいこと:
- solution catalog は restaurant 専用ではなく、clinic にも適用できる最小実例を追加した
- ただし clinic catalog は prototype であり、本格医療知識体系ではない

---

## 9. 実装上の注意
- 最小 prototype に留める
- 医療助言のように見せない
- 候補側意味記述の例示に集中する
- unknown を消しすぎない
- limitation を過剰に書かない
- catalog を truth source にしない

---

## 10. 成功条件
- clinic 用 minimal solution catalog が追加される
- 既存 schema または同等構造で通る
- unknown と limitation の原則が守られる
- 可能なら clinic pipeline に optional attach される
- tests が通る

---

## 11. 今回やらないこと
- medical ontology の本格設計
- 症状 triage
- emergency routing
- live benchmark
- provider authoring UI

---

## 最後に出してほしいもの
1. 追加ファイル一覧
2. clinic problem pattern の一覧
3. 各 clinic 候補の claim / limitation 要約
4. pipeline に接続したかどうか
5. 追加したテスト
