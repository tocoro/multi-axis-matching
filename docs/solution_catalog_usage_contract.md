# Solution Catalog 利用規約

## Precedence (優先関係)

1. **user query / inferred constraints** — 最優先
2. **candidate raw / structured data** — 主要な判断根拠
3. **solution catalog** — 補助情報

catalog は candidate data を置き換えない。矛盾時は candidate data を優先。

## solution_claims の使い方

### 許可
- axis reason の根拠補強
- supported / partial support の判断補助
- claim と candidate data が整合する場合の confidence 支援

### 禁止
- claim だけで高得点を確定
- raw evidence なしに hard support とみなす
- strength (strong/medium/weak) を機械的に score へ直結

## hard_limitations の使い方

### 許可
- conflict reason の補助
- user query の問題パターンと一致し、candidate data とも整合する場合の不向き判断

### 禁止
- limitation だけで即 disqualify
- limitation を hard_constraint_violation に自動変換
- user query と無関係な limitation を持ち込む

## unknown handling

- catalog があっても unknown は自動解消しない
- claim があっても具体情報不足なら unknown は残る
- limitation がないことは「問題なし」の証拠ではない
- catalog 未記載は否定でも肯定でもない

## reason の書き方

推奨:
- 「solution catalog でも quiet_conversation 向きと整理されており、候補説明とも整合する」
- 「solution catalog に banquet 不向きの記述があり、ユーザーの宴会用途とはずれる」

避ける:
- 「catalog にあるので完全に一致」
- 「catalog に limitation があるので失格」
