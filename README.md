# multi-axis-matching

LLMベースの問題解決マッチング評価器です。

## 目的
ユーザーの問題記述と複数の候補解決策を入力として、問題タイプごとに異なる評価軸を用いながら各候補を多軸評価し、理由付きランキングを返します。

## スコープ
- 問題タイプ推定
- 制約抽出
- 候補ごとの軸別評価
- 総合スコア集約
- 理由付きランキング

## 初期構成
- `docs/spec.md` 仕様書
- `schemas/request.schema.json` 入力スキーマ
- `schemas/response.schema.json` 出力スキーマ
- `prompts/` LLMプロンプト
- `examples/` サンプル入出力

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
