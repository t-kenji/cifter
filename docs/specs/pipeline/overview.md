# パイプライン

処理順は次のとおり。

> 入力列挙 -> 条件分岐前処理 -> tree-sitter 解析 -> 抽出 -> text/json render -> 出力

## 入力列挙

- `[inputs...]` と `--files-from` を結合する
- file はそのまま扱う
- dir は再帰走査し、C/C++ 系拡張子だけを対象にする
- path は正規化、重複除去し、絶対 path 昇順で処理する
- dir 走査は逐次列挙を前提とし、木全体を一括保持しない

## parse

- file 単位で前処理と tree-sitter 解析を行う
- 同一 run 内では `(path, defines, language)` ごとに parse 結果を再利用する
- `route` の DSL 解析は run 前段で 1 回だけ行う

## 抽出

- `function` は関数全体
- `flow` は制御構造骨格と `--track` 一致文
- `route` は指定 route に沿う枝
- 複数 file、複数一致を順に `ExtractionItem` へ積む
- 既定では未一致 file を warning として記録し、`--strict-inputs` 指定時だけ失敗させる

## render

- text と json は同じ `ExtractionItem` 集合から生成する
- text は複数 item のとき `command`、`symbol`、`route`、行範囲を含む見出しを付ける
- json は安定キーで構造化シリアライズする
