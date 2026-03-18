# CLI

この文書は公開 CLI の開発者向け整理です。利用者向け導線は `README.md`、正本仕様は `docs/specs/configuration.md` を参照します。

## 共通

- エントリポイントは `cift`
- モジュール実行は `python -m cifter`
- `--version` は `cift {version}` を表示して終了します
- `--source PATH` は必須です
- `--language auto|c|cpp` を各抽出サブコマンドで指定できます
- `-D NAME[=VALUE]` は複数回指定できます
- 出力は行番号付き text です
- `--color` / `--no-color` は各抽出サブコマンドで指定できます
- 色指定を省略した場合は、標準出力が TTY のときだけ色付きになります
- `.h` と未知拡張子では `auto` が parse quality の高い言語を選びます
- parse quality が `degraded` のときだけ標準エラーへ診断を出します
- active な `#pragma` / `#error` は保持したまま解析し、これだけでは `preprocess` 診断を出しません

## サブコマンド

`function`:

- 必須引数は `--name`
- `--language` で解析言語を固定できます
- `--color` / `--no-color` で出力のシンタックスハイライトを制御できます
- 指定関数の実装全体をそのまま抽出します

`flow`:

- 必須引数は `--function`
- `--language` で解析言語を固定できます
- 制御構造の骨格だけを残します
- `--track` は複数回指定できます
- `--highlight` を付けたときだけ `--track` 一致箇所を追加強調します
- `--color` / `--no-color` で出力のシンタックスハイライトを制御できます
- `--track` 一致文は骨格に追加して残します
- 省略された区間は `...` の合成行で表示します

`path`:

- 必須引数は `--function`
- `--route` は 1 個以上必須で、複数回指定できます
- `--language` で解析言語を固定できます
- `--color` / `--no-color` で出力のシンタックスハイライトを制御できます
- route は `/` 区切りの canonical DSL です
- segment は `case[...]` / `default` / `if[...]` / `else` / `else-if[...]` / `for` / `for[...]` / `while` / `while[...]` / `do-while` / `do-while[...]` を扱います
- 詳細は [docs/specs/path-route-dsl.md](/home/tkenji/Repos/cifter/docs/specs/path-route-dsl.md) を参照します
- 複数指定時は各 route を独立に解決し、結果を OR で union します
- 表示順は元ソース行順で、指定順には依存しません
- route 終端後は、その直後に続く通常文だけを残し、同じ階層で次の分岐文またはループ文に達した時点で打ち切ります
- 省略された区間は `...` の合成行で表示します

## 終了コード

- Typer の引数エラーは終了コード `2`
- 抽出失敗、未一致、DSL 不正は終了コード `1`
- 正常終了は終了コード `0`

## エラーモデル

- 利用者向けの失敗は `CiftError` に集約します
- CLI は `CiftError.message` を標準エラーへ出し、終了コード `1` で終了します
- route 不正、関数未検出、未一致、前処理ディレクティブ不整合が主な失敗要因です
- 成功時でも parse quality が `degraded` なら `quality[...]` と `repro:` を標準エラーへ出します
- `preprocess` 診断は、active 領域に本当に未対応な directive が残った場合だけ出します

## 代表例

```sh
cift --version
cift function --name FooFunction --source examples/demo.c
cift function --name HeaderCpp --source include/foo.h --language cpp
cift flow --function FooFunction --source examples/demo.c --track 'ctx->state'
cift path --function FooFunction --source examples/demo.c --route 'case[CMD_HOGE]/else-if[errno == EINT]'
cift path --function FooFunction --source examples/demo.c --route 'case[CMD_LOOP]/while[(ctx->retry_count < 2)]/if[(ctx->retry_count == 1)]' --route 'case[CMD_LOOP]/for'
```
