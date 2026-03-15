# cifter

`cifter` は、C/C++ の関数実装を機械的かつ高速に抽出する CLI です。重い推論や意味解析は行わず、`tree-sitter` ベースで読める範囲を整理して返します。

## v0 の対象

- 単一 `--source` ファイルからの抽出
- `function` / `flow` / `path` の 3 サブコマンド
- 行番号付き text 出力
- `-D NAME[=VALUE]` による条件分岐評価

## non-goals

- ディレクトリ走査
- JSON 出力
- LLM 連携
- 意味解析
- データフロー解析
- CFG 構築

## インストールと実行

開発用:

```sh
uv sync
uv run cift --help
```

配布物から:

GitHub Release から `wheel` または `sdist` を取得して install します。

```sh
python -m pip install ./cifter-0.1.0-py3-none-any.whl
cift --help
python -m cifter --help
```

モジュール実行:

```sh
uv run python -m cifter --help
```

旧 `python -m cift` と `import cift` の互換は提供しません。

install 後の最小確認:

```sh
cift function --name FooFunction --source examples/demo.c
```

## サブコマンド

`function`:
指定した関数の実装全体をそのまま抽出します。

```sh
uv run cift function --name FooFunction --source examples/demo.c
```

`flow`:
制御構造の骨格だけを残します。`--track` で完全一致した文を追加保持します。

```sh
uv run cift flow --function FooFunction --source examples/demo.c --track state
uv run cift flow --function FooFunction --source examples/demo.c --track 'ctx->state'
```

`path`:
指定した分岐経路だけを細く取り出します。親構造は残し、route が終端に達したコンテナでは後続の通常文も残します。

```sh
uv run cift path --function FooFunction --source examples/demo.c --route 'case CMD_HOGE > if ret == OK'
uv run cift path --function FooFunction --source examples/demo.c --route 'case CMD_HOGE > else if ret == 11'
uv run cift path --function FlowOnlySample --source examples/demo.c --route 'else'
```

## `-D` / `--track` / `--route`

`-D`:

```sh
uv run cift function --name FooFunction --source examples/demo.c -D DEF_FOO -D ENABLE_BAR=1
```

`--track`:

- `state`
- `ctx->state`
- `a->b.c`

`--route`:

- `case CMD_HOGE`
- `case CMD_HOGE > if ret == OK`
- `case CMD_HOGE > else if ret == 11`
- `default`
- `else`

## 既知制約

- 入力は UTF-8 前提です
- `.h` は現状 C 扱いです
- `--route` は `case` / `default` / `if` / `else` / `else if` のみ対応します
- ループ経路、`goto` 横断、意味解析は v0 の対象外です
- `--track` は構文上の完全一致のみを扱い、名前解決やスコープ解析は行いません

## サンプル

`examples/demo.c` に、`function` / `flow` / `path` と条件分岐前処理を試すためのサンプルを置いています。

```sh
uv run cift function --name FooFunction --source examples/demo.c
uv run cift flow --function FooFunction --source examples/demo.c --track 'ctx->state'
uv run cift path --function FooFunction --source examples/demo.c --route 'case CMD_LOOP > if ret == OK'
```
