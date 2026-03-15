# 仕様概要

本ディレクトリは `cifter` の実行可能仕様の正本である。
実装や README より優先して参照する。

## 文書の優先順位

1. この文書
2. [configuration.md](/home/tkenji/Repos/cifter/docs/specs/configuration.md)
3. [release.md](/home/tkenji/Repos/cifter/docs/specs/release.md)
4. [data-model/overview.md](/home/tkenji/Repos/cifter/docs/specs/data-model/overview.md)
5. [pipeline/overview.md](/home/tkenji/Repos/cifter/docs/specs/pipeline/overview.md)
6. [docs/overview.md](/home/tkenji/Repos/cifter/docs/overview.md)

## 対象範囲

- 対象言語は C/C++ のみ
- 公開サブコマンドは `function` / `flow` / `path` のみ
- 入力は単一の `--source` ファイル 1 個のみ
- 出力形式は text のみ

## 命名方針

- 配布名は `cifter-cli`
- 実行コマンドは `cift`
- Python モジュール実行は `python -m cifter`
- import package は `cifter`
- 旧 Python パッケージ名 `cift` の互換は提供しない

## トレーサビリティ原則

- すべての抽出結果は元ソースの 1-based 行番号を保持する
- 条件分岐前処理で削除した行は空行化して行番号を維持する
- `flow` と `path` は必要最小限の再構成を許可するが、対応する元行番号は失わない
- `path` は選択した枝の親構造と route 終端コンテナ内の直列文脈を保ったまま再構成する

## Non-Goals

- LLM 連携
- 意味解析
- データフロー解析
- CFG 構築
- JSON 出力
- ディレクトリ走査
