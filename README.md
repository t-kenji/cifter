# cifter

`cifter` は、C/C++ の関数実装を機械的かつ高速に抽出する CLI です。
`tree-sitter` で構文を捉え、行番号付き text として返します。重い意味解析や LLM 連携は行いません。

## 概要

- 単一の `--source` ファイルから抽出します
- 公開サブコマンドは `function` / `flow` / `path` の 3 つです
- 出力は元ソースと対応付け可能な行番号付き text です
- `-D NAME[=VALUE]` により条件分岐前処理を評価できます
- 出力先が TTY の場合は既定でシンタックスハイライトします

## Why cifter

- 関数全体をそのまま抜き出したい
- 分岐の骨格だけを見たい
- 特定の route だけを細く追いたい
- 元の行番号を失わずにレビューや調査へ貼りたい

## Installation

PyPI から install:

```sh
python -m pip install cifter-cli
```

最小確認:

```sh
cift --version
cift --help
python -m cifter --version
python -m cifter --help
```

GitHub Release の `wheel` / `sdist` から install することもできます。

```sh
python -m pip install ./cifter_cli-0.2.0-py3-none-any.whl
```

開発用:

```sh
uv sync
uv run cift --help
```

## Quick Start

サンプルソース:

```c
int FooFunction(int x)
{
    if (x > 0) {
        return 1;
    }

    return 0;
}
```

関数全体を抽出:

```sh
cift function --name FooFunction --source foo.c
```

出力:

```text
1: int FooFunction(int x)
2: {
3:     if (x > 0) {
4:         return 1;
5:     }
6:
7:     return 0;
8: }
```

## Commands

バージョン表示:

```sh
cift --version
python -m cifter --version
```

`function`:
指定した関数の実装全体をそのまま抽出します。レビュー対象の最小切り出しに向きます。

```sh
cift function --name FooFunction --source examples/demo.c
```

`flow`:
制御構造の骨格だけを残します。`--track` を付けると、完全一致したアクセスパスを含む文を追加保持します。

```sh
cift flow --function FooFunction --source examples/demo.c --track state
cift flow --function FooFunction --source examples/demo.c --track 'ctx->state'
```

`path`:
指定した route だけを細く抽出します。親構造は残し、route 終端に達したコンテナでは後続の通常文も残します。

```sh
cift path --function FooFunction --source examples/demo.c --route 'case CMD_HOGE > if ret == OK'
cift path --function FooFunction --source examples/demo.c --route 'case CMD_HOGE > else if errno == EINT'
cift path --function ElseRoute --source examples/demo.c --route 'else'
```

## Preprocessor / Track / Route

`-D`:
条件分岐前処理の評価に使うマクロを追加します。

```sh
cift function --name FooFunction --source examples/demo.c -D DEF_FOO -D ENABLE_BAR=1
```

`--track`:
`flow` で保持したいアクセスパスです。構文上の完全一致だけを扱います。

- `state`
- `ctx->state`
- `a->b.c`

`--route`:
`path` で辿る最小 DSL です。

- `case CMD_HOGE`
- `case CMD_HOGE > if ret == OK`
- `case CMD_HOGE > else if errno == EINT`
- `default`
- `else`

## Limitations

- 対象は C/C++ のみです
- 入力は単一ファイルのみです
- 出力形式は text のみです
- 入力文字コードは UTF-8 前提です
- `.h` は現状 C 扱いです
- `--route` は `case` / `default` / `if` / `else` / `else if` のみ対応です
- `--track` は名前解決やスコープ解析を行いません
- ループ経路、`goto` 横断、意味解析、CFG 構築、JSON 出力は対象外です

## Examples

リポジトリには `examples/demo.c` を含めています。

```sh
cift function --name FooFunction --source examples/demo.c
cift function --name FooFunction --source examples/demo.c --color
cift function --name FooFunction --source examples/demo.c --no-color
cift flow --function FooFunction --source examples/demo.c --track 'ctx->state'
cift path --function FooFunction --source examples/demo.c --route 'case CMD_LOOP > if ret == OK'
```

## Development

開発者向け文書は `docs/` にまとめています。

- [docs/overview.md](/home/tkenji/Repos/cifter/docs/overview.md)
- [docs/cli.md](/home/tkenji/Repos/cifter/docs/cli.md)
- [docs/output-format.md](/home/tkenji/Repos/cifter/docs/output-format.md)
- [docs/pipeline.md](/home/tkenji/Repos/cifter/docs/pipeline.md)
- [docs/data-model.md](/home/tkenji/Repos/cifter/docs/data-model.md)
- [docs/architecture.md](/home/tkenji/Repos/cifter/docs/architecture.md)
- [docs/release.md](/home/tkenji/Repos/cifter/docs/release.md)

仕様の正本は `docs/specs/` にあります。

## License

MIT License で配布します。詳細は `LICENSE` を参照してください。
