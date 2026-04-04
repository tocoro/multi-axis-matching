# Solution Catalog Live Ablation Protocol

## 目的
mock ではなく live LLM で Solution Catalog の有無による評価差を観測する。
ranking だけでなく、reason / confidence / unknown の変化に注目する。

## 比較条件

| | Condition A | Condition B |
|---|---|---|
| catalog | あり | なし |
| query | 同一 | 同一 |
| candidate source | 同一 (mock or Google) | 同一 |
| model | 同一 | 同一 |

## 観測項目
- ranking order
- total_score
- confidence
- axis reason (catalog 参照の有無)
- missing_information / unknown count
- disqualified

## 初期ケース

### Case 1: quiet conversation
```
恵比寿で静かに話せるイタリアン。予算は3000円以内
```
claim が reason 補強に効きやすい。quiet_conversation claim の寄与を観測。

### Case 2: limitation が関わるケース
```
恵比寿周辺で会食したい。なるべく静かで少人数向け
```
location / limitation の補助効果を観測。

## 実行方法

```bash
python scripts/run_solution_catalog_live_ablation.py \
  --query "恵比寿で静かに話せるイタリアン。予算は3000円以内" \
  --model gemini-2.5-flash \
  --out artifacts/live_ablation_case1.json
```

## 結果保存形式
```json
{
  "query": "...",
  "model": "gemini-2.5-flash",
  "timestamp": "2026-04-05T...",
  "with_catalog": { ... },
  "without_catalog": { ... },
  "diff_summary": { ... },
  "notes": {
    "run_purpose": "catalog live ablation",
    "interpretation_caution": "single run is not conclusive"
  }
}
```

## 解釈上の注意

### live 出力は揺れる
同一モデルでも出力が多少ぶれる。1回で断定しない。

### mock と live は役割が違う
- mock: 差分構造の可視化・検証
- live: 実寄与の観測

### catalog の寄与を過大評価しない
- reason が少し改善しただけでも有意な観測
- ranking 不変でも自然
- unknown 不変でも自然 (catalog は unknown を魔法のように解消しない)

### 実験ログは保存する
- query, model, timestamp
- catalog on/off の結果
- diff summary
