# 性能

`cifter` は、リポジトリ全体を賢く探索することよりも、「候補 file 集合に対して素早く切り出すこと」を重視します。

## 何を重視しているか

- 全体探索より、絞り込み後の file 集合への処理速度
- 同一 run 内での parse 再利用
- dir 入力や `--files-from` での多件処理
- 抽出と render の責務分離による無駄な再計算の抑制

つまり、`rg` や `fd` で候補を絞ったあとに `cifter` を流す使い方を最適化対象にしています。

## 性能の非目標

- オールインワン検索エンジンとしての最適化
- 意味解析ベースの重い解析
- CFG 全探索やデータフロー解析のような高コスト機能

これらは意図的に対象外です。

## 開発者が見るべき観点

### parser 再利用

- 同一 run 内で同じ file を不要に再 parse していないか
- language / defines の違いだけで再利用条件が崩れていないか

### 入力列挙コスト

- dir 走査が不要に全件保持になっていないか
- `--files-from` と argv の統合で無駄な重複が増えていないか

### 抽出器コスト

- `function` / `flow` / `route` の各抽出器が不要な全探索をしていないか
- route の segment 解釈を file ごとに繰り返していないか

### render コスト

- text と json のために同じ情報を二重計算していないか
- `ExtractedLine` からの変換が余計な再構築を増やしていないか

## benchmark

計測コマンド:

```sh
uv run python tools/benchmark_phase3.py
```

## 計測対象

- `parse_source(c)` / `parse_source(cpp)`
- `function(c)` / `flow(c)` / `route(c)`
- `function(cpp)` / `flow(cpp)` / `route(cpp)`
- `dir` 入力
- `--files-from` 多件処理
- 未一致 file 混在
- parser 再利用の有無

## 性能変更時の確認ポイント

- 多件入力で極端に遅くなっていないか
- parse 再利用が壊れていないか
- route 追加や renderer 変更で run 全体の時間が不自然に増えていないか
- 想定運用である「絞り込み後の候補 file 集合」に対して体感が悪化していないか
