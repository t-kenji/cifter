# CLI

この文書は、公開 CLI の契約を列挙するというより、「どのコマンドをどう使い分けるか」を説明します。
厳密な正本は [specs/configuration.md](specs/configuration.md) を参照してください。

## コマンドの選び分け

### `function`

関数全体を読みたいときに使います。

- 使いどころ: 実装全体をそのまま確認したい
- 向いている場面: まず関数の全体像を把握したいとき
- 形式: `cift function <symbol> [inputs...]`

### `flow`

制御構造の骨格を読みたいときに使います。

- 使いどころ: `if`、`switch`、loop の流れをざっと見たい
- 向いている場面: 関数全体は長いが、分岐の構造だけを早く追いたいとき
- 形式: `cift flow <symbol> [inputs...] --track <path>...`

`--track` を使うと、特定の変数やアクセスパスに関係する文を骨格に追加できます。

### `route`

特定の分岐だけを見たいときに使います。

- 使いどころ: ある `if` の枝、ある `case` の枝だけを確認したい
- 向いている場面: 条件分岐の一部だけを focused に読みたいとき
- 形式: `cift route <symbol> [inputs...] (--route <route>... | --infer-from-line <line>)`

`route` は「分岐の通り道」を文字列で指定するコマンドです。
詳細は [route-dsl.md](route-dsl.md) を参照してください。

`--infer-from-line` を使うと、単一 file の中で指定行を含む最も深い branch path を推論して、その route をそのまま実行できます。

## 共通オプションの整理

### 入力関連

- `[inputs...]`: file または dir
- `--files-from <path>`: path 一覧 file
- `--files-from -`: 標準入力から path 一覧を読む

`cifter` 自体は検索ツールではないため、候補 file の絞り込みは外部ツールへ委譲する前提です。

### 出力関連

- `--format auto|text|json`
- `--color` / `--no-color`

`auto` は、画面へ直接出すときは text、パイプやリダイレクトで受け渡すときは json を返します。

### 厳格性関連

- `--strict-inputs`

既定では未一致 file は warning として飛ばします。
全件一致を要求したい場合だけ `--strict-inputs` を使います。

### 前処理関連

- `--language auto|c|cpp`
- `-D NAME[=VALUE]`

`-D` は条件分岐前処理に渡すマクロ定義です。

## 運用意図

- file 候補の絞り込みは外部ツールへ委譲する
- `cifter` は抽出と JSON/text 出力に責務を絞る
- `function` / `flow` / `route` の違いは見た目ではなく抽出戦略の違いである

## 使い始めの順番

迷ったときは次の順で使うのが分かりやすいです。

1. `function` で関数全体を見る
2. `flow` で骨格だけを見る
3. 必要なら `route` で特定の枝だけを抜く
