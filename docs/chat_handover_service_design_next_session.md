# 次チャット引き継ぎメモ（サービス設計移行）

この文書は、`multi-axis-matching` の**デモ UI 改修フェーズから、実用サービス設計フェーズへ移る**ための引き継ぎです。

対象時点:
- 最新確認コミット: `1cf20dc`
- テスト数: **540 passing**

---

## 1. このチャット時点の結論
この repo では、デモ UI と比較導線の整備は十分に進んだ。
次チャットでは、**デモ強化の続きではなく、実用ユースケースのサービス設計に移る**のが自然である。

この判断の理由:
- restaurant / clinic の 2 ドメイン実装がある
- solution catalog on/off の Compare がある
- unknown を残す設計がある
- review / gate / summary の基盤がある
- Web UI 上で、比較結果をプレゼン可能なところまで読める
- candidate 単位の差分導線まである

したがって、現時点で「どうしても先に片付けるべき UI 残作業」は**特にない**。

---

## 2. repo の現在地
現状を最も正確に言うと、この repo は:

**multi-axis evaluator の共通カーネルに、restaurant / clinic の 2 ドメイン、2 ドメイン catalog、ablation 基盤、比較 UI を載せた prototype**

である。

### すでに成立しているもの
- 共通 evaluator / aggregation / ranking / explanation
- unknown / conflict / hard violation の分離
- restaurant ドメイン
- clinic ドメイン
- DomainProfile / adapter binding 的な境界
- restaurant / clinic の solution catalog
- catalog usage contract
- single-domain / multi-domain ablation 基盤
- live ablation protocol
- Web UI 上の compare-first 導線
- scenario-driven demo UI
- candidate compare navigation
- candidate delta / changed-only filter / candidate focus
- compare history 導線（`1cf20dc` 到達点）

### まだやっていないこと
- 実サービスの対象ユースケース確定
- 実サービス用の入力 UX 設計
- 不足情報収集フロー
- 実データ投入戦略
- 運用フロー込みのサービス要件定義

---

## 3. 設計上の中核原則（次チャットでも維持）

### A. unknown を推測で埋めない
- 情報不足は unknown のまま扱う
- unknown は low score と同一視しない
- 「分からないことが分かる」こと自体が価値

### B. conflict と hard violation を分ける
- conflict は不一致・懸念
- hard violation だけを disqualify 根拠にする
- limitation があるだけで即失格にしない

### C. solution catalog は補助情報
- query / structured candidate data が先
- catalog は補強に使う
- catalog だけで truth を確定しない

### D. unknown と limitation を混同しない
- 情報欠如を limitation と呼ばない
- evidence-based limitation のみを limitation とする
- catalog 未記載は中立

### E. 過度な抽象化を急がない
- 毎回、最小導入で進めてきた
- いきなり full generic platform にしない
- 次のサービス設計でも、最初は 1 ユースケースに絞る方がよい

---

## 4. デモ UI の到達点
このチャットまでの UI 改修で、比較導線はかなり整った。

### プレゼン向けに成立している要素
- restaurant / clinic の preset groups
- clinic presets 3本
- `Start with Compare`
- `Why Compare matters`
- top-level diff highlights
- demo scenario cards 6本
- `Compare this scenario`
- `What to notice`
- domain filter tabs
- visible counts
- `Demo context`
- `Compare summary`
- `Changed candidates`
- `Quick jump`
- candidate compare anchors
- `Candidate compare index`
- per-candidate `Candidate delta`
- changed-only filter
- `Candidate focus`
- recent compare history / rerun / restore query

### 含意
- プレゼン用 UI としては、かなり十分
- これ以上の微修正より、**サービス本体の UX に頭を使う方が価値が高い**

---

## 5. 次チャットの主題
次チャットでは、次を主題にするのが自然。

## **実用ユースケースのサービス設計**

今回の方針として、すでにこのチャット中で合意できていること:
- デモ専用 UI の追加開発を続けるより、サービス構築に移る
- まず対象ユースケースを 1 つに固定する
- 実サービスでは、Compare UI よりも「推薦 + 不足情報表示 + 追加入力」の流れが重要

---

## 6. サービス設計で最初に決めるべきこと
次チャットでは、まず以下を詰めるべき。

### A. 誰の何の課題を扱うか
候補例:
- 事業課題 → ソリューション/施策候補の推薦
- 受診ニーズ → クリニック候補の推薦
- 支援策/制度 → 対象制度候補の推薦
- 業務課題 → SaaS / ベンダー / 外注先の推薦

この repo の強みと整合しやすいのは、
**説明責任があり、unknown を残す価値が高い領域**である。

### B. 候補データを何で持つか
- 現在の mock / catalog ベースをそのまま仮データにするか
- CSV / JSON / DB で本番候補データを持つか
- catalog と candidate structured data の責務をどう分けるか

### C. MVP の体験を何にするか
比較ではなく、まずは次の流れが候補。
1. ユーザー入力
2. 候補上位 3 件表示
3. 候補ごとの理由表示
4. 不足情報表示
5. 追加で聞くべき質問提示

### D. 何をデモ UI から再利用し、何を切り離すか
再利用しやすいもの:
- evaluator core
- domain profiles
- catalog contract
- candidate-level reason / unknown / confidence の表示ロジック

切り離した方がよいもの:
- compare-first のプレゼン導線
- scenario cards
- changed candidates / compare summary などの比較専用 UI

---

## 7. 次チャットで避けたい進め方
- いきなり汎用プラットフォーム設計に飛ぶこと
- 3 つ以上のユースケースを同時に追うこと
- provider / marketplace / ad system まで一気に拡張すること
- UI 先行で派手な見た目を増やすこと
- unknown を潰す方向で UX を作ること

---

## 8. 次チャットの自然な開始手順
おすすめの開始順:

1. この handover 文書を前提に repo の現在地を短く確認
2. サービス候補を 1 つに絞る
3. そのユースケースの MVP 体験を定義
4. 必要データと既存資産の再利用方針を決める
5. その後で OPUS 向け実装指示書に落とす

---

## 9. 次チャットの開始文の例
例えば次のように始めると継続しやすい。

> `docs/chat_handover_service_design_next_session.md` を前提に、現状の repo を短く確認したうえで、実用サービスとして最初に狙うユースケースを一緒に決めてください。

または

> `docs/chat_handover_service_design_next_session.md` を前提に、この repo を土台にした MVP サービスの要件を定義してください。

---

## 10. 現時点の一言要約
この repo は、**比較実験と説明可能性のデモ基盤としては十分整った**。
次にやるべきことは、**その評価カーネルを使って、1 つの実用ユースケースに絞ったサービスを設計すること**である。
