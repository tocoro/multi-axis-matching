# OPUS 実装指示書（batch after 6e6db6b）

## この文書の位置づけ
これは**複数タスクをまとめた実装指示書**です。
設計書ではありません。実装対象、変更ファイル、追加関数、追加テストを固定します。

対象コミット: `6e6db6b`
このコミットで以下は完了済み。
- demo presets（restaurant / clinic）
- compare-first copy
- demo scenario cards 6本
- `Compare this scenario`
- scenario-driven `What to notice`
- 478 tests passing

したがって、今回の実装対象は **Web アプリのデモ導線をさらに見やすくし、restaurant / clinic の切り替えを明確にすること** に限定します。

この指示書は 4 タスクで構成する。
- Task A: domain filter tabs を追加
- Task B: scenario cards の visible subset と counts を追加
- Task C: active demo context header を追加
- Task D: web UI テストを追加

---

## 今回の目的
プレゼン時に、
- restaurant / clinic を瞬時に切り替えられる
- 今どちらのドメインを見ているか迷わない
- scenario cards が多すぎて視線が散らない

状態にする。

新しい評価意味論は追加しない。
既存 scenario データと Compare 導線だけを再構成する。

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

# Task A: domain filter tabs を追加

## 目的
scenario cards を restaurant / clinic / all の3状態で絞り込めるようにする。

## 変更ファイル
- `static/index.html`

## 実装内容
`Demo scenarios` 見出しの近くに tabs または segmented control を追加する。

## 固定ラベル
- `All`
- `Restaurant`
- `Clinic`

## 状態
- client-side state: `currentScenarioDomainFilter`
- allowed values: `all`, `restaurant`, `clinic`
- 初期値は `all`

## 動作仕様
- `All` → 6 cards 表示
- `Restaurant` → restaurant 3 cards のみ表示
- `Clinic` → clinic 3 cards のみ表示
- シナリオ順序は既存順を維持する
- tabs 切替で query は変更しない
- tabs 切替で Compare を自動実行しない

## 注意
- 新しい scenario データは増やさない
- hidden でも rerender でもよい
- style は既存 button 系でよい

## テスト追加
1. 初期状態が `All`
2. `Restaurant` で 3 件になる
3. `Clinic` で 3 件になる
4. `All` で 6 件になる

---

# Task B: scenario cards の visible subset と counts を追加

## 目的
今見えている scenario 数と domain 別数が一目で分かるようにする。

## 変更ファイル
- `static/index.html`

## 実装内容
`Demo scenarios` セクションに count line を追加する。

## 固定ラベル
- `Visible scenarios`
- `Restaurant`
- `Clinic`

## 表示形式
```text
Visible scenarios: 3 | Restaurant: 3 | Clinic: 0
```

## 計算ルール
- `Visible scenarios`: 現在表示中の cards 件数
- `Restaurant`: 現在表示中の restaurant 件数
- `Clinic`: 現在表示中の clinic 件数

## 注意
- 全件総数ではなく、現在 visible な件数のみ
- `all` のときは `6 | 3 | 3`
- `restaurant` のときは `3 | 3 | 0`
- `clinic` のときは `3 | 0 | 3`

## テスト追加
5. `all` のとき count が `6 | 3 | 3`
6. `restaurant` のとき count が `3 | 3 | 0`
7. `clinic` のとき count が `3 | 0 | 3`

---

# Task C: active demo context header を追加

## 目的
今の query / compare がどの scenario・どの domain 由来かを上部で明示する。

## 変更ファイル
- `static/index.html`

## 実装内容
検索カードの下または `Start with Compare` の下に、小さな context header を追加する。

## 固定ラベル
- `Demo context`

## 表示ルール
### デフォルト
```text
Demo context: manual
```

### scenario card から Compare 実行した後
```text
Demo context: clinic / Specialty conflict
```
または
```text
Demo context: restaurant / Quiet Italian
```

### 通常 Compare ボタンを押したとき
- `currentScenarioId = null` に戻る既存仕様を維持
- 表示は `Demo context: manual`

### preset ボタンのみ押したとき
- compare 実行前は `manual` のままでよい
- preset 選択を context に反映しない

## 注意
- scenario Compare のときだけ scenario title を使う
- `What to notice` と整合していること
- hidden state を増やしすぎない

## テスト追加
8. 初期表示が `Demo context: manual`
9. scenario compare 後に `domain / title` が表示される
10. 通常 Compare で `manual` に戻る
11. preset click だけでは `manual` のまま

---

# Task D: web UI テストを追加

## 目的
domain filter と active context が壊れないようにする。

## 変更ファイル
- `tests/test_web_summary_panel.py`

## 必須検証項目
12. domain filter は `all / restaurant / clinic` の3値固定である
13. cards の順序は filter 後も既存順を保つ
14. count line は visible subset の件数だけを数える
15. demo context は scenario Compare のときだけ scenario 名を持つ

### テスト方針
- 既存同様 lightweight でよい
- DOM 完全 E2E は不要
- state / filtering / count / string generation 中心でよい

---

## 受け入れ条件
次を満たしたら完了。

1. domain filter tabs が追加される
2. scenario cards を `all / restaurant / clinic` で絞れる
3. visible count line が追加される
4. `Demo context` が追加される
5. scenario Compare と manual Compare が UI 上で区別できる
6. 既存 `Compare this scenario` と `What to notice` は壊さない
7. API schema は変更しない
8. 全テストが通る

---

## 実装順
必ずこの順で実装すること。

1. Task A: domain filter tabs
2. Task B: count line
3. Task C: demo context
4. Task D: テスト追加
5. 必要なら protocol を最小更新

---

## コミット分割
可能なら 2 コミットまで分けてよい。

### Option 1: 1コミット
```text
Add domain filter and demo context to scenario compare UI
```

### Option 2: 2コミット
1. `Add domain filter tabs and visible counts to demo scenarios`
2. `Add demo context header for scenario compare`

---

## やってはいけないこと
- new scenario を追加すること
- `/api/ablation` の schema を変更すること
- full artifact JSON を UI で読むこと
- multi-domain evaluator 側に手を入れること
- preset click を auto-run に変えること
- scenario filter で hidden flags を勝手に変えること

---

## 期待する差分の大きさ
- 中規模だが局所的
- 対象は `static/index.html` と UI テストのみ
- OPUS が 1 回で実装可能な範囲
