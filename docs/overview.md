# 開発者向け概要

`docs/specs/` は実行可能仕様の正本であり、`docs/` はその内容を人間向けに説明する補助文書です。
実装の背景、内部構造、責務分離、読み方を把握したい場合は、まず `docs/` を読む想定です。

## `docs/` と `docs/specs/` の違い

- `docs/specs/`: CLI 契約、データモデル、パイプライン、release 条件などの正本
- `docs/`: 開発者向けの解説、設計意図、内部構造、使い方ガイド

迷った場合の基本方針:

- 実装が従うべき契約を確認したいときは `docs/specs/`
- 実装や設計の考え方を理解したいときは `docs/`

## どの文書を読むか

- 全体像を知りたい: [architecture.md](architecture.md)
- 処理の流れを追いたい: [pipeline.md](pipeline.md)
- 共有型の役割を知りたい: [data-model.md](data-model.md)
- CLI の使い分けを知りたい: [cli.md](cli.md)
- route DSL を使いこなしたい: [route-dsl.md](route-dsl.md)
- 性能設計と benchmark の見方を知りたい: [performance.md](performance.md)
- release 手順を確認したい: [release.md](release.md)

## 推奨読書順

全体像から読む場合:

1. [architecture.md](architecture.md)
2. [pipeline.md](pipeline.md)
3. [data-model.md](data-model.md)
4. [cli.md](cli.md)

route DSL を深掘りする場合:

1. [route-dsl.md](route-dsl.md)
2. [cli.md](cli.md)
3. [specs/route-dsl.md](specs/route-dsl.md)

性能観点を確認する場合:

1. [performance.md](performance.md)
2. [pipeline.md](pipeline.md)
3. [architecture.md](architecture.md)

## 実装の見取り図

- `cli`: 公開エントリポイント。引数解釈と終了コードを担当する
- `run`: 入力列挙、parse 再利用、複数 file 実行、run 結果集約を担当する
- `parser` / `preprocessor`: file 単位の前処理と tree-sitter 解析を担当する
- `extract_function` / `extract_flow` / `extract_route`: 抽出戦略の違いを担当する
- `render_text` / `render_json`: 同じ中間表現から出力形式を変換する
- `model`: 層をまたいで使う共有型を定義する
