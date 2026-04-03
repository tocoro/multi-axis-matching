# Matching Engine と Parametric Search の違い

この文書は、multi-axis-matching が通常のパラメータ検索や DB 検索と何が同じで、何が違うのかを整理するための上位設計メモです。

## 1. 先に結論
候補収集の段階だけ見ると、multi-axis-matching はかなり **高機能な検索 + 再ランキング** に近いです。

ただし、本質的な違いは後段にあります。

- 通常の検索は、事前定義された属性に対して条件をかける
- multi-axis-matching は、入力ごとに評価関数を組み立て、候補を再評価する

つまり違いの核心は、検索そのものよりも **評価関数の可変性** と **unknown / conflict / hard violation の分離** にあります。

---

## 2. 通常の parametric search
例: 靴検索、EC 検索、DB 検索

### 特徴
- 属性は事前定義されている
- 条件は固定スキーマに落ちる
- 一致判定は基本的に yes/no
- 並び替えは価格順、人気順、レビュー順など既定

### 典型例
- サイズ = 27.0
- 色 = 黒
- 価格 <= 10000
- ブランド = Nike

この方式は、条件が列として明確な領域では非常に強いです。

---

## 3. multi-axis-matching の現在地
現在の multi-axis-matching は、次の2段階に分かれています。

### 3-1. 候補収集
- query understanding
- 検索条件抽出
- Google Places search / location bias
- retrieve

この部分は、既存の検索システムにかなり近いです。

### 3-2. 候補評価
- hard constraints と soft preferences の分離
- 軸ごとの score / status / reason
- unknown を 0 点扱いしない
- conflict と unknown を分離する
- aggregate で総合順位を決める

この後段が、通常の検索と大きく違います。

---

## 4. 何が違うのか

### 4-1. 評価関数が固定ではない
通常検索:
- 価格フィルタ
- ブランドフィルタ
- 人気順

multi-axis-matching:
- 何が hard constraint か
- 何が soft preference か
- どの軸をどれくらい重く見るか
- unknown をどう扱うか

を、入力ごとに変えることができます。

### 4-2. 不一致と不明を分ける
通常検索では値がなければ除外・残存・補完のどれかになりがちです。

multi-axis-matching は設計上、少なくとも次を分けます。
- supported
- conflict
- unknown
- hard_constraint_violation

これは情報が不完全な候補を扱う際に重要です。

### 4-3. 候補の説明可能性が高い
通常検索の結果は、なぜ1位かが曖昧になりやすいです。

multi-axis-matching では、少なくとも将来的には次を返せます。
- 軸別スコア
- 軸別理由
- missing_information
- source metadata

---

## 5. ただし、まだ検索型に近い部分
現状の system は、まだ完全に新しい型になっているわけではありません。

### 現在かなり検索寄りな点
- 候補側データはまだ薄い
- 候補収集は Google Places のような検索 API に依存
- 候補表現は半構造化に留まる
- 広告主 / 提供者側の「解決できる悩み」の記述が未整備

つまり現在は、

**検索は従来型に近く、評価が新しい**

という段階です。

---

## 6. 将来的に本当に違うものにするには
通常検索との差をさらに明確にするには、次が必要です。

### 6-1. 候補側の問題解決記述
候補が単なる店舗データではなく、
- どんな悩みに効くか
- どんな条件なら不向きか
- どこまで対応できるか

を持つ必要があります。

### 6-2. 問題タイプごとの評価関数
restaurant, clinic, product, legal support などで、
評価軸や hard/soft の意味が変わる必要があります。

### 6-3. オーガニック回答との比較基準
候補同士の比較だけでなく、
- 広告や推薦が無い場合の通常回答より優れているか

を測る基準が必要です。

### 6-4. downstream 計測
- 推薦後の行動
- コンバージョン
- 満足度
- false positive

などの下流計測が必要です。

---

## 7. システムの大枠

### 現在
1. Query understanding
2. Candidate collection
3. Normalization
4. Multi-axis evaluation
5. Ranking

### 将来像
1. User problem structuring
2. Candidate collection from multiple sources
3. Candidate-side solution catalog structuring
4. Problem-specific evaluation function construction
5. Multi-axis evaluation and ranking
6. Explanation / traceability
7. Outcome measurement
8. Economic layer (pricing / quality control / marketplace)

---

## 8. 要するに何か
要するに、この system は

- ただの検索ではない
- しかし候補収集部分はまだかなり検索に近い
- 本質は、検索後に可変の評価関数で意味的な適合度を評価するところにある

という位置づけです。

したがって、今後の実装優先順位は
1. 候補収集の改善
2. 候補側意味記述の構造化
3. 評価関数の問題タイプ別化
4. 下流計測

の順で考えるのが自然です。
