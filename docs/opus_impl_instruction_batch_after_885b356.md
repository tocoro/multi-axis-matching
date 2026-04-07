# OPUS 実装指示書（batch after 885b356）

## この文書の位置づけ
これは**複数タスクをまとめた実装指示書**です。
設計書ではありません。実装対象、変更ファイル、追加関数、追加テストを固定します。

対象コミット: `885b356`
このコミットで以下は完了済み。
- `Compare summary`
- `Changed candidates`
- `Quick jump`
- with / without anchor ids
- 506 tests passing

したがって、今回の実装対象は **Compare 詳細の視線移動を減らし、同一 candidate の比較をしやすくすること** に限定します。

この指示書は 4 タスクで構成する。
- Task A: changed candidate links を追加
- Task B: candidate compare anchors を追加
- Task C: candidate compare index を追加
- Task D: web UI テストを追加

---

## 今回の目的
Compare 実行後に、
- changed candidate から直接その candidate 比較位置へ飛べる
- with / without の同一 candidate をまとめて見やすい
- scenario を連続実行しても視線移動が少ない

状態にする。

新しい評価意味論は追加しない。
既存 `diff_summary` と既存 ranking 表示を再構成するだけにする。

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

# Task A: changed candidate links を追加

## 目的
`Changed candidates` を単なる文字列一覧ではなく、候補比較位置へのリンクにする。

## 変更ファイル
- `static/index.html`

## 実装内容
既存 `Changed candidates` block の各 candidate id を anchor link に変更する。

## 表示形式
- `- place_1` の文字列は維持してよい
- ただし candidate id 部分は link にする

## href ルール
- `href="#candidateCompare-place_1"`
- `href="#candidateCompare-clinic_3"`

## 注意
- `Changed candidates: none` はそのまま
- 既存の union / dedupe / order ルールは一切変えない
- candidate 名への解決はしない

## テスト追加
1. changed candidate が link になる
2. href が `#candidateCompare-{id}` 形式である
3. `none` のとき link を出さない

---

# Task B: candidate compare anchors を追加

## 目的
with / without の結果列の中で、同一 candidate を比較する位置に飛べるようにする。

## 変更ファイル
- `static/index.html`

## 実装内容
Compare 結果描画時に、candidate ごとの compare anchor block を追加する。

## 実装ルール
- with / without の ranking から candidate ids の union を作る
- 順序は with_catalog の ranking 順を優先し、残りを without_catalog 順で後ろに足す
- 各 candidate ごとに invisible でもよいので anchor target を作る

## anchor id
- `id="candidateCompare-place_1"`
- `id="candidateCompare-clinic_3"`

## 配置
- 各 candidate の with/without 比較開始位置の手前
- 少なくとも browser anchor が効く位置であればよい

## 注意
- 既存 result card 構造は大きく壊さない
- candidate 表示名の新規取得はしない
- ranking 順自体は変えない

## テスト追加
4. with 優先 + without 補完の union order が維持される
5. candidate compare anchor id が生成される
6. anchor ids が changed candidates link と整合する

---

# Task C: candidate compare index を追加

## 目的
詳細結果の手前に、比較対象 candidate の index をまとめて置く。

## 変更ファイル
- `static/index.html`

## 表示位置
- `Quick jump` の下
- with / without 詳細列の上

## 固定見出し
- `Candidate compare index`

## 表示ルール
- candidate ids の一覧を link として表示
- href は `#candidateCompare-{id}`
- 順序は Task B の union order と同じ
- 1件もなければ `Candidate compare index: none`

## 注意
- `Changed candidates` は diff が出たものだけ
- `Candidate compare index` は compare 対象 candidate 全体
- この2つを混同しないこと

## テスト追加
7. `Candidate compare index` 見出しが表示される
8. 全 candidate の link が表示される
9. 順序が Task B の union order と一致する
10. 空なら `none`

---

# Task D: web UI テストを追加

## 目的
candidate navigation 導線が壊れないようにする。

## 変更ファイル
- `tests/test_web_summary_panel.py`

## 必須検証項目
11. changed candidate links は changed set のみを対象にする
12. compare index は full union set を対象にする
13. href 形式は常に `#candidateCompare-{id}`
14. union order は with → without 補完を守る
15. scenario Compare / manual Compare のどちらでも candidate navigation が使える

### テスト方針
- 既存同様 lightweight でよい
- DOM 完全 E2E は不要
- string generation / union order / href 生成中心でよい

---

## 受け入れ条件
次を満たしたら完了。

1. `Changed candidates` が link 化される
2. candidate compare anchor ids が追加される
3. `Candidate compare index` が追加される
4. full union と changed subset が区別される
5. 既存 `Compare summary` / `Quick jump` / `What to notice` は壊さない
6. API schema は変更しない
7. 全テストが通る

---

## 実装順
必ずこの順で実装すること。

1. Task A: changed candidate links
2. Task B: candidate compare anchors
3. Task C: candidate compare index
4. Task D: テスト追加
5. 必要なら protocol を最小更新

---

## コミット分割
可能なら 2 コミットまで分けてよい。

### Option 1: 1コミット
```text
Add candidate compare navigation to web UI
```

### Option 2: 2コミット
1. `Link changed candidates to compare anchors`
2. `Add candidate compare index for with/without results`

---

## やってはいけないこと
- new diff semantics を追加すること
- `/api/ablation` の schema を変更すること
- full artifact JSON を UI で読むこと
- multi-domain evaluator 側に手を入れること
- candidate 表示名を新規解決すること

---

## 期待する差分の大きさ
- 中規模だが局所的
- 対象は `static/index.html` と UI テストのみ
- OPUS が 1 回で実装可能な範囲
