# 開発者向け概要

`docs/specs/` は実行可能仕様の正本であり、この `docs/` は実装理解と運用理解のための開発者向け補助文書です。仕様判断は先に `docs/specs/` を確認し、その後に本ディレクトリで実装構造を追います。

## 文書一覧

- [cli.md](/home/tkenji/Repos/cifter/docs/cli.md): 公開コマンド、オプション、終了コード、代表的な失敗
- [output-format.md](/home/tkenji/Repos/cifter/docs/output-format.md): 行番号付き text 出力の契約
- [pipeline.md](/home/tkenji/Repos/cifter/docs/pipeline.md): 前処理からレンダリングまでの処理順と責務
- [data-model.md](/home/tkenji/Repos/cifter/docs/data-model.md): 抽出結果と route / track 周辺の主要データ型
- [architecture.md](/home/tkenji/Repos/cifter/docs/architecture.md): モジュール責務と依存方向
- [performance.md](/home/tkenji/Repos/cifter/docs/performance.md): フェーズ3の性能計測手順と現状記録
- [release.md](/home/tkenji/Repos/cifter/docs/release.md): release 手順と PyPI publish 運用

## 実装の見取り図

- `cli`: Typer ベースの公開エントリポイント
- `preprocessor`: 条件分岐前処理
- `parser`: tree-sitter 解析、言語判定、関数探索
- `extract_function`: 関数全体抽出
- `extract_flow`: 制御骨格抽出
- `extract_path`: route 抽出
- `render`: 行番号付き text レンダリング
- `model`: 入出力モデルと DSL 正規化
- `errors`: 利用者向け失敗メッセージ

## 参照順

- 正本仕様: [docs/specs/overview.md](/home/tkenji/Repos/cifter/docs/specs/overview.md)
- 開発者運用: [release.md](/home/tkenji/Repos/cifter/docs/release.md)
