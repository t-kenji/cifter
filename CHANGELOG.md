# CHANGELOG

利用者から見える変更だけを記録する。

## [Unreleased]

## [0.2.0] - 2026-03-16

- 抽出結果へシンタックスハイライトを追加し、`--color` / `--no-color` で制御できるようにした
- `cift --version` と `python -m cifter --version` を追加

## [0.1.0] - 2026-03-16

- 配布名を `cifter-cli` へ変更し、PyPI 公開向けの project metadata を追加
- README を利用者向けに再構成し、Quick Start と install 導線を追加
- 開発者向け `docs/` に CLI、出力、パイプライン、データモデル、アーキテクチャ、release 運用の文書を追加
- `function` / `flow` / `path` の 3 サブコマンドを追加
- `-D NAME[=VALUE]` による条件分岐評価を追加
- 行番号付き text 出力と `python -m cifter` 実行を追加
