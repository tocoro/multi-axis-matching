# Opus 実装指示書: Clinic を 2 ドメイン目として最小実装する

この指示書に従って、multi-axis-matching に **clinic の最小実装** を追加してください。

## 背景
現状の repo では restaurant 実装が最も進んでいます。
アーキテクチャ文書で「共通カーネル + domain adapter」の構造は整理されましたが、
まだ実際に動くドメインは restaurant しかありません。

そのため、現段階では
- 理屈上は汎用
- しかし実体は restaurant のみ

という状態です。

この状況を一歩進めるために、今回は **2 ドメイン目の超最小実装** として clinic を追加してください。

目的は本格医療検索ではなく、
**同じ evaluator / aggregation / explanation カーネルが別ドメインでも再利用できることを repo 上で示す**
ことです。

---

## 目的
次の5点を実現してください。

1. clinic ドメインの最小 pipeline を追加する
2. restaurant とは異なる axes で評価されることを示す
3. 既存 evaluator / aggregation を再利用する
4. mock データだけで deterministic に動くようにする
5. restaurant path を壊さない

---

## スコープ
### 対象
- clinic 用 mock searcher / retriever
- clinic 用 normalizer
- clinic 用 minimal pipeline
- clinic 用 sample solution catalog（任意だが推奨）
- tests
- 必要なら docs / README 更新

### 非対象
- 実 API 接続
- 医療の本格ドメイン設計
- 保険制度の詳細モデル化
- 医療助言機能
- live evaluation 大規模実験

---

## 今回の対象ファイル
主な対象:
- `src/pipeline/clinic_pipeline.py`
- `src/normalizers/clinic_normalizer.py`
- `src/mock/` 既存構成に合わせた clinic mock data
- 必要なら `examples/clinic_solution_catalog.json`
- `tests/test_clinic_pipeline.py`
- 必要なら `docs/core_vs_domain_architecture.md` か `README.md`

ファイル名は repo 構成に合わせて調整してよいです。

---

## 1. まずは mock-only でよい
clinic は今回は **mock-only** で十分です。

最低限必要なのは:
- searcher: 固定候補集合から返す
- retriever: source_id で詳細を返す
- normalizer: raw_record → clinic candidate
- pipeline: query → candidates → evaluate → ranking

restaurant と同じレベルの検索精度は不要です。

---

## 2. clinic で使う problem_type と axes
problem_type は以下でよいです。

- `local.clinic`

初期の axes 例は、少なくとも次の 4〜5 軸にしてください。

推奨:
- `specialty_fit`
- `distance`
- `hours`
- `insurance`
- `urgency_fit` または `availability`

重要なのは、restaurant と違う軸で動くことが見えることです。

---

## 3. query understanding は最小でよい
今回、query understanding は LLM に任せてもよいし、補助的な軽い抽出を入れてもよいです。
ただし restaurant の `infer_search_conditions` を無理に使い回さないでください。

最低限取りたいものの例:
- specialty / symptoms 由来の科目希望
- location
- open_now / evening / weekend などの時間希望
- insurance / 保険適用の希望

ただし今回は精密でなくてよいです。

---

## 4. clinic mock 候補
最低でも 3 件、できれば 4 件の候補を用意してください。

差が見えるようにしてください。

推奨例:
- `clinic_1`: 内科、駅近、夜まで、保険可
- `clinic_2`: 専門は近いが遠い、営業時間が短い
- `clinic_3`: 駅近だが専門不一致
- `clinic_4`: 情報不足が多い

目的は、
- supported
- conflict
- unknown
- hard violation ではない不一致

が見えることです。

---

## 5. normalizer は最小でよい
clinic normalizer では、最低限次のような structured attributes に落としてください。

例:
```json
{
  "candidate_id": "clinic_1",
  "title": "Ebisu Family Clinic",
  "description": "...",
  "structured_attributes": {
    "specialties": ["internal_medicine", "general_practice"],
    "location": "恵比寿",
    "hours_text": "平日 20時まで",
    "accepts_insurance": true,
    "same_day_available": true
  }
}
```

推測で埋めないでください。
不足は不足のままにしてください。

---

## 6. solution catalog は任意だがあるとよい
可能なら clinic 用にも最小 solution catalog を 2〜3 件だけ入れてください。

例:
- `chronic_care`
- `after_work_visit`
- `same_day_consultation`
- limitation: `no_pediatrics`

ただし、今回は必須ではありません。
**pipeline が動くことが優先**です。

---

## 7. clinic pipeline
`run_clinic_pipeline()` のような最小 pipeline を用意してください。

想定フロー:
1. query understanding / problem type inference
2. mock clinic search
3. mock clinic retrieve
4. clinic normalize
5. evaluate
6. ranking

restaurant pipeline を完全抽象化する必要はありません。
今回はまず **2つ目の実例** を作ることが目的です。

---

## 8. テスト要求
最低限、以下を追加してください。

### A. clinic pipeline が有効な response を返す
- schema に通る
- ranking が返る

### B. restaurant と違う軸が出る
- 少なくとも `specialty_fit` や `insurance` など、clinic らしい軸が含まれること
  （mock evaluator でも可）

### C. 情報不足候補で unknown が出る
- `clinic_4` のような候補で unknown が出ること

### D. specialty mismatch が conflict になる
- ただし hard violation に自動でしないなら、その仕様を明示的に固定する

### E. restaurant path を壊さない
- 既存 restaurant tests は通る

重要:
- 実 API テスト不要
- deterministic にする

---

## 9. docs 更新
必要なら docs に 1〜2 行だけ追記してください。

例:
- restaurant は 1 実装例だったが、clinic mock adapter も追加され、core 再利用の実例が増えた

ただし大きく書き換える必要はありません。

---

## 10. 実装上の注意
- 今回は demonstration としての 2 ドメイン目
- 本格医療システムのように見せない
- 医療助言をしているような文言を避ける
- evaluator の共通カーネルをなるべく再利用する
- restaurant 実装の複製に見えないよう、axes と候補属性を分ける

---

## 11. 成功条件
- clinic の最小 pipeline が動く
- restaurant と異なる axes で評価される
- 共通 evaluator / aggregation を再利用している
- tests が通る
- restaurant path を壊さない

---

## 12. 今回やらないこと
- 実 API 接続
- 保険制度の詳細化
- 症状 triage の高度化
- リアルな医療 recommendation
- multi-domain registry の本格実装

---

## 最後に出してほしいもの
1. 追加ファイル一覧
2. clinic pipeline の流れ
3. clinic で使った axes の一覧
4. mock 候補の要約
5. 追加したテスト
