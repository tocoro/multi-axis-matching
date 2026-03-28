# Specification

本システムは問題→解決策の多軸評価ランキングを行う。

## コア構造
- 問題理解
- 評価軸選択
- 候補評価
- 集約

## スコア
- 各軸: 0.0〜1.0
- status: supported / unknown / conflict

## 総合スコア
Σ(weight × score) / Σ(valid weight)

## 高リスク領域
- 医療
- 法律

unknownは保守的に扱う。
