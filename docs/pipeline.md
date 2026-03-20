# パイプライン

この文書は、`cifter` が入力を受けてから出力を返すまでに、どこで何が決まるかを説明します。

処理順は次のとおりです。

> 入力列挙 -> 条件分岐前処理 -> tree-sitter 解析 -> 抽出 -> render -> 出力

## 1. 入力列挙と正規化

入力は次の 3 系統から入ります。

- 位置引数 `[inputs...]`
- `--files-from <path>`
- `--files-from -`

run 層はこれらを 1 つの path 集合に統合し、次を行います。

- file / dir を解決する
- dir は再帰走査して C/C++ 系拡張子だけを対象にする
- path を正規化する
- 重複 path を除去する
- 絶対 path 昇順で deterministic に処理する

この段階で「どの file を対象にするか」が決まります。

## 2. 前処理と parse

各 file は file 単位で次の処理を受けます。

1. 入力の正規化
2. 条件分岐前処理
3. tree-sitter parse
4. 言語解決
5. parse quality 診断生成

この結果が `ParsedSource` です。

ここで決まるのは「ソースをどう読むか」であり、「どの行を返すか」ではありません。

## 3. run 内再利用

同一 run 内では、同じ `(path, defines, language)` に対する parse 結果を再利用します。

これにより、複数 command を 1 run 内で繰り返すわけではなくても、同じ file を重複処理するコストを避けられます。
また、route DSL の解析も run 前段で 1 回だけ行います。

## 4. 抽出戦略の選択

parse 済み file ごとに、run 層が command に応じて抽出器を呼び分けます。

### `function`

- 対象関数全体を返す
- 最も直接的で、構造の省略を行わない

### `flow`

- `if` / `switch` / loop などの制御構造骨格を残す
- `--track` に一致する文を追加で残す
- 必要のない区間は `...` で省略する

### `route`

- route DSL に沿って枝をたどる
- その route に関係する構造だけを残す
- 一般的な CFG path 全探索は行わない

この段階で「どの line を残すか」が決まります。

## 5. 中間表現への変換

抽出器の返り値は、最終的に `ExtractedLine` 集合として扱われます。
run 層はこれを `ExtractionItem` にまとめ、さらに run 全体を `RunResult` にまとめます。

ここで管理する情報は次のとおりです。

- file
- symbol
- span
- lines
- diagnostics
- routes
- command

この中間表現が text/json の共通入力です。

## 6. render

render 層は `ExtractionItem` 集合を別の見せ方へ変換します。

### text

- 行番号付きで表示する
- 複数結果時は見出しを追加する
- `flow` / `route` の省略区間は `...` で表す
- 必要なら color を付ける

### json

- 同じ抽出結果を安定キーの構造化 JSON で返す
- 後段ツールやスクリプトが扱いやすい形にする

## 7. warning と error の扱い

run 層は file 単位の出来事を run 全体の診断へ集約します。

代表的な扱いは次のとおりです。

- 未一致 file: 既定では warning
- `--strict-inputs` 下の未一致 file: error
- route DSL 不正: error
- parse 不能、入力不正: error
- 結果が 0 件: `no_results` error

つまり、抽出器が単一 file の成否を決め、run 層が「run 全体として成功か」を決めます。

## 8. 開発時に見るべき観点

- 入力追加の変更は、入力列挙段で完結しているか
- parse に関わる変更は、抽出器へ責務が漏れていないか
- 新しい抽出戦略を入れる場合、`ExtractedLine` ベースに寄せられているか
- text/json の差分が renderer だけに閉じているか
- warning / error の意味が run 層で一貫しているか
