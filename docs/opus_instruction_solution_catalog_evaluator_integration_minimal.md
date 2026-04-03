# Opus 実装指示書: Solution Catalog を evaluator 入力へ最小接続

この指示書に従って、Solution Catalog prototype を **evaluator 入力へ最小限だけ接続**してください。

## 背景
現状の repo には以下があります。
- user problem structuring
- candidate collection
- normalization
- multi-axis evaluation
- Google Places integration
- Solution Catalog prototype

ただし Solution Catalog はまだ docs / schema / sample / tests の層に留まっており、
実際の評価パイプラインでは使われていません。

次の自然な段階は、
**candidate_id に応じて Solution Catalog を引き、evaluator に optional context として渡すこと**です。

今回は minimal integration に留めてください。

---

## 目的
次の4点を実現してください。

1. candidate_id から Solution Catalog entry を引けるようにする
2. evaluator の入力に optional な `solution_catalog` context を追加する
3. catalog が無い場合でも従来どおり動くようにする
4. まだ評価ロジック全体を catalog 依存にはしない

---

## スコープ
### 対象
- catalog loader / lookup の追加
- pipeline で candidate_id に対応する catalog entry を添付
- evaluator request / prompt へ optional field を追加
- テスト追加
- 必要なら docs 更新

### 非対象
- catalog を必須化すること
- score aggregation の変更
- hard constraint 判定の全面変更
- catalog 自動生成
- UI 編集機能
- cross-domain 展開

---

## 今回の対象ファイル
主な対象:
- `src/pipeline/restaurant_pipeline.py`
- `src/evaluator/` 配下の request building / prompt rendering コード
- 必要なら `src/contracts/` や `src/catalog/` 配下の loader
- `tests/test_evaluator.py`
- `tests/test_restaurant_pipeline.py`
- 必要なら `README.md`
- 必要なら `docs/solution_catalog_proto.md`

実際の repo 構成に合わせて調整してよいです。

---

## 1. catalog loader / lookup を追加
まず、sample catalog を読む薄い層を追加してください。

推奨:
- `load_solution_catalog(path: str | Path) -> dict[str, dict]`
- `get_solution_catalog_entry(candidate_id: str) -> dict | None`

要件:
- まずは `examples/restaurant_solution_catalog.json` を読むだけでよい
- candidate_id を key に引けるようにする
- entry が無ければ `None` を返す
- schema validation を毎回 runtime でやる必要はない。テストで担保済みなら可

---

## 2. pipeline で candidate に catalog を紐付ける
restaurant pipeline で、normalized candidate を作る段階か evaluate 用 request を作る段階で、
対応する catalog entry があれば添付してください。

### 例
candidate object 自体に直接入れてもよいし、evaluate request 用の別フィールドでもよいです。

推奨例:
```json
{
  "candidate_id": "place_1",
  "title": "Trattoria A",
  "description": "...",
  "structured_attributes": {...},
  "solution_catalog": {
    "solution_claims": [...],
    "hard_limitations": [...],
    "evidence": {...}
  }
}
```

または evaluator request 側で
```json
{
  "candidate": {...},
  "solution_catalog": {...}
}
```
でもよいです。

重要なのは、**既存 schema を壊さず optional に足すこと**です。

---

## 3. evaluator prompt に optional context を追加
評価 prompt に、Solution Catalog がある場合のみそれを参照してよいことを追加してください。

### 重要な方針
- catalog は補助情報である
- raw candidate / structured_attributes を置き換えない
- catalog が無ければ従来どおり評価する
- catalog を絶対視しない
- catalog に書いてないことを hard violation とみなさない

### prompt に追加したい趣旨
- `solution_claims` は、その候補がどんな問題パターンに向くと整理されているかの補助情報
- `hard_limitations` は、明示的に不向きとされている問題パターンの補助情報
- ただし catalog は補助であり、他の candidate data と矛盾する場合は理由を見ながら慎重に扱う
- catalog が無い場合は通常どおり評価する

---

## 4. まだやりすぎないこと
今回は minimal integration なので、次はやらないでください。

- catalog claim を自動で score 化する
- claim の strength を直接 numeric score に変換する
- hard_limitations を自動 disqualify に直結する
- problem_pattern taxonomy を大規模拡張する

今回は、**LLM が補助コンテキストとして読める状態を作るだけ**で十分です。

---

## 5. 不明と limitation を混同しない修正
前段の prototype で見えた注意点として、
「不明」を hard limitation に入れない原則を docs か sample に反映してください。

特に `late_night_dining` のように、
根拠が「営業時間情報が無い」だけなら、hard limitation ではなく未記載にするほうがよいです。

要件:
- sample catalog を必要なら修正する
- docs に「不明は limitation にしない」と一言書く

---

## 6. テスト要求
最低限、以下を追加してください。

### A. catalog lookup test
- candidate_id で正しい entry が取れる
- 無い ID は `None`

### B. pipeline attaches catalog
- mock candidate `place_1` などに catalog が添付される
- catalog の無い候補では落ちずに動く

### C. evaluator request / prompt test
- catalog があるとき prompt / request に含まれる
- catalog が無いときも従来どおり動く

### D. backward compatibility
- 既存 mock path を壊さない
- Google path を壊さない

### E. prototype correction
- 不明を hard limitation にしない修正が反映される

---

## 7. 実装上の注意
- optional field として追加する
- 既存 schema が strict なら、外側 request で保持するなど工夫する
- catalog を truth source にしない
- evidence を見える形で残してよい
- minimal integration に留める

---

## 8. 成功条件
- candidate_id → solution catalog lookup ができる
- evaluator に optional context として渡せる
- catalog 無しでも従来動作する
- 「不明」を limitation にしない原則が反映される
- テストが通る

---

## 9. 今回やらないこと
- catalog 主導の scoring rewrite
- claim strength の定量化
- automatic disqualification
- auto catalog generation
- provider portal
- cross-domain catalog

---

## 最後に出してほしいもの
1. 変更ファイル一覧
2. catalog をどこで lookup してどこで evaluator に渡したか
3. prompt に追加した catalog の扱い方の要約
4. 不明と limitation の区別についての修正内容
5. 追加テスト内容
