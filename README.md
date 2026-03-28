# multi-axis-matching

LLMベースの問題解決マッチング評価器です。

## 目的
ユーザーの問題記述と複数の候補解決策を入力として、問題タイプごとに異なる評価軸を用いながら各候補を多軸評価し、理由付きランキングを返します。

## スコープ
- 問題タイプ推定
- 制約抽出
- 評価軸選択 (LLM による動的選定)
- 候補ごとの軸別評価
- 総合スコア集約
- 理由付きランキング

## 想定問題タイプ
- entertainment.music
- local.restaurant
- local.clinic
- professional.legal
- commerce.product

## 設計原則
1. 候補生成と候補評価を分離する
2. 類似度は候補抽出に使えても、最終評価の代替にはしない
3. 評価軸は問題タイプ依存とする
4. unknown は低得点と区別する
5. 高リスク領域では保守的に動作する

---

## セットアップ

### 依存関係

```bash
# uv がある場合 (推奨)
uv pip install -r requirements.txt

# pip の場合
pip install -r requirements.txt
```

### 環境変数

```bash
cp .env.example .env
# .env を編集して使用するプロバイダの API キーを設定
```

| 変数名 | 必須 | 説明 |
|---|---|---|
| `EVAL_MODEL` | いいえ | 使用モデル (default: `claude-sonnet-4-6`) |
| `EVAL_PROVIDER` | いいえ | プロバイダ明示指定。省略時はモデル名から自動判定 |
| `ANTHROPIC_API_KEY` | Anthropic 使用時 | `claude-*` モデル用 |
| `OPENAI_API_KEY` | OpenAI 使用時 | `gpt-*` / `o1-*` / `o3-*` / `o4-*` モデル用 |
| `GOOGLE_API_KEY` | Gemini 使用時 | `gemini-*` モデル用 |

プロバイダはモデル名のプレフィックスから自動判定されます。`EVAL_PROVIDER` で明示指定も可能です。

## 実行方法

### Mock モード（API キー不要）

```bash
uv run scripts/run_restaurant_example.py --mock
```

LLM を呼ばず固定値で動作します。毎回同じ結果を返します。

### Live モード（API キーが必要）

```bash
# Anthropic (default)
export ANTHROPIC_API_KEY=sk-ant-...
uv run scripts/run_restaurant_example.py --live

# OpenAI
export OPENAI_API_KEY=sk-...
EVAL_MODEL=gpt-4o uv run scripts/run_restaurant_example.py --live

# Gemini
export GOOGLE_API_KEY=...
EVAL_MODEL=gemini-2.5-flash uv run scripts/run_restaurant_example.py --live
```

`EVAL_MODEL` でモデルを指定すると、プロバイダが自動で切り替わります。

### ログ出力

`--log-level` でログ量を制御できます。ログは stderr に出力され、stdout の JSON を汚しません。

```bash
# パイプライン各ステップの進捗を確認
uv run scripts/run_restaurant_example.py --mock --log-level INFO

# LLM の入出力を含むデバッグログ
uv run scripts/run_restaurant_example.py --mock --log-level DEBUG
```

### テスト

```bash
uv run --with anthropic --with jsonschema --with pytest pytest tests/ -v
```

## ファイル構成

```
src/
  evaluator.py        # 評価パイプライン本体
  mock.py             # Deterministic mock (テスト・--mock 用)
scripts/
  run_restaurant_example.py  # 実行スクリプト (--mock / --live)
prompts/
  infer_problem_type.txt     # 問題タイプ推定プロンプト
  extract_constraints.txt    # 制約抽出プロンプト
  select_axes.txt            # 評価軸選択プロンプト
  evaluate_candidate.txt     # 候補評価プロンプト
schemas/
  request.schema.json        # 入力スキーマ
  response.schema.json       # 出力スキーマ
examples/
  restaurant.json            # サンプル入力
  restaurant.expected.json   # Mock 実行時の期待出力
docs/
  spec.md                    # 仕様書
tests/
  test_evaluator.py          # ユニット + 統合テスト
  test_restaurant_e2e.py     # Restaurant E2E テスト
```

## 注意事項
- **Live 実行には使用するプロバイダの API キーが必要です**
- SDK は使うプロバイダ分だけインストールすれば OK（遅延 import）
- 候補検索機能は未実装です。現時点では JSON で候補を与えて評価する部分のみ動作します
- `examples/restaurant.expected.json` は `--mock` 実行時の期待出力です。mock のロジックを変更した場合は再生成してください
