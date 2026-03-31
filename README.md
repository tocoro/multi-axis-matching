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
| `GOOGLE_PLACES_API_KEY` | Google Places 使用時 | Places Text Search API 用 |

プロバイダはモデル名のプレフィックスから自動判定されます。`EVAL_PROVIDER` で明示指定も可能です。

## 実行方法

### Web UI (推奨)

```bash
uv run server.py              # mock mode → http://localhost:3000
uv run server.py --live       # real LLM
uv run server.py --port 8080  # custom port
```

ブラウザで `http://localhost:3000` を開くと、クエリ入力 → ランキング表示の UI が使えます。

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

## Restaurant 候補収集パイプライン

query → search → retrieve → normalize → evaluate の流れで動作します。
現時点では search / retrieve は mock 実装です (実 API 未接続)。

```
user query
  ↓  query understanding (ルールベース条件抽出)
  ↓  search (mock: 条件ベースフィルタ + fallback)
  ↓  retrieve (mock: source_id → 詳細レコード)
  ↓  normalize (raw_record → candidate 形式)
  ↓  evaluate (既存の多軸評価)
  ↓
ranking JSON
```

### Search filtering
mock search は条件に応じて候補を絞り込みます:
- **Hard filter**: genre 不一致、location 不一致 (近隣エリアは許容) を除外
- **Soft filter**: max_price は除外ではなく優先度ソートに使用
- **Fallback**: 0 件時は `genre+location → genre のみ → location のみ → 全件` の順で条件緩和
- **Strict mode**: `--strict` で fallback を無効化。0 件ならそのまま 0 件を返す
- **Diagnostics**: `search_diagnostics` で fallback の有無・段階・件数を追跡可能

```bash
# Strict モード (fallback なし)
uv run scripts/run_restaurant_pipeline.py --mock --strict
```

### Pipeline 実行

```bash
# Mock (API キー不要)
uv run scripts/run_restaurant_pipeline.py --mock

# Live
uv run scripts/run_restaurant_pipeline.py --live

# ログ付き
uv run scripts/run_restaurant_pipeline.py --mock --log-level INFO
```

### Adapter 構造
search / retrieve は adapter interface 経由で差し替え可能です:
- **デフォルト**: `MockPlaceSearcher` / `MockPlaceRetriever` (固定候補プール)
- **Search 実装済み**: `GooglePlacesSearcher` (Text Search API)
- **Retrieve 未実装**: `GooglePlacesRetriever` (Place Details スタブ)
- Pipeline は adapter injection を受け付けます

Google Places Search を使うには `GOOGLE_PLACES_API_KEY` が必要です。
現時点では Search のみ実装されており、Retrieve は mock のままです。

設計詳細: `docs/google_places_design.md`

## ファイル構成

```
src/
  evaluator.py                  # 多軸評価パイプライン
  mock.py                       # Deterministic mock (テスト・--mock 用)
  adapters/
    places/
      base.py                   # PlaceSearcher / PlaceRetriever Protocol
      mock_places.py            # Mock adapter (フィルタ + fallback)
      google_places.py          # Google Places スタブ (未実装)
      config.py                 # GooglePlacesConfig
  services/
    infer_search_conditions.py  # Query understanding (条件抽出)
  searchers/
    place_searcher.py           # 後方互換ラッパー
  retrievers/
    place_retriever.py          # 後方互換ラッパー
  normalizers/
    restaurant_normalizer.py    # raw_record → candidate 正規化
  pipeline/
    restaurant_pipeline.py      # パイプラインオーケストレーター
server.py                       # FastAPI サーバー (Web UI + API)
static/
  index.html                    # Web UI
scripts/
  run_restaurant_example.py     # 評価器単体実行 (--mock / --live)
  run_restaurant_pipeline.py    # パイプライン実行 (--mock / --live)
prompts/
  infer_problem_type.txt        # 問題タイプ推定プロンプト
  extract_constraints.txt       # 制約抽出プロンプト
  select_axes.txt               # 評価軸選択プロンプト
  evaluate_candidate.txt        # 候補評価プロンプト
schemas/
  request.schema.json           # 入力スキーマ
  response.schema.json          # 出力スキーマ
examples/
  restaurant.json               # 評価器サンプル入力
  restaurant.expected.json      # Mock 評価器の期待出力
  restaurant_pipeline_input.json # パイプラインサンプル入力
  restaurant_case_1..5.json     # 境界条件テストケース
docs/
  spec.md                       # 仕様書
  google_places_design.md       # Google Places 接続設計書
tests/
  test_evaluator.py             # 評価器ユニット + 統合テスト
  test_restaurant_e2e.py        # 評価器 E2E テスト
  test_restaurant_cases.py      # 境界条件テスト (5ケース)
  test_restaurant_pipeline.py   # パイプラインテスト
```

## 注意事項
- **Live 実行には使用するプロバイダの API キーが必要です**
- SDK は使うプロバイダ分だけインストールすれば OK（遅延 import）
- search / retrieve は adapter interface 経由。デフォルトは mock 実装。Google Places 接続は設計済み・スタブ準備済み・実通信は未実装
- `examples/restaurant.expected.json` は `--mock` 実行時の期待出力です。mock のロジックを変更した場合は再生成してください
