# OPUS 実装指示書（batch after c62ae00）

## この文書の位置づけ
これは**複数タスクをまとめた実装指示書**です。
設計書ではありません。実装対象、変更ファイル、追加関数、追加テストを固定します。

対象コミット: `c62ae00`
このコミットで以下は完了済み。
- live ablation artifact 保存
- `.index.json` / `_index_summary.json` 保存
- `trend_summary` / `anomaly_flags`
- `latest_artifact` / `comparison_rows` / `comparison_stats` / `flagged_rows`
- `focus_rows` / `recommended_artifact_paths` / `review_digest`
- `row_status` / `gate_summary`
- `format_directory_summary_text()`
- `--summarize-dir` CLI
- 411 tests passing

したがって、今回の実装対象は **directory summary を web UI 上で最小表示・確認できるようにすること** に限定します。

この指示書は 3 タスクで構成する。
- Task A: directory summary loader を追加
- Task B: summary panel を追加
- Task C: web UI テストを追加

---

## 今回の目的
web UI 上で `_index_summary.json` を読み、少なくとも次を確認できるようにする。

- gate status
- manual review の要否
- recommended artifacts
- flagged rows の有無

新しい評価意味論は追加しない。
既存の `_index_summary.json` をそのまま読むだけにする。

---

## 変更してよいファイル
今回変更してよいのは次だけ。

- `app/` 配下の live ablation UI 関連ファイル
- `components/` 配下の live ablation UI 関連ファイル
- `tests/` 配下の web UI テスト
- 必要なら `docs/solution_catalog_live_ablation_protocol.md`

**それ以外は変更しないこと。**

---

## 変更してはいけないもの
- `src/evaluator.py`
- `src/experiments/review_summary.py`
- `scripts/run_solution_catalog_live_ablation.py`
- `diff_summary` の既存キー
- `review_summary` の既存キー
- multi-domain ablation 系コード
- prompt / schema / catalog contract

---

# Task A: directory summary loader を追加

## 目的
UI 側で `_index_summary.json` を安全に読み取る最小 loader を追加する。

## 変更ファイル
- `app/` または `components/` 配下の live ablation UI 用 util

## 追加する関数
```ts
export async function loadDirectorySummary(path: string): Promise<DirectorySummary | null>
```

## 実装要件
- 入力は `_index_summary.json` への path
- JSON 読み込みに成功したら parsed object を返す
- 読み込み失敗または parse 失敗時は `null`
- 例外を UI に投げない
- 型は UI で使う最小 subset だけでよい

## UI で使う最小フィールド
- `total_runs`
- `gate_summary`
- `recommended_artifact_paths`
- `flagged_rows`
- `latest_artifact`

## テスト追加
1. `loadDirectorySummary` が正常 JSON を読める
2. 不正 JSON で `null`
3. 未存在 path で `null`

---

# Task B: summary panel を追加

## 目的
web UI に live ablation summary の最小表示を追加する。

## 表示する項目
1. `Gate status`
2. `Manual review required`
3. `Flagged runs`
4. `Recommended artifacts`
5. `Latest artifact`

## 表示ルール
- `Gate status`: `pass` / `review_required` / `empty`
- `Manual review required`: yes/no
- `Flagged runs`: `flagged_rows.length`
- `Recommended artifacts`: path を箇条書き
- `Latest artifact`: `artifact_path` を1行表示
- recommended が空なら `none`
- latest が null なら `none`

## UI 制約
- 新しいデザインシステム導入はしない
- 既存コンポーネントがあれば再利用
- テーブルは不要
- まずは summary card / panel で十分

## テスト追加
4. gate status が表示される
5. manual review yes/no が表示される
6. recommended artifacts が表示される
7. latest artifact が表示される
8. 空ケースで `none` が表示される

---

# Task C: web UI テストを追加

## 目的
summary panel が `_index_summary.json` の主要フィールドを正しく表示することを保証する。

## テスト方針
- fixture 的な summary object を使う
- 実ファイル I/O を伴わなくてよい
- loader と panel は分けてテストしてよい

## 必須検証項目
9. `review_required` のとき manual review が yes
10. `pass` のとき manual review が no
11. flagged rows 件数が表示される
12. recommended artifacts の順序が保持される
13. latest artifact が null のとき `none`

---

## 受け入れ条件
次を満たしたら完了。

1. `_index_summary.json` を読む loader が追加される
2. UI に summary panel が追加される
3. gate / manual review / flagged / recommended / latest を表示できる
4. 読み込み失敗時に UI が落ちない
5. web UI テストが追加される
6. 既存 live ablation script は一切変更しない
7. 全テストが通る

---

## 実装順
必ずこの順で実装すること。

1. Task A: loader
2. Task B: summary panel
3. Task C: web UI テスト
4. 必要なら protocol を最小更新

---

## コミット分割
可能なら 2 コミットまで分けてよい。

### Option 1: 1コミット
```text
Add web UI summary panel for live ablation directory summary
```

### Option 2: 2コミット
1. `Add directory summary loader for web UI`
2. `Add live ablation summary panel and UI tests`

---

## やってはいけないこと
- `scripts/run_solution_catalog_live_ablation.py` を変更すること
- `_index_summary.json` の schema を変更すること
- multi-domain 側 UI に広げること
- free-form 解釈文を UI に追加すること
- full artifact JSON を UI で読むこと

---

## 期待する差分の大きさ
- 中規模だが局所的
- 対象は web UI とそのテストのみ
- OPUS が 1 回で実装可能な範囲
