# CLI

この文書は公開 CLI の開発者向け整理です。利用者向け導線は `README.md`、正本仕様は `docs/specs/configuration.md` を参照します。

## 共通

- エントリポイントは `cift`
- モジュール実行は `python -m cifter`
- `--version` は `cift {version}` を表示して終了します
- `--source PATH` は必須です
- `-D NAME[=VALUE]` は複数回指定できます
- 出力は行番号付き text です
- `--color` / `--no-color` は各抽出サブコマンドで指定できます
- 色指定を省略した場合は、標準出力が TTY のときだけ色付きになります

## サブコマンド

`function`:

- 必須引数は `--name`
- `--color` / `--no-color` で出力のシンタックスハイライトを制御できます
- 指定関数の実装全体をそのまま抽出します

`flow`:

- 必須引数は `--function`
- 制御構造の骨格だけを残します
- `--track` は複数回指定できます
- `--color` / `--no-color` で出力のシンタックスハイライトを制御できます
- `--track` 一致文は骨格に追加して残します

`path`:

- 必須引数は `--function`
- 必須引数は `--route`
- `--color` / `--no-color` で出力のシンタックスハイライトを制御できます
- route は `>` でネストを下る最小 DSL です
- `case LABEL` / `default` / `if CONDITION` / `else` / `else if CONDITION` を扱います

## 終了コード

- Typer の引数エラーは終了コード `2`
- 抽出失敗、曖昧一致、未一致、DSL 不正は終了コード `1`
- 正常終了は終了コード `0`

## エラーモデル

- 利用者向けの失敗は `CiftError` に集約します
- CLI は `CiftError.message` を標準エラーへ出し、終了コード `1` で終了します
- route 不正、関数未検出、曖昧一致、前処理ディレクティブ不整合が主な失敗要因です

## 代表例

```sh
cift --version
cift function --name FooFunction --source examples/demo.c
cift flow --function FooFunction --source examples/demo.c --track 'ctx->state'
cift path --function FooFunction --source examples/demo.c --route 'case CMD_HOGE > else if errno == EINT'
```
