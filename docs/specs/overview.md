# 仕様概要

本ディレクトリは `cifter` v1 の実行可能仕様の正本である。
README や `docs/` より優先する。

## 文書の優先順位

1. この文書
2. [configuration.md](configuration.md)
3. [route-dsl.md](route-dsl.md)
4. [data-model/overview.md](data-model/overview.md)
5. [pipeline/overview.md](pipeline/overview.md)
6. [release.md](release.md)
7. [../overview.md](../overview.md)

## 対象範囲

- 対象言語は C/C++ のみ
- 公開サブコマンドは `function` / `flow` / `route` のみ
- 入力は file / dir / `--files-from` / stdin
- 出力形式は `text` と `json`
- 他ツールで絞った候補ファイル集合に対する高速 slice を主目的とする

## 命名方針

- 配布名は `cifter-cli`
- 実行コマンドは `cift`
- Python モジュール実行は `python -m cifter`
- import package は `cifter`

## トレーサビリティ原則

- すべての抽出結果は元ソースの 1-based 行番号を保持する
- `flow` / `route` は必要最小限の再構成を許可するが、対応する元行番号は失わない
- JSON と text は同じ抽出結果集合を異なる表現で返す

## Non-Goals

- オールインワン検索エンジン
- LLM 連携
- 意味解析
- データフロー解析
- CFG 構築
