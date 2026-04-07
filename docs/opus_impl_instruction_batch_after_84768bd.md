# OPUS 実装指示書（batch after 84768bd）

## この文書の位置づけ
これは**複数タスクをまとめた実装指示書**です。
設計書ではありません。実装対象、変更ファイル、追加関数、追加テストを固定します。

対象コミット: `84768bd`
補足: `99852a7` で以下は完了済み。
- domain preset groups（Restaurant / Clinic）
- clinic presets 3本
- `Start with Compare` compare-first ガイダンス
- 関連 UI テスト追加

`84768bd` では prompt 側で非標準 status 値を禁止し、`supported / unknown / conflict` の3値に強制する修正が入っている。

したがって、今回の実装対象は **Web アプリで「どのケースを、何に注目して見ればよいか」を一目で分かるようにすること** に限定します。

この指示書は 4 タスクで構成する。
- Task A: scenario cards を追加
- Task B: scenario ごとの `Compare this scenario` 導線を追加
- Task C: result 側に `What to notice` block を追加
- Task D: web UI テストを追加

---

## 今回の目的
プレゼン時に、
- 単なる検索 UI ではなく、比較実験 UI であること
- restaurant / clinic の両方で、見るべきポイントが違うこと
- fixed mock でも、ケースごとの価値が伝わること

を明確にする。

新しい評価意味論は追加しない。
既存 Search / Compare / diff_summary / preset query を再構成するだけにする。

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

# Task A: scenario cards を追加

## 目的
preset を単なるボタン列ではなく、「何を見せるケースか」が分かるカードとして表示する。

## 変更ファイル
- `static/index.html`

## 実装内容
既存 preset group の下に、scenario cards block を追加する。

## 固定セクション見出し
- `Demo scenarios`

## 表示対象シナリオ
restaurant 3本 + clinic 3本、合計 6 本。
既存 preset 文言をそのまま使う。

## 各 scenario card に固定で含める要素
1. scenario title
2. domain label
   - `restaurant` または `clinic`
3. scenario query（短い本文で表示）
4. `What this shows` 見出し
5. fixed bullet 2つ

## fixed bullet（シナリオ別）

### Restaurant / Quiet Italian
- `catalog can change reasons without forcing rank changes`
- `good fit can be explained across multiple axes`

### Restaurant / Cheap but far
- `trade-offs can surface without becoming hard disqualification`
- `distance and budget can pull in different directions`

### Restaurant / Information lacking
- `unknowns should remain visible when evidence is missing`
- `the system should avoid pretending certainty`

### Clinic / After-work internal medicine
- `specialty, hours, and insurance can align in one strong match`
- `multi-axis support is clearer than a single relevance score`

### Clinic / Specialty conflict
- `specialty mismatch can remain a conflict without hard exclusion`
- `the system separates conflicts from disqualification`

### Clinic / Insurance but low info
- `low-information cases should still return candidates`
- `unknown handling matters as much as ranking`

## UI 制約
- 新しいデザインシステム導入はしない
- grid でも縦並びでもよい
- free-form bullet を追加しない
- scenario title は preset label と一致させる

## テスト追加
1. `Demo scenarios` 見出しが表示される
2. scenario card が 6 本表示される
3. 各 card に domain label がある
4. 各 card に `What this shows` がある

---

# Task B: scenario ごとの `Compare this scenario` 導線を追加

## 目的
preset click だけで終わらず、プレゼン時に 1 操作で Compare に進めるようにする。

## 変更ファイル
- `static/index.html`

## 実装内容
各 scenario card に button を追加する。

## 固定ボタン文言
- `Compare this scenario`

## 動作仕様
button 押下時:
1. その scenario の query を `#query` にセット
2. 既存の Compare 実行関数を呼ぶ
3. Search は実行しない

## 状態管理
- client-side で `currentScenarioId` を保持してよい
- scenario card からの実行時のみ、その id をセットする
- 手入力や通常 Compare では `currentScenarioId = null` に戻してよい

## 注意
- 既存 preset ボタンは残す
- preset ボタンは従来どおり「置き換えのみ」
- auto-run を追加するのはこの新ボタンだけ

## テスト追加
5. `Compare this scenario` ボタンが各 card にある
6. button 押下で query が置き換わる
7. button 押下で Compare 実行経路に入る
8. preset click 単体では従来どおり自動実行しない

---

# Task C: result 側に `What to notice` block を追加

## 目的
Compare 結果を見たときに、観客が何を見るべきかを迷わないようにする。

## 変更ファイル
- `static/index.html`

## 実装内容
scenario card 由来で Compare を実行した場合のみ、diff card の上部または直下に `What to notice` block を表示する。

## 表示条件
- `currentScenarioId` が存在する場合のみ表示
- 手入力 Compare や通常 Compare では非表示

## 固定見出し
- `What to notice`

## 表示内容
Task A のシナリオごとの fixed bullet 2つを、そのまま箇条書きで表示する。

## 注意
- diff_summary の内容に応じて文言を変えない
- free-form 要約を生成しない
- あくまで「見る観点」の固定ガイドであること

## テスト追加
9. scenario Compare 後に `What to notice` が表示される
10. 手入力 Compare では `What to notice` が表示されない
11. scenario ごとに対応する fixed bullet が表示される

---

# Task D: web UI テストを追加

## 目的
scenario-driven demo UI が壊れないようにする。

## 変更ファイル
- `tests/test_web_summary_panel.py`

## 必須検証項目
12. scenario cards は restaurant 3 + clinic 3 の固定構成である
13. `Compare this scenario` は preset click と別経路である
14. `What to notice` は scenario Compare のときだけ出る
15. fixed bullet は scenario ごとに固定であり、diff 内容から生成しない

### テスト方針
- 既存同様 lightweight でよい
- DOM 完全 E2E は不要
- 文字列存在、state 分岐、handler 呼び出し中心でよい

---

## 受け入れ条件
次を満たしたら完了。

1. `Demo scenarios` セクションが追加される
2. scenario cards が 6 本追加される
3. 各 card に `Compare this scenario` がある
4. scenario button から 1 操作で Compare 実行できる
5. scenario Compare のときだけ `What to notice` が出る
6. 既存 preset button は従来動作を維持する
7. API schema は変更しない
8. 全テストが通る

---

## 実装順
必ずこの順で実装すること。

1. Task A: scenario cards
2. Task B: `Compare this scenario`
3. Task C: `What to notice`
4. Task D: テスト追加
5. 必要なら protocol を最小更新

---

## コミット分割
可能なら 2 コミットまで分けてよい。

### Option 1: 1コミット
```text
Add scenario cards and one-click compare guidance to web UI
```

### Option 2: 2コミット
1. `Add demo scenario cards for restaurant and clinic`
2. `Add one-click compare and what-to-notice guidance`

---

## やってはいけないこと
- random scenario を導入すること
- `/api/ablation` の schema を変更すること
- full artifact JSON を UI で読むこと
- multi-domain evaluator 側に手を入れること
- free-form marketing copy を増やすこと
- scenario に応じて hidden flags を勝手に変えること

---

## 期待する差分の大きさ
- 中規模だが局所的
- 対象は `static/index.html` と UI テストのみ
- OPUS が 1 回で実装可能な範囲
