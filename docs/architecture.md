# アーキテクチャ

`cifter` は、C/C++ ソースから必要な部分だけを抜き出す CLI です。
内部構造は「入力解釈」「解析」「抽出」「表示」を分離し、公開コマンドの見た目よりも、抽出戦略の違いを中心に組み立てています。

## システム全体像

大まかな処理は次の 6 層です。

1. CLI 層
2. run 層
3. parse / preprocess 層
4. extraction 層
5. render 層
6. model 層

この分割により、CLI の形、抽出ロジック、表示形式をそれぞれ独立して変更しやすくしています。

## 層ごとの責務

### CLI 層

- 公開コマンド `function` / `flow` / `route` を受ける
- 引数を解釈し、run 層へ request を渡す
- text / json のどちらを出すかを決める
- 終了コードを最終的に決める

CLI 層は「何をしたいか」を受け取るだけで、解析や抽出の中身は持ちません。

### run 層

- 入力 path の列挙、正規化、重複除去を行う
- file ごとの parse を再利用する
- `function` / `flow` / `route` の各抽出器を呼び分ける
- 結果を `RunResult` に集約する
- warning / error を run 単位で管理する

run 層は、CLI と抽出器の間にある調停層です。
複数 file 実行、未一致 file の扱い、`--strict-inputs`、`no_results` などの run 全体の振る舞いはここで決まります。

### parse / preprocess 層

- file を読み、前処理をかける
- tree-sitter で構文木を作る
- 言語自動判定や parse quality 診断を作る
- 抽出器が使う `ParsedSource` を返す

この層は「ソースを読める形にする」責務だけを持ちます。
どの行を残すかは決めません。

### extraction 層

- `function`: 関数全体を返す
- `flow`: 制御構造の骨格と `--track` 一致文を返す
- `route`: 指定 route に沿った枝だけを返す

ここでの主責務は、どの source line を残すかを決めることです。
表示形式そのものは render 層に任せます。

### render 層

- `ExtractionItem` を人間向け text に変換する
- 同じ `ExtractionItem` を JSON に変換する
- color や複数結果見出しを text 側で扱う

text と json は別 renderer ですが、元になる抽出結果集合は同じです。

### model 層

- 各層をまたぐ共有型を持つ
- run 結果、抽出結果、diagnostic、route segment などを表現する
- route / track の内部表現を共通化する

model 層は依存の中心であり、できるだけ安定させるべき層です。

## データの流れ

1. CLI が利用者入力を受ける
2. run 層が対象 file 集合を決める
3. parse / preprocess 層が file を `ParsedSource` に変換する
4. extraction 層が `ExtractedLine` 集合を作る
5. run 層が `ExtractionItem` と `RunResult` にまとめる
6. render 層が text または json に変換する

重要なのは、抽出器が直接 CLI 表示を作らないことです。
抽出器は source line を選び、render 層が見せ方を決めます。

## モジュール責務

- `src/cifter/cli.py`: 引数解釈、出力形式選択、終了コード
- `src/cifter/run.py`: 入力列挙、parse 再利用、結果集約
- `src/cifter/parser.py`: 言語判定、tree-sitter parse、関数探索
- `src/cifter/preprocessor.py`: 条件分岐前処理
- `src/cifter/extract_function.py`: 関数全体抽出
- `src/cifter/extract_flow.py`: 制御骨格抽出
- `src/cifter/extract_route.py`: route 抽出
- `src/cifter/render_text.py`: text 表示
- `src/cifter/render_json.py`: JSON 表示
- `src/cifter/model.py`: 共通型

## 依存方向

- `cli -> run -> parser / extract_* / render_*`
- `extract_* -> parser / model / omission / tree_helpers`
- `render_* -> model`
- `model` は他層へ依存しない

依存方向を一方向に保つことで、抽出戦略と表示形式を分離しています。

## `function` / `flow` / `route` の違い

この 3 つは UI だけの違いではなく、抽出戦略が異なります。

- `function`: 関数本体をそのまま読むための抽出
- `flow`: 分岐と繰り返しの骨格を読むための抽出
- `route`: 特定の枝だけを選択するための抽出

`route` は検索エンジンではなく selection 機能です。
つまり「どこにあるかを探す」よりも、「見つけた関数の中でどの枝を残すか」を扱います。

## 開発者が守るべき不変条件

- 行番号トレーサビリティを失わない
- text と json は同じ抽出結果集合を別表現で返す
- run 層が複数 file 実行の責務を持ち、抽出器は単一 `ParsedSource` に集中する
- `route` は CFG 全探索ではなく、route DSL に沿う逐次 selection として扱う
