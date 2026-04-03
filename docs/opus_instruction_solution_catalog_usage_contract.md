# Opus 実装指示書: Solution Catalog の利用規約を明文化する

この指示書に従って、Solution Catalog を evaluator に渡したときに、**どのように参照してよいか**の利用規約を prompt / docs / tests で明文化してください。

## 背景
現状の repo では、Solution Catalog はすでに evaluator に optional context として渡されています。

ただし現時点では、規約としては主に次のレベルに留まっています。
- 補助情報として参照してよい
- truth source にしない
- catalog が無くても動く
- 未記載を hard violation とみなさない

ここから一歩進めて、
**Solution Catalog を軸評価にどう効かせてよいか / いけないか**
をもう少し具体的に定義してください。

今回は scoring の大改造ではなく、**利用契約の明文化**が目的です。

---

## 目的
次の4点を実現してください。

1. `solution_claims` を評価にどう使ってよいかを具体化する
2. `hard_limitations` を評価にどう反映してよいかを具体化する
3. raw candidate / structured attributes / solution catalog の優先関係を明記する
4. prompt / docs / tests でこの契約を固定する

---

## スコープ
### 対象
- `prompts/evaluate_candidate.txt`
- 必要なら evaluator docs
- 必要なら `docs/solution_catalog_proto.md`
- テスト追加または更新

### 非対象
- aggregate score の変更
- catalog claim の自動数値化
- hard limitation の自動 disqualify 実装
- catalog 自動生成
- UI 変更

---

## 1. priority / precedence を明文化する
prompt と docs に、少なくとも以下の優先関係を明記してください。

### 優先関係
1. user query / inferred constraints
2. candidate の raw / structured data
3. solution catalog

つまり、catalog は有用だが、candidate data より上位ではないことを明記してください。

### 具体的に書きたいこと
- catalog は補助的な semantic summary である
- candidate の属性データや source evidence と矛盾する場合は、catalog を盲信しない
- evidence の薄い catalog 記述だけで極端な判断をしない

---

## 2. `solution_claims` の使い方を定義
`solution_claims` は、候補の得意領域を示す補助情報です。

これをどう使ってよいかを具体的に書いてください。

### 許可する使い方
- axis reason を補強する
- supported / partial support の判断補助に使う
- 情報が薄いが claim と candidate data が整合する場合、confidence を少し支える材料にしてよい

### 禁止または抑制する使い方
- claim があるだけで高得点を確定しない
- claim を raw evidence なしに hard support とみなさない
- claim の強度 (`strong`, `medium`, `weak`) を機械的に score へ直結しない

### 例
- `quiet_conversation` claim があり、candidate data も quiet 系なら atmosphere 軸 reason の補助にしてよい
- claim だけあって raw data が乏しい場合は、support の補助にはしてよいが過信しない

---

## 3. `hard_limitations` の使い方を定義
`hard_limitations` は、明示的に不向きな問題パターンの補助情報です。

### 許可する使い方
- conflict reason の補助に使う
- 明らかに problem_pattern が一致し、candidate data とも整合する場合、不向き判断の補助にしてよい

### 禁止または抑制する使い方
- limitation があるだけで即 disqualify しない
- limitation を hard constraint violation に自動変換しない
- user query と対応しない limitation を無理に持ち込まない

### 例
- `large_group_banquet` limitation があり、ユーザーが宴会店を求めているなら conflict reasoning に使ってよい
- ただし user query が少人数会食なら、その limitation を無関係な軸に持ち込まない

---

## 4. unknown と catalog を混同しない
prompt に、次をはっきり書いてください。

- catalog があることは unknown を自動的に解消しない
- claim があっても、軸に必要な具体情報が足りなければ unknown は残りうる
- limitation がないことは「問題なし」の証拠ではない
- catalog 未記載は否定でも肯定でもない

これは重要です。

---

## 5. reason の書き方に反映する
軸別 reason で catalog を使う場合、どの程度まで言ってよいかを定義してください。

推奨:
- 「solution catalog でも quiet_conversation 向きと整理されており、候補説明とも整合する」
- 「solution catalog に banquet 不向きの記述があり、ユーザーの宴会用途とはずれる」

避けたい:
- 「catalog にあるので完全に一致」
- 「catalog に limitation があるので失格」

つまり、**reason の根拠補強として使う**という位置づけを明確にしてください。

---

## 6. docs に短い利用契約を追加
必要なら docs に短いメモを追加してください。

推奨例:
- `docs/solution_catalog_usage_contract.md`

書く内容:
- precedence
- allowed uses
- disallowed uses
- unknown handling
- example reasoning

長文化は不要です。短く明確にしてください。

---

## 7. テスト要求
最低限、以下のどれかを追加または更新してください。

### A. prompt contract test
- prompt に precedence / allowed uses / disallowed uses / unknown rules が入っていること

### B. evaluator contract test
- `solution_claims` を高得点確定に直結しない文言がある
- `hard_limitations` を即 disqualify に直結しない文言がある
- catalog 未記載を否定とみなさない文言がある

### C. docs presence test は不要
ただし docs を追加したら簡単な存在確認でも可

今回は live の挙動統計までは不要です。

---

## 8. 実装上の注意
- 今回は契約の明文化に留める
- evaluator 出力 schema は変えない
- catalog の value を numeric score にマッピングしない
- hard / conflict / unknown の既存設計を壊さない
- 文言は曖昧すぎず、過剰に自動化しない

---

## 9. 成功条件
- prompt に catalog 利用規約が追加される
- precedence が明文化される
- claim / limitation の allowed / disallowed uses が明記される
- unknown handling が明確になる
- テストで契約が固定される

---

## 10. 今回やらないこと
- catalog 直接 scoring
- automatic disqualification
- claim strength の数値化
- evaluator 出力の新フィールド追加
- provider authoring UI

---

## 最後に出してほしいもの
1. 変更ファイル一覧
2. precedence の要約
3. claim / limitation の allowed / disallowed use 要約
4. unknown handling の要約
5. 追加 / 更新したテスト
