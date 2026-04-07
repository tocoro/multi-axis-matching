# OPUS 実装指示書（batch after 88dbc43）

## この文書の位置づけ
これは**複数タスクをまとめた実装指示書**です。
設計書ではありません。実装対象、変更ファイル、追加関数、追加テストを固定します。

対象コミット: `88dbc43`
このコミットで以下は完了済み。
- demo presets（restaurant 3本）
- `Why Compare matters` explainer card
- Compare 後の diff highlight badges
- 459 tests passing

したがって、今回の実装対象は **Web アプリ上で restaurant / clinic の両ドメインを価値訴求しやすくすること** に限定します。

この指示書は 4 タスクで構成する。
- Task A: domain preset groups を追加
- Task B: clinic presets を追加
- Task C: compare-first 導線を強める hero / section copy を追加
- Task D: web UI テストを追加

---

## 今回の目的
Web アプリをプレゼンしたときに、
- restaurant だけの検索 UI に見えない
- clinic でも multi-axis matching の価値が分かる
- Compare を主役として見せられる
- fixed mock でも「同じ答えを返すだけ」に見えない

状態にする。

新しい評価意味論は追加しない。
既存 Search / Compare / diff_summary / summary panel を再構成するだけにする。

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

# Task A: domain preset groups を追加

## 目的
preset が restaurant 専用に見える状態をやめ、restaurant / clinic の両方を UI 上で明示する。

## 変更ファイル
- `static/index.html`

## 実装内容
既存 preset bar を 2 グループに分ける。

## 固定見出し
1. `Restaurant presets`
2. `Clinic presets`

## UI 仕様
- 既存 restaurant presets は `Restaurant presets` の下に移す
- clinic presets は `Clinic presets` の下に追加する
- 既存 `setPreset(query)` を再利用してよい
- preset click で query を置き換えるだけにする
- 自動実行はしない

## 注意
- domain selector は今回追加しない
- preset ごとに hidden state を変更しない
- live / strict / google places の状態は変更しない

## テスト追加
1. `Restaurant presets` 見出しが表示される
2. `Clinic presets` 見出しが表示される
3. preset click は query を置き換えるだけで自動実行しない

---

# Task B: clinic presets を追加

## 目的
clinic ドメインでも、このシステムの利点が伝わる代表ケースを 1 クリックで再現できるようにする。

## 変更ファイル
- `static/index.html`

## 固定で追加する clinic preset
1. `After-work internal medicine`
   - `恵比寿で夕方以降に内科を受診したい。保険適用希望`
2. `Specialty conflict`
   - `渋谷で今夜受診したい。近いところがよいが、内科が望ましい`
3. `Insurance but low info`
   - `新宿近辺で保険が使えるクリニックを探したい。情報が少なくても候補は見たい`

## 意図
- 1本目: strong match
- 2本目: conflict but not disqualified
- 3本目: unknown retained

## 動作仕様
- click で `#query` の値を置き換える
- 自動実行しない
- 既存 restaurant presets と同じ UI スタイルでよい

## テスト追加
4. clinic preset が 3 本存在する
5. `After-work internal medicine` で query が置き換わる
6. `Specialty conflict` で query が置き換わる
7. `Insurance but low info` で query が置き換わる

---

# Task C: compare-first 導線を強める hero / section copy を追加

## 目的
初見のユーザーが Search ではなく Compare を先に試すよう、UI の説明を寄せる。

## 変更ファイル
- `static/index.html`

## 実装内容
検索カードの上部か直下に、短い固定 copy block を追加する。

## 固定タイトル
`Start with Compare`

## 固定本文
`Use Compare first to see how catalog knowledge changes reasons, scores, and unknown handling across the same query.`

## 補助行（固定）
`Search shows one result set. Compare shows what the system actually adds.`

## 表示ルール
- 文章は固定
- 強調はしてよいが free-form copy は追加しない
- 既存 `Why Compare matters` card は残す
- `Start with Compare` block は `Why Compare matters` より上に置く

## 注意
- ボタンの並び順は変えなくてよい
- Compare を自動実行させない

## テスト追加
8. `Start with Compare` タイトルが表示される
9. 固定本文が表示される
10. 補助行が表示される

---

# Task D: web UI テストを追加

## 目的
新しい domain-aware presets と compare-first 導線が壊れないようにする。

## 変更ファイル
- `tests/test_web_summary_panel.py`

## 必須検証項目
11. restaurant / clinic の両 preset group が存在する
12. clinic presets は 3 本固定である
13. clinic presets も自動実行しない
14. compare-first copy は固定文言を持つ
15. 既存 `Why Compare matters` card は残っている

### テスト方針
- 既存同様 lightweight でよい
- DOM 完全 E2E は不要
- 文字列存在と preset 値検証中心でよい

---

## 受け入れ条件
次を満たしたら完了。

1. preset UI が restaurant / clinic の 2 グループになる
2. clinic preset が 3 本追加される
3. compare-first copy が追加される
4. 既存 restaurant presets は残る
5. 既存 explainer / diff highlights / summary panel は壊さない
6. API schema は変更しない
7. 全テストが通る

---

## 実装順
必ずこの順で実装すること。

1. Task A: domain preset groups
2. Task B: clinic presets
3. Task C: compare-first copy
4. Task D: テスト追加
5. 必要なら protocol を最小更新

---

## コミット分割
可能なら 2 コミットまで分けてよい。

### Option 1: 1コミット
```text
Add clinic presets and compare-first copy to web UI
```

### Option 2: 2コミット
1. `Add domain-aware preset groups to web UI`
2. `Add clinic presets and compare-first guidance`

---

## やってはいけないこと
- clinic 専用の新 API を追加すること
- preset click で自動実行すること
- `/api/ablation` の schema を変更すること
- full artifact JSON を UI で読むこと
- random preset を導入すること
- free-form marketing copy を増やすこと

---

## 期待する差分の大きさ
- 中規模だが局所的
- 対象は `static/index.html` と UI テストのみ
- OPUS が 1 回で実装可能な範囲
