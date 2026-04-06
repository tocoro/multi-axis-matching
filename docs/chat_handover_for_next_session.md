# 次チャット引き継ぎメモ

この文書は、`multi-axis-matching` の設計・レビューを次チャットで継続するための引き継ぎです。

## 1. プロジェクトの現在地
この repo は、単なる restaurant 専用検索ではなく、**共通 multi-axis evaluator カーネル**の上に **domain-specific adapters** を載せる構造を段階的に作ってきたものです。

現時点で成立している要素:
- 共通 evaluator / aggregation / ranking / explanation
- unknown / conflict / hard constraint violation の分離
- restaurant ドメイン
- clinic ドメイン（mock-only）
- DomainProfile / ProblemTypeSpec
- AdapterBinding registry
- solution catalog（restaurant / clinic の両方）
- evaluator への optional catalog context
- catalog usage contract
- single-domain ablation 基盤
- live ablation protocol
- core vs domain architecture docs

現時点の正確な表現:
- **fully generic system ではない**
- ただし **共通評価カーネル + 2つの domain adapter + 2 domain catalogs** まで実証済み

---

## 2. 設計上の中核原則
次チャットでも崩さないほうがよい原則:

### A. unknown を推測で埋めない
- 情報不足は unknown のまま扱う
- unknown は score の分母に混ぜない
- unknown は low score と同一視しない

### B. conflict と hard violation を分ける
- conflict は低スコア要因
- hard violation のみ disqualify 候補
- limitation があるだけで即 disqualify にしない

### C. solution catalog は補助情報
優先順位:
1. user query / inferred constraints
2. candidate raw / structured data
3. solution catalog

catalog は:
- reason の補強
- support / conflict の補助
- 軽い confidence 補助
には使ってよいが、
- truth source にしない
- claim だけで高得点確定しない
- limitation だけで失格にしない

### D. unknown と limitation を混同しない
- 情報が無いだけなら limitation にしない
- limitation は evidence-based に限る
- catalog 未記載は中立
- limitation 不在は「問題なし」の証拠ではない

### E. 過度な抽象化を避ける
ここまでの流れでは、毎回「最小導入」で進めている。
- いきなり full generic pipeline にしない
- registry / profile / docs を段階的に入れてきた
- mock で deterministic に比較できることを重視している

---

## 3. 実装・文書としてすでに追加済みの重要物
次チャットで参照しやすい主要ファイル群:

### 設計・指示書系
- `docs/core_vs_domain_architecture.md`
- `docs/solution_catalog_usage_contract.md`
- `docs/solution_catalog_live_ablation_protocol.md`
- `docs/opus_instruction_multi_domain_catalog_ablation.md`

### domain / registry 系
- `src/domain/profiles.py`
- `src/domain/registry.py` （または adapter registry 相当）

### pipeline 系
- `src/pipeline/restaurant_pipeline.py`
- `src/pipeline/clinic_pipeline.py`

### catalog 系
- `examples/restaurant_solution_catalog.json`
- `examples/clinic_solution_catalog.json`
- `src/catalog/loader.py`

### 実験系
- restaurant の ablation 実装
- live ablation script / protocol
- 次にやるべきもの: multi-domain catalog ablation

---

## 4. ここまでのレビュー要約
### すでに確認できたこと
- evaluator core は restaurant / clinic の両方で再利用できる
- 軸は domain に応じて切り替わる
- domain profile と adapter binding により、core と domain の境界がコード上でも見える
- solution catalog も restaurant 専用ではなく clinic に拡張できた
- catalog は optional supplementary context として扱う設計が固定されている

### まだ未解決 / 未実施のこと
- multi-domain catalog ablation の実装と観測
- live 比較の実行結果の蓄積
- generic dispatch の完成
- 3ドメイン目追加
- catalog 自動生成
- provider-side authoring
- downstream measurement（CV / ROAS 的なレイヤー）

---

## 5. 次チャットで最も自然な開始点
最優先候補はこれ:

## **multi-domain solution catalog ablation comparison**
目的:
- restaurant / clinic の両方で catalog on/off を同じフォーマットで比較する
- ranking / confidence / reason / unknown の差をドメイン横断で見る
- catalog が複数ドメインで補助的に働くことを観測する

対応する指示書:
- `docs/opus_instruction_multi_domain_catalog_ablation.md`

次チャットでは、まずこの指示書の実装コミットを確認する流れが自然です。

---

## 6. 次チャットでレビューする際の観点
multi-domain ablation のレビュー観点:

### A. 共通 output shape になっているか
- restaurant / clinic で同じ見方ができるか
- with_catalog / without_catalog / diff_summary が揃っているか

### B. catalog の寄与を過大に演出していないか
- score が不自然に跳ねていないか
- ranking を無理に変えていないか
- unknown を勝手に減らしていないか

### C. clinic が restaurant のコピーになっていないか
- clinic らしい reason / limitation の効き方になっているか
- after_work / insurance / specialty などが自然に出ているか

### D. no overclaim が守られているか
- limitation → 即 disqualify になっていないか
- claim → 即 support 確定になっていないか

---

## 7. 次チャット用の短い開始文
次チャットの冒頭で、この文脈を引き継ぎたい場合は、例えば以下のように始めるとよいです。

> `docs/chat_handover_for_next_session.md` を前提に、`docs/opus_instruction_multi_domain_catalog_ablation.md` の実装結果をレビューしてください。

または

> handover 文書を前提に、現在の repo の到達点を短く確認したうえで、次の実装の優先順位を判断してください。

---

## 8. 現在のトーン / 判断方針
このプロジェクトでは、次の方針で設計・レビューを進めてきました。

- 大きな一般論に逃げず、repo の現物に即して判断する
- 「できていること」と「まだできていないこと」を分ける
- 過大評価しない
- ただし設計上の前進は明確に認める
- いつも最も自然な next step を 1つに絞って提案する

この方針を維持すると継続しやすいです。

---

## 9. 現時点の一言要約
現状の repo は、

**multi-axis evaluator の共通カーネルに、restaurant / clinic の2ドメイン実装と2ドメイン solution catalog を載せた prototype**

と表現するのが最も正確です。
