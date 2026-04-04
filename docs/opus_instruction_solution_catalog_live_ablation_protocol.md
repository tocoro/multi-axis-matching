# Opus 実装指示書: Solution Catalog live ablation protocol

この指示書に従って、**live LLM を使って Solution Catalog の有無を比較観測するための実験プロトコル**を repo に追加してください。

## 背景
現状の repo には以下があります。
- Solution Catalog prototype
- evaluator への optional context 接続
- Solution Catalog usage contract
- mock ablation comparison
- server mock 側の可視差分

ここまでで、mock 条件では
- reason の変化
- score の微差
- unknown 不変
- ranking 不変または小差

を観測できるようになりました。

次に必要なのは、**実モデルで catalog on/off を比較する手順を整備すること**です。

今回は「本番品質評価」ではなく、
**live 実験を再現可能に行うための protocol / script / docs** を整えることが目的です。

---

## 目的
次の5点を実現してください。

1. 同一 query を catalog on/off で live 実行できる
2. 同一条件で結果比較を保存できる
3. 観測項目を固定する
4. 実験時の注意点を docs に明記する
5. 既存 mock / pipeline を壊さない

---

## スコープ
### 対象
- live 実験プロトコル文書
- 必要なら比較実行 script
- 結果保存形式の例
- 実験時の観測観点の整理

### 非対象
- live 実験の大量実施
- 統計解析の自動化
- UI 変更
- score aggregation の変更
- catalog 自動生成

---

## 今回の対象ファイル
主な対象:
- `docs/solution_catalog_live_ablation_protocol.md`
- 必要なら `scripts/run_solution_catalog_live_ablation.py`
- 必要なら `examples/solution_catalog_live_ablation_result_template.json`
- 必要なら `README.md`

repo 構成に合わせて調整してよいです。

---

## 1. protocol docs を作る
少なくとも docs に次を明記してください。

### A. 目的
- mock ではなく live モデルで catalog 寄与を観測する
- ranking だけでなく、reason / confidence / unknown の変化を見る

### B. 比較条件
- Condition A: catalog あり
- Condition B: catalog なし
- query は同一
- candidate source は同一
- model は同一
- temperature 相当の変動要因があれば固定する

### C. 観測項目
- ranking order
- total_score
- confidence
- axis reason
- missing_information / unknown
- disqualified

### D. 解釈上の注意
- ranking が変わらなくても失敗ではない
- reason と confidence だけ変わることは自然
- catalog が unknown を魔法のように解消しないのは正常
- 1回の出力だけで結論を出しすぎない

---

## 2. 実行スクリプトは任意だが推奨
可能なら、live 用の比較実行 script を追加してください。

推奨例:
- `scripts/run_solution_catalog_live_ablation.py`

### 要件
- query を1件受け取る
- model 名を受け取れる
- catalog on/off の2回を実行する
- 出力 JSON を保存できる
- 比較サマリーをコンソールに出せる

ただし今回は、複雑な CLI にしなくてよいです。

### 例
```bash
python scripts/run_solution_catalog_live_ablation.py \
  --query "恵比寿で静かに話せるイタリアン。予算は3000円以内" \
  --model gemini-2.5-flash \
  --out artifacts/live_ablation_case1.json
```

---

## 3. 出力形式を決める
live 実験結果は少なくとも次の形を持つようにしてください。

```json
{
  "query": "...",
  "model": "gemini-2.5-flash",
  "with_catalog": {...},
  "without_catalog": {...},
  "diff_summary": {...},
  "notes": {
    "run_purpose": "catalog live ablation",
    "interpretation_caution": "single run is not conclusive"
  }
}
```

厳密一致でなくてよいですが、
**mock ablation と似た見方ができること**が望ましいです。

---

## 4. 初期ケースを docs に書く
少なくとも 2ケース、最初に試す query を docs に書いてください。

推奨:

### Case 1
- quiet conversation 系
- 例: `恵比寿で静かに話せるイタリアン。予算は3000円以内`
- claim が reason 補強に効きやすい

### Case 2
- limitation が関わる系
- 例: `恵比寿周辺で会食したい。なるべく静かで少人数向け`
- location / limitation の補助が効くか見やすい

無理に多ケース化しなくてよいです。

---

## 5. 実験時の注意を docs で固定
必ず次を明記してください。

### A. live 出力は揺れる
- 同一モデルでも出力が多少ぶれる可能性がある
- 1回で断定しない

### B. mock と live は役割が違う
- mock は差分可視化のため
- live は実寄与の観測のため

### C. catalog の寄与を過大評価しない
- 少し reason が改善しただけでも有意な観測
- ranking 不変でも自然
- unknown 不変でも自然

### D. 実験ログは保存する
- query
- model
- timestamp
- catalog on/off の結果
- diff summary

---

## 6. テスト要求
今回は heavy な live test は不要です。
最低限、以下のどれかを追加してください。

### A. script argument parsing test
- query / model / out が受け取れる

### B. output template test
- 出力 JSON が必要 keys を持つ

### C. docs presence test は不要

live API を叩く自動 test は不要です。

---

## 7. 実装上の注意
- live 実験の protocol 化が目的
- 大量自動実行は不要
- モデル依存の結果を一般化しすぎない
- mock と live を混同しない
- repo に実験の残し方を用意する

---

## 8. 成功条件
- live ablation protocol docs が追加される
- 可能なら簡易実行 script が追加される
- 結果保存形式が定義される
- 観測項目と注意点が明文化される
- 既存 pipeline を壊さない

---

## 9. 今回やらないこと
- 統計検定
- ベンチマーク自動化
- multi-model dashboard
- catalog 自動生成
- provider authoring UI

---

## 最後に出してほしいもの
1. 追加ファイル一覧
2. live 実験の実行手順
3. 結果保存形式の要約
4. 初期ケース一覧
5. 観測できること / まだ観測できないこと
