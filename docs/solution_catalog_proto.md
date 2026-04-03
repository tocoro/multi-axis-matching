# Solution Catalog Prototype

## なぜ Solution Catalog が必要か

現状の候補表現は店舗属性 (名前, 住所, 価格, ジャンル) に留まっている。
これだと通常の parametric search との差は評価関数側にしかない。

Solution Catalog は、候補側が「どんな悩みをどの条件で解決できるか」を表現する層。
これにより、ユーザーの問題構造と候補の解決能力を直接マッチングできるようになる。

## 通常の店舗属性と何が違うか

| 店舗属性 | Solution Catalog |
|---|---|
| `genre: italian` | `claim: budget_italian, strength: strong, conditions: [lunch, dinner]` |
| `atmosphere: quiet` | `claim: quiet_conversation, strength: strong, conditions: [weekday_evening]` |
| `price: 2500` | (price は claim の根拠として evidence に入る) |

店舗属性は「何であるか」。Solution Catalog は「何ができるか / 何ができないか」。

## 構造

### solution_claims
候補が解決できる問題パターンの一覧。

- `problem_pattern`: 解決できる問題 (例: `quiet_conversation`, `budget_dinner`)
- `strength`: 適合の強さ (`strong` / `medium` / `weak`)
- `conditions`: claim が成立する条件 (例: `weekday_evening`, `small_group`)
- `reason`: claim の根拠

### hard_limitations
候補が明確に不向きな問題パターン。

- `problem_pattern`: 不向きな問題 (例: `large_group_party`, `late_night_dining`)
- `reason`: 不向きな理由

### evidence
claim / limitation の根拠データの出所。

- `source_type`: データの出所 (`mock`, `google_places`, `manual`)
- `source_fields`: 根拠に使った raw_record のフィールド名

## 重要な原則: 不明は limitation にしない

情報が無いだけのケースを hard_limitations に入れてはいけない。
例: 「営業時間が不明」は limitation ではなく、単に情報欠落。
limitation は「情報があり、明確に不向きだと判断できる場合」のみ記載する。

## 今回の位置づけ

- prototype: 手書きサンプル、restaurant 限定
- pipeline に直接組み込まない (疎結合)
- candidate_id は既存 mock データと一致させている
- 将来的に evaluator の入力として使う想定

## 将来の拡張

1. **LLM による自動生成**: raw_record + reviews → solution_claims 自動抽出
2. **Provider portal**: 飲食店自身が claims を編集
3. **Evaluator 統合**: claims を evaluator の入力に含め、ユーザーの問題構造と直接マッチング
4. **Cross-domain**: clinic, legal, product への展開
5. **Quality control**: claims の検証・フィードバックループ
