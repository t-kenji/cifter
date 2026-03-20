# 出力フォーマット

`cifter` の公開出力は `text` と `json` の 2 系統である。

## text

- 基本行は `<line_no>: <text>`
- 行番号は 1-based
- `flow` / `route` は省略区間に `...` を入れる
- 複数結果時は file 見出しを挿入する
- `--color` / `--no-color` は text だけに作用する

## json

- トップレベルは `tool_version`、`command`、`inputs`、`results`、`diagnostics`
- `results[*]` は `rendered_lines` と `rendered_text` を両方持つ
- text と json は同じ抽出結果集合を返す
