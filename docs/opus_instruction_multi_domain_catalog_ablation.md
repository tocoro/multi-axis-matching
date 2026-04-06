# Opus 実装指示書: multi-domain solution catalog ablation comparison

この指示書に従って、restaurant / clinic の両ドメインで **solution catalog の有無を比較する multi-domain ablation** を追加してください。

## 背景
現状の repo では、次が揃っています。

- 共通 evaluator / aggregation カーネル
- restaurant / clinic の 2 ドメイン
- DomainProfile / AdapterBinding
- restaurant / clinic の solution catalog
- catalog usage contract
- restaurant 側の ablation 基盤
- live ablation protocol

ここまで来たので、次は
**catalog の寄与を restaurant だけでなく clinic でも同じ形式で比較する**
段階です。

目的は、solution catalog が
- ある特定ドメイン専用の偶然ではなく
- 候補側意味記述として複数ドメインで補助的に働く

ことを repo 上で観測できるようにすることです。

---

## 目的
次の6点を実現してください。

1. restaurant / clinic の両方で catalog on/off 比較を走らせる
2. 同じ diff summary 形式で比較できるようにする
3. reason / confidence / unknown / ranking の差をドメイン横断で見られるようにする
4. catalog の寄与を過大に演出しない
5. 既存 single-domain ablation を壊さない
6. docs / examples に見方を残す

---

## スコープ
### 対象
- multi-domain comparison helper / script / tests
- restaurant と clinic の両方を比較する出力構造
- docs / examples の追加または更新

### 非対象
- live LLM の大量ベンチマーク
- 統計検定
- evaluator ロジック変更
- catalog score 直結
- 3ドメイン目追加

---

## 今回の対象ファイル
主な対象:
- `src/experiments/multi_domain_catalog_ablation.py`
- 必要なら `scripts/compare_multi_domain_catalog_ablation.py`
- `tests/test_multi_domain_catalog_ablation.py`
- 必要なら `examples/multi_domain_catalog_ablation_expected.json`
- 必要なら `docs/solution_catalog_live_ablation_protocol.md`
- 必要なら `README.md`

repo 構成に合わせて調整してよいです。

---

## 1. 比較対象
少なくとも次の 2 ドメインを対象にしてください。

### restaurant
- 既存 restaurant ablation をベースにする

### clinic
- clinic catalog on/off 比較を追加する

重要:
- まずは mocked / deterministic 比較でよい
- live 実験は protocol の対象であり、今回は必須ではない

---

## 2. 共通の比較出力形式
restaurant と clinic で、できるだけ同じ output shape にしてください。

推奨例:
```json
{
  "domain": "clinic",
  "query": "仕事帰りに行ける内科。保険適用がよい",
  "with_catalog": {...},
  "without_catalog": {...},
  "diff_summary": {
    "ranking_changed": false,
    "score_changes": {...},
    "confidence_changes": {...},
    "reason_changes": {...},
    "unknown_changes": {...}
  }
}
```

さらに multi-domain 全体としては、例えば
```json
{
  "restaurant": {...},
  "clinic": {...}
}
```
または
```json
{
  "runs": [
    {"domain": "restaurant", ...},
    {"domain": "clinic", ...}
  ]
}
```
のどちらかでよいです。

重要なのは、**ドメインをまたいでも同じ観点で読めること**です。

---

## 3. clinic ablation の設計
clinic 側でも、catalog の有無で以下のどれかに差が出るようにしてください。

### 観測したい差
- reason が catalog を参照する形に変わる
- confidence が少し変わる
- score が微差で変わる
- unknown は必要以上に減らない
- ranking は変わっても変わらなくてもよい

### 例
- `clinic_1` は `after_work_visit` や `insurance_covered_visit` により reason / confidence が少し補強される
- `clinic_2` は `not_for_after_work`, `no_same_day` が conflict reason を補強する
- `clinic_4` は catalog があっても unknown を解消しない

restaurant と同じく、**差は小さくてよい**です。

---

## 4. mocked evaluator / mock server の扱い
必要なら restaurant 側と同じく deterministic な mocked evaluator を使ってよいです。

ただし守ること:
- catalog ありで大きく score を跳ね上げない
- unknown を魔法のように消さない
- limitation を即 disqualify にしない
- ranking 不変でも失敗にしない

目的は **寄与の観測** であり、勝たせることではありません。

---

## 5. 差分サマリー
最低限、各ドメインについて次を見られるようにしてください。

- ranking_changed
- score_changes
- confidence_changes
- reason_changes
- unknown_changes

さらに multi-domain 全体として、簡単な横断サマリーがあるとよいです。

例:
```json
{
  "cross_domain_summary": {
    "domains_compared": ["restaurant", "clinic"],
    "reason_changed_domains": ["restaurant", "clinic"],
    "unknown_reduced_domains": [],
    "ranking_changed_domains": []
  }
}
```

厳密にこの形でなくてよいですが、
**どのドメインで何が変わったかがすぐ分かること**が望ましいです。

---

## 6. テスト要求
最低限、以下を追加してください。

### A. output shape
- multi-domain の結果に restaurant / clinic の両方がある
- 各ドメインに with_catalog / without_catalog / diff_summary がある

### B. restaurant backward compatibility
- 既存 restaurant ablation を壊さない

### C. clinic catalog effect
- clinic で reason または confidence が変化する

### D. no overclaim
- clinic でも unknown が不当に減らない
- limitation が即 disqualify を増やさない

### E. deterministic
- 同じ入力で同じ multi-domain 結果になる

---

## 7. docs / examples
必要なら docs に短く書いてください。

書きたいこと:
- catalog の寄与比較は restaurant 専用ではなく clinic にも拡張された
- ranking 不変でも reason / confidence の変化は有意味
- domain によって catalog の効き方は異なりうる
- unknown が不変でも正常

---

## 8. 実装上の注意
- multi-domain だが最小実装に留める
- 共通 comparison shape を優先する
- ドメインごとの差を消しすぎない
- clinic を restaurant のコピーにしない
- mocked comparison を live の証明と混同しない

---

## 9. 成功条件
- restaurant / clinic の両方で catalog on/off 比較が走る
- 共通の diff summary 形式で出せる
- clinic 側でも寄与が観測できる
- no overclaim 原則が保たれる
- 既存 tests を壊さない

---

## 10. 今回やらないこと
- live multi-domain benchmark の自動化
- 3ドメイン目の追加
- catalog score の直接数値化
- provider authoring UI
- generic routing 完成

---

## 最後に出してほしいもの
1. 追加ファイル一覧
2. multi-domain 比較の出力形式要約
3. restaurant / clinic で何が変わるようにしたか
4. cross-domain summary の要約
5. 追加したテスト
