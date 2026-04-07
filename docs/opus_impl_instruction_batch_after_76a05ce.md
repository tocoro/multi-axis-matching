# OPUS 実装指示書（batch after 76a05ce）

## この文書の位置づけ
これは**複数タスクをまとめた実装指示書**です。
設計書ではありません。実装対象、変更ファイル、追加関数、追加テストを固定します。

対象コミット: `76a05ce`
このコミットで以下は完了済み。
- `Compare summary`
- `Changed candidates`
- `Quick jump`
- `Candidate compare index`
- per-candidate `Candidate delta`
- changed-only filter
- `Candidate focus`
- 528 tests passing

したがって、今回の実装対象は **プレゼン中に複数ケースを連続で比較しやすくする lightweight な compare history UI** に限定します。

この指示書は 4 タスクで構成する。
- Task A: compare history state を追加
- Task B: compare history panel を追加
- Task C: rerun / restore query 導線を追加
- Task D: web UI テストを追加

---

## 今回の目的
プレゼン時に、
- 直前の Compare ケースを見失わない
- restaurant / clinic の複数ケースを行き来しやすい
- fixed mock でも「複数ケースを比較している」ことが伝わる

状態にする。

新しい評価意味論は追加しない。
既存の query / scenario context / diff_summary から lightweight な履歴を作るだけにする。

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

# Task A: compare history state を追加

## 目的
直近の Compare 実行を client-side に軽く保持する。

## 変更ファイル
- `static/index.html`

## 追加 state
- `compareHistory`

## データ構造
各 entry は次の固定 shape にする。

```js
{
  query: string,
  scenarioLabel: string | null,
  domain: string | null,
  rankingChanged: boolean,
  changedCandidateCount: number,
  timestampLabel: string,
}
```

## 計算ルール
- `query`: Compare 実行時の query
- `scenarioLabel`: scenario compare のときは title、manual compare のときは `null`
- `domain`: scenario compare のときは `restaurant` or `clinic`、manual compare のときは `null`
- `rankingChanged`: `data.diff_summary.ranking_changed`
- `changedCandidateCount`: 既存 changed candidate union の件数
- `timestampLabel`: client-side で `new Date().toLocaleTimeString()` でよい

## 保持ルール
- 新しい Compare 成功時に先頭追加
- 最大 5 件まで保持
- 6 件目以降は末尾を落とす
- Search 実行では履歴を更新しない

## テスト追加
1. compare success で履歴追加
2. manual compare は `scenarioLabel/domain` が null
3. scenario compare は label/domain を持つ
4. 最大5件で打ち止め

---

# Task B: compare history panel を追加

## 目的
UI 上で直近の Compare ケース一覧を見られるようにする。

## 変更ファイル
- `static/index.html`

## 表示位置
- Compare 結果エリアの上部
- `Compare summary` より上

## 固定見出し
- `Recent compare history`

## 表示形式
各 entry を1行で表示する。

### fixed row format
```text
- 14:32:10 | clinic | Specialty conflict | ranking unchanged | changed candidates: 2
```

manual compare の場合:
```text
- 14:35:05 | manual | ranking changed | changed candidates: 1
```

## 文言ルール
- domain が null のとき `manual`
- scenarioLabel が null のとき label 部分は出さない
- rankingChanged true → `ranking changed`
- false → `ranking unchanged`
- changedCandidateCount は整数で表示

## empty 表示
- `Recent compare history: none`

## 注意
- 永続化不要
- localStorage 不要
- session 中だけでよい

## テスト追加
5. 見出しが表示される
6. empty で `none`
7. scenario row format が正しい
8. manual row format が正しい

---

# Task C: rerun / restore query 導線を追加

## 目的
履歴行から同じ query に戻り、すぐ Compare し直せるようにする。

## 変更ファイル
- `static/index.html`

## 実装内容
各 history row に 2 つの小リンクまたはボタンを追加する。

## 固定文言
- `Restore query`
- `Run again`

## 動作仕様
### Restore query
- `#query` にその履歴の query を入れる
- Compare は実行しない

### Run again
- `#query` にその履歴の query を入れる
- 既存 Compare 実行関数を呼ぶ

## 注意
- hidden flags は変更しない
- scenario compare の履歴でも、復元時に scenario state を自動復元しなくてよい
- `What to notice` は manual compare 扱いでよい

## テスト追加
9. `Restore query` は query を戻すだけ
10. `Run again` は compare 実行経路に入る
11. history rerun は scenario state を必須にしない

---

# Task D: web UI テストを追加

## 目的
compare history UI が壊れないようにする。

## 変更ファイル
- `tests/test_web_summary_panel.py`

## 必須検証項目
12. history entry は compare 実行時だけ増える
13. row formatting は scenario/manual を区別する
14. history size は最大5件
15. rerun と restore の役割が分離している

### テスト方針
- 既存同様 lightweight でよい
- DOM 完全 E2E は不要
- state / formatting / handler intent 中心でよい

---

## 受け入れ条件
次を満たしたら完了。

1. compare history state が追加される
2. `Recent compare history` panel が追加される
3. 最大5件の履歴が表示される
4. `Restore query` と `Run again` が機能する
5. Search 実行では履歴を汚さない
6. 既存 Compare UI は壊さない
7. API schema は変更しない
8. 全テストが通る

---

## 実装順
必ずこの順で実装すること。

1. Task A: history state
2. Task B: history panel
3. Task C: restore / rerun
4. Task D: テスト追加
5. 必要なら protocol を最小更新

---

## コミット分割
可能なら 2 コミットまで分けてよい。

### Option 1: 1コミット
```text
Add recent compare history panel to web UI
```

### Option 2: 2コミット
1. `Add compare history state and formatting`
2. `Add restore and rerun actions for compare history`

---

## やってはいけないこと
- localStorage を導入すること
- `/api/ablation` の schema を変更すること
- full artifact JSON を UI で読むこと
- multi-domain evaluator 側に手を入れること
- scenario hidden state を history rerun で自動復元すること

---

## 期待する差分の大きさ
- 中規模だが局所的
- 対象は `static/index.html` と UI テストのみ
- OPUS が 1 回で実装可能な範囲
