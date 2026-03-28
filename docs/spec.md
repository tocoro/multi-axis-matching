# Specification

本システムは問題→解決策の多軸評価ランキングを行う。

## コア構造
- 問題理解（problem type 推定）
- 制約抽出
- 評価軸選択（LLM による動的選定）
- 候補評価
- 集約
- ランキング

## 評価軸選択
- 問題タイプとユーザー要求に基づき LLM が動的に選定する
- 各軸に weight を割り当て、合計 1.0 とする
- 軸名はハードコードせず、問題に応じて柔軟に決定する

## スコア
- 各軸: 0.0〜1.0
- status: supported / unknown / conflict
- hard_constraint_violation: hard_constraints への明示的違反の場合のみ true

## 総合スコア
Σ(weight × score) / Σ(valid weight)

unknown は分母から除外する。

## 失格 (Disqualification)
- hard_constraints への明示的違反がある場合のみ disqualified とする
- conflict status だけでは失格にしない（低スコアとして扱う）
- axis_scores の hard_constraint_violation フラグで判定する

## 高リスク領域
- 医療
- 法律

unknown は保守的に扱う。
