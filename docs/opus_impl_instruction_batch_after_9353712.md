# OPUS 実装指示書（batch after 9353712）

## この文書の位置づけ
これは**複数タスクをまとめた実装指示書**です。
設計書ではありません。実装対象、変更ファイル、追加関数、追加テストを固定します。

対象コミット: `9353712`
このコミットで以下は完了済み。
- `/api/directory-summary`
- web UI summary panel
- manual-review-only filter
- refresh / status
- separate recommended / flagged lists
- fetched timestamp 表示
- 444 tests passing

したがって、今回の実装対象は **Web アプリとしてこのシステムの利点が一目で分かる導線を作ること** に限定します。

この指示書は 4 タスクで構成する。
- Task A: demo presets を追加
- Task B: Compare-first の value explainer を追加
- Task C: ablation diff の top-level highlight badges を追加
- Task D: web UI テストを追加

---

## 今回の目的
初見のユーザーやプレゼン相手が、通常の検索アプリではなく、
**「比較可能・理由付き・unknown を保持する multi-axis matching system」**
であることを UI からすぐ理解できるようにする。

今回の重点は、自然文の派手さではなく、次を見せること。
- 条件によって評価が変わる
- catalog on/off で reason / score が変わる
- unknown を無理に埋めない
- review gate まで含めて運用できる

新しい評価意味論は追加しない。
既存 API と既存レスポンスを再構成するだけにする。

---

## 変更してよいファイル
今回変更してよいのは次だけ。

- `static/index.html`
- `tests/test_web_summary_panel.py`
- 必要なら `docs/solution_catalog_live_ablation_protocol.md`

**それ以外は変更しないこと。**

---

## 変更してはいけないもの
- `server.py`
- `scripts/run_solution_catalog_live_ablation.py`
- `/api/pipeline` の schema
- `/api/ablation` の schema
- `_index_summary.json` の schema
- multi-domain ablation 系コード
- evaluator / prompt / catalog contract

---

# Task A: demo presets を追加

## 目的
手入力なしで、システムの違いが分かる代表ケースをすぐ再現できるようにする。

## 変更ファイル
- `static/index.html`

## 実装内容
検索カードの入力欄の下に preset buttons を追加する。

## 固定で追加する preset
1. `Quiet Italian`
   - `恵比寿で静かに話せるイタリアン。予算は3000円以内`
2. `Cheap but far`
   - `渋谷で安い和食。多少遠くてもよい`
3. `Information lacking`
   - `新宿で落ち着いて話せる店。情報が少なくても候補は見たい`

## 動作仕様
- ボタン押下で `#query` の値を preset に置き換える
- 送信は自動実行しない
- 既存 Search / Compare ボタンはそのまま
- 選択中 preset の視覚強調は不要。付けてもよいがテスト不要

## 注意
- preset 文言は固定
- random preset は追加しない
- live / strict / google places の状態は変更しない

## テスト追加
1. preset button が 3 つ存在する
2. `Quiet Italian` で query が置き換わる
3. `Cheap but far` で query が置き換わる
4. `Information lacking` で query が置き換わる

---

# Task B: Compare-first の value explainer を追加

## 目的
このシステムの見るべき点を UI 自体が説明するようにする。

## 変更ファイル
- `static/index.html`

## 実装内容
Search カードの下、summary panel の上に explanatory card を追加する。

## 固定タイトル
`Why Compare matters`

## 固定 bullet 4つ
- `Shows how catalog changes reasons, not just rankings`
- `Keeps unknowns instead of pretending certainty`
- `Separates conflicts from hard disqualification`
- `Supports review workflows with flagged runs and gate status`

## UI 制約
- 新しいデザインシステム導入はしない
- 既存 card スタイルを再利用してよい
- 折りたたみにはしない

## 注意
- free-form explanation は追加しない
- 文言は固定

## テスト追加
5. `Why Compare matters` が表示される
6. 4 bullet がすべて表示される

---

# Task C: ablation diff の top-level highlight badges を追加

## 目的
Compare 実行後、何が変わったかを最上部で一目で把握できるようにする。

## 変更ファイル
- `static/index.html`

## 変更対象
`runAblation()` 内の diff card 表示部分

## 追加する highlight block
diff card のタイトル直下に badges / chips 的な表示を追加する。

## 表示する項目
1. `ranking changed: yes/no`
2. `score changes: N`
3. `reason changes: N`
4. `unknown reduced: yes/no`
5. `confidence changes: N`

## 計算ルール
- `ranking changed`
  - `data.diff_summary.ranking_changed`
- `score changes: N`
  - `Object.keys(data.diff_summary.score_changes || {}).length`
- `reason changes: N`
  - `Object.keys(data.diff_summary.reason_changes || {}).length`
- `unknown reduced: yes/no`
  - `Object.keys(data.diff_summary.unknown_changes || {}).length > 0`
- `confidence changes: N`
  - `Object.keys(data.diff_summary.confidence_changes || {}).length`

## 表示ルール
- 1 行でも複数行でもよい
- ラベル文言は固定
- `yes/no` は小文字
- count は整数

## 注意
- 差分の意味づけは増やさない
- 新しい判定ロジックは作らない
- with / without の詳細 card はそのまま残す

## テスト追加
7. diff highlight block が表示される
8. `ranking changed: yes/no` が表示される
9. `score changes: N` が表示される
10. `reason changes: N` が表示される
11. `unknown reduced: yes/no` が表示される

---

# Task D: web UI テストを追加

## 目的
新しい value-oriented UI が壊れないようにする。

## 変更ファイル
- `tests/test_web_summary_panel.py`

## 必須検証項目
12. preset は query を置き換えるが自動実行しない前提である
13. explainer card は固定 4 bullet を持つ
14. ablation highlight は diff_summary の既存キーだけから導出される
15. unknown highlight は unknown_changes の有無だけで決まる

### テスト方針
- 既存同様 lightweight でよい
- DOM 完全 E2E は不要
- state / string generation / simple HTML presence 中心でよい

---

## 受け入れ条件
次を満たしたら完了。

1. preset buttons が追加される
2. explanatory card が追加される
3. Compare 後に top-level diff highlights が表示される
4. highlights は既存 diff_summary だけから導出される
5. 既存 Search / Compare / summary panel の挙動は壊さない
6. API schema は変更しない
7. 全テストが通る

---

## 実装順
必ずこの順で実装すること。

1. Task A: demo presets
2. Task B: value explainer
3. Task C: diff highlights
4. Task D: テスト追加
5. 必要なら protocol を最小更新

---

## コミット分割
可能なら 2 コミットまで分けてよい。

### Option 1: 1コミット
```text
Add demo presets and value-oriented compare highlights to web UI
```

### Option 2: 2コミット
1. `Add demo presets and compare explainer to web UI`
2. `Add ablation highlight badges to compare view`

---

## やってはいけないこと
- live randomness を導入すること
- `/api/ablation` の schema を変更すること
- full artifact JSON を UI で読むこと
- multi-domain UI に広げること
- free-form marketing copy を増やすこと
- preset click で自動実行すること

---

## 期待する差分の大きさ
- 中規模だが局所的
- 対象は `static/index.html` と UI テストのみ
- OPUS が 1 回で実装可能な範囲
