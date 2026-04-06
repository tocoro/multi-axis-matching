# OPUS Implementation Brief

この文書は、次の実コーディングを行う OPUS 向けの実装指示書です。

## 目的
このリポジトリの目的は、広告システムを作ることではなく、**問題記述と候補解決策の高品質なマッチング評価**を行うことです。

評価器として重視するのは次です。
- 問題記述の構造化
- 候補解決策の比較可能な正規化
- 問題タイプ依存の評価軸選択
- unknown を無理に埋めないこと
- 理由付きランキング
- 高リスク領域での保守性
- 複数ドメインへの再利用性

## 現在の到達点
現状の repo は、次の状態にあります。

- 共通 multi-axis evaluator カーネルがある
- restaurant / clinic の 2 ドメインで再利用されている
- DomainProfile / AdapterBinding がある
- solution catalog は 2 ドメインで成立している
- catalog usage contract が固定されている
- single-domain ablation がある
- multi-domain ablation は commit `09e090d` で完了済み
- cross-domain summary で domain ごとの差分を把握できる
- live ablation protocol と script がある

現在の repo の正確な位置づけは、
**multi-axis evaluator の共通カーネルに、2ドメイン実装・2ドメイン catalog・single/multi-domain ablation を載せた prototype**
である。

## 設計原則
以下を壊さないこと。

1. 候補生成と候補評価を分離する
2. evaluator の共通カーネルを優先し、ドメイン固有処理を中に埋め込まない
3. unknown は low score と同一視しない
4. conflict は hard violation と同一視しない
5. high-risk domain では保守的に扱う
6. catalog は supplementary context であり truth source ではない
7. no overclaim を守る

## catalog に関する不変条件
特に以下は守ること。

- catalog は reason や score に影響してよい
- catalog によって unknown を magically 解消したように見せてはならない
- ranking を無理に変えにいってはならない
- limitation は evidence-based である必要がある
- missing / unknown 情報を limitation に変換しない
- clinic_4 のような情報欠落候補は、catalog があっても untouched でありうる

## `run_multi_domain_ablation()` に関する注意
現在は catalog off を
`catalog_path="/nonexistent/__no_catalog__.json"`
で表現している。

これは現時点では十分に簡潔であり、**今は抽象化しないこと**。
将来的に pipeline ごとの catalog 無効化方法が分かれる可能性はあるが、現時点で先回りして abstraction を増やさない。

## OPUS が次に着手すべき自然な論点
最も自然な次段階は **live 実験結果のレビューと、それを支える最小限の改善** である。

見るべき観点は次。
- reason がどう変わるか
- confidence がどう動くか
- ranking が不自然に崩れないか
- unknown がちゃんと残るか
- catalog による change が過剰主張になっていないか

## 実装優先順位
次の順で進めること。

### A. live 実験の読みやすさ向上
優先度: 高

目的:
- live ablation の結果を human review しやすくする

候補:
- diff summary の可読性改善
- reason / score / confidence / unknown の変化の整理表示
- domain ごとの差分要約の改善

制約:
- evaluator の意味論を変えない
- score aggregation の契約を変えない
- unknown の扱いを変えない

### B. 理由品質の改善
優先度: 高

目的:
- reason が「なぜその候補が合う / 合わないか」をより検証可能な形で表現する

候補:
- evaluate_candidate prompt の理由表現の改善
- catalog reason と organic reason の混同防止
- limitation reason の説明明確化

制約:
- overclaim しない
- catalog があるからといって事実認定を強めない
- unsupported な断定を増やさない

### C. ドメイン横断の一貫性改善
優先度: 中

目的:
- restaurant / clinic で比較可能な summary を維持する

候補:
- cross-domain summary の項目整理
- diff schema の小改善
- response 内 field naming の整合確認

制約:
- restaurant backward compatibility を壊さない
- 既存 single-domain ablation を壊さない

### D. 将来拡張のための整理
優先度: 低

目的:
- 3ドメイン目以降の追加がしやすい状態を維持する

候補:
- binding / profile / pipeline の責務整理
- catalog attach 部分の共通化余地の確認

制約:
- 今は abstraction のための abstraction をしない
- 変更コストに対して明確な利得がない場合は手を出さない

## やってはいけないこと
- 広告配信システム方向へ話を戻すこと
- CTR / impression 的な発想を evaluator の中心に持ち込むこと
- unknown を解消したことに見せること
- catalog に ranking 改変の役割を持たせること
- high-risk domain で aggressive な最適化をすること
- clinic 実装を本格医療検索であるかのように拡張主張すること
- 先回りした大規模 abstraction を入れること

## 実装時の期待値
OPUS は次の姿勢で実装すること。

- 小さく、検証可能な差分を作る
- 各変更に対応するテストを必ず追加・更新する
- backward compatibility を確認する
- no overclaim を最優先する
- mock と live の両方で解釈しやすい出力を意識する

## 成功条件
次の状態になれば成功。

- live 実験結果を見たとき、catalog の効果を過不足なく読める
- reason の変化が説明可能
- confidence の動きが不自然でない
- unknown が不自然に減っていない
- restaurant / clinic の両方で同じ読み方ができる
- 既存テスト群が維持される

## 一言でいう現在の開発方針
**広告ではなく、問題と解決策の高品質なマッチング評価器として磨くこと。**
