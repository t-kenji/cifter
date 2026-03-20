# cifter

`cifter` は、C/C++ のコードから必要な部分だけを抜き出す CLI です。
特に、検索ツールで候補ファイルを絞ったあとに「関数を丸ごと見たい」「分岐の流れだけ見たい」「特定の分岐だけ見たい」という場面を軽くします。

## 概要

- `function`: 関数をそのまま抜き出す
- `flow`: 分岐や繰り返しの流れを見やすく抜き出す
- `route`: 特定の分岐だけを抜き出す
- 入力はファイル / ディレクトリ / `--files-from` / 標準入力から受け取れます
- 出力は text と JSON に対応している
- 対象言語は C / C++

`route` では、分岐の通り道を文字列で指定する書き方を使います。
たとえば `else-if[value == 10]` や `case[CMD_OK]/else` のように指定できます。

`--format auto` を使うと、画面に直接表示するときは text、パイプや `>` で受け渡すときは JSON を返します。

## Why cifter

- `grep` だけだと、関数全体や分岐の前後関係までは見えにくい
- IDE を開くほどではないけれど、必要なコードの文脈は確認したい
- 大きい C/C++ リポジトリで、候補を絞ったあとに読みやすい形で抜き出したい
- 人間向けの text と、後段処理しやすい JSON の両方を同じコマンドで取りたい

`cifter` は検索ツールの代わりではなく、その後ろで使う「切り出し」に特化したツールです。

## Installation

```sh
python -m pip install cifter-cli
```

確認:

```sh
cift --version
cift --help
python -m cifter --version
```

## README 内サンプルソース

README では次の最小サンプルを使います。
同じ内容を [examples/quickstart/decide_mode.c](examples/quickstart/decide_mode.c) に置いています。

```c
int DecideMode(int value)
{
    int state = 0;

    if (value > 10) {
        state = 1;
    } else if (value == 10) {
        state = 2;
    } else {
        state = 3;
    }

    return state;
}
```

## Quick Start

関数全体を丸ごと見たいとき:

```sh
cift function DecideMode examples/quickstart/decide_mode.c --format text
```

```text
 1: int DecideMode(int value)
 2: {
...
14: }
```

関数の本体をそのまま確認したいときに使います。

分岐の流れをざっと見たいとき:

```sh
cift flow DecideMode examples/quickstart/decide_mode.c --track state --format text
```

```text
 1: int DecideMode(int value)
 2: {
 3:     int state = 0;
...
13:     return state;
```

`state` に関係する行と、`if / else if / else` の骨格を残して読みやすくします。

特定の分岐だけを見たいとき:

```sh
cift route DecideMode examples/quickstart/decide_mode.c --route 'else-if[value == 10]' --format text
```

```text
 1: int DecideMode(int value)
 2: {
...
 7:     } else if (value == 10) {
 8:         state = 2;
...
13:     return state;
```

`else if` の枝だけを確認したい、のような場面に向いています。

検索結果をそのまま渡したいとき:

```sh
rg -l 'MirrorValue' examples/multi_input | cift function MirrorValue --files-from - --format json
```

`--files-from -` を使うと、標準入力から path 一覧を受け取れます。

## Examples

最小の単一 file:

- [examples/quickstart/decide_mode.c](examples/quickstart/decide_mode.c)

C の網羅例:

- [examples/showcase/c/control_flow.c](examples/showcase/c/control_flow.c)
- [examples/showcase/c/preprocess.c](examples/showcase/c/preprocess.c)

```sh
cift flow DispatchCommand examples/showcase/c/control_flow.c --track 'ctx->state' --track ret --highlight --format text
cift route DispatchCommand examples/showcase/c/control_flow.c \
  --route 'case[CMD_HOGE]/else-if[ret == RETRY_LATER]' \
  --route 'case[CMD_LOOP]/while/if[ctx->retry_count == 1]' \
  --format text
cift function ConfigureBuild examples/showcase/c/preprocess.c \
  -D ENABLE_FAST_PATH -D FEATURE_LEVEL=2 --format text
```

C++ の例:

- [examples/showcase/cpp/member_workflow.cpp](examples/showcase/cpp/member_workflow.cpp)
- [examples/showcase/cpp/route_cases.cpp](examples/showcase/cpp/route_cases.cpp)

```sh
cift function Process examples/showcase/cpp/member_workflow.cpp --format text
cift function PickNonZero examples/showcase/cpp/member_workflow.cpp --format text
cift route RouteMode examples/showcase/cpp/route_cases.cpp --route else --format text
cift route QualifiedDispatch examples/showcase/cpp/route_cases.cpp --route 'case[ns::State::Busy]' --format text
```

複数入力の例:

- [examples/multi_input/alpha.c](examples/multi_input/alpha.c)
- [examples/multi_input/beta.cpp](examples/multi_input/beta.cpp)
- [examples/multi_input/targets.txt](examples/multi_input/targets.txt)

```sh
cift function MirrorValue examples/multi_input --format json
cift function MirrorValue --files-from examples/multi_input/targets.txt --format json
```

## Commands

`function`

- 関数を丸ごと読みたいときに使います
- 形式: `cift function <symbol> [inputs...]`

`flow`

- 分岐や繰り返しの流れをざっと確認したいときに使います
- 形式: `cift flow <symbol> [inputs...] --track <path>...`
- `--highlight` を付けると、`--track` に一致した箇所を text 出力でも強調できます

`route`

- 特定の分岐だけを見たいときに使います
- 形式: `cift route <symbol> [inputs...] --route <route>...`
- `--route` は「分岐の通り道を文字列で指定する書き方」です

共通オプション:

- `--files-from <path>` または `--files-from -`
- `--language auto|c|cpp`
- `-D NAME[=VALUE]`
- `--format auto|text|json`
- `--color` / `--no-color`
- `--strict-inputs`

## Limitations

- 対象言語は C/C++ のみです
- `cifter` 自体は検索ツールではありません。候補の絞り込みは `rg` / `fd` / `ast-grep` などと併用します
- 意味解析や、完全な実行経路解析は行いません
- `route` は一般的な CFG path ではなく、cifter 独自の route 指定に沿って抽出します
- 出力は tree-sitter と前処理結果に依存するため、複雑なマクロや壊れたコードでは `degraded` 診断や抽出失敗が起こることがあります

## Migration

| v0                                                  | v1                                         |
| --------------------------------------------------- | ------------------------------------------ |
| `cift function --name Foo --source a.c`             | `cift function Foo a.c`                    |
| `cift flow --function Foo --source a.c`             | `cift flow Foo a.c`                        |
| `cift path --function Foo --source a.c --route ...` | `cift route Foo a.c --route ...`           |
| 単一 file 前提                                      | `file` / `dir` / `--files-from` / 標準入力 |

補足:

- 同じ file に同名関数が複数ある場合は、ソースに書かれた順で複数結果を返します
- 未一致 file は既定で warning として飛ばします
- 全件一致を要求する場合だけ `--strict-inputs` を付けます

## License

MIT License です。詳細は [LICENSE](LICENSE) を参照してください。

## Docs

利用者向け:

- route の書き方: [docs/route-dsl.md](docs/route-dsl.md)
- CLI の詳しい仕様: [docs/cli.md](docs/cli.md)

開発者向け:

- 文書の入口: [docs/overview.md](docs/overview.md)
