# CLI 仕様

## 共通

- `--version` は `cift {version}` を標準出力へ 1 行出力し、終了コード 0 で終了する
- 公開コマンドは `function` / `flow` / `route`
- `function` / `flow` / `route` の第 1 引数は必須 `symbol`
- 入力は追加位置引数 `[inputs...]` と `--files-from` から受ける
- `[inputs...]` は file または dir を受ける
- `--files-from <path>` は UTF-8 text とし、1 行 1 path を読む
- `--files-from -` は標準入力から path 一覧を読む
- `[inputs...]` と `--files-from` は併用できる
- 結合後の入力 path は正規化、重複除去、絶対 path 化し、絶対 path 昇順で処理する
- dir は再帰走査し、既定では C/C++ 系拡張子だけを対象にする
- `--language auto|c|cpp` を指定可能
- `-D NAME[=VALUE]` は複数回指定可能
- `--format auto|text|json` を指定可能
- `auto` は TTY なら `text`、非 TTY なら `json`
- ただし `--color` / `--no-color` を明示した `auto` は `text` として扱う
- `--color` / `--no-color` は text 出力だけに作用する
- `--strict-inputs` を指定すると、未一致 file が 1 件でもあれば終了コード 1 にする
- `text` は行番号付き表示、`json` は構造化結果を返す
- 複数入力時は複数結果を返してよい
- same-file 内の同名関数は source order で複数結果を返す
- 既定では未一致 file は warning として記録し、1 件以上結果があれば成功する
- `--files-from` の UTF-8 読み込み失敗は利用者向けエラーとして終了コード 1 に正規化する
- 1 件でも DSL 不正、抽出失敗、または `--strict-inputs` 下の未一致があれば終了コード 1
- Typer の引数エラーは終了コード 2

## `function`

- 形式は `cift function <symbol> [inputs...]`
- 対象関数の実装全体をそのまま返す

## `flow`

- 形式は `cift flow <symbol> [inputs...]`
- `--track` は複数回指定可能
- `--highlight` は highlight span を追加保持する
- 制御構造の骨格と `--track` 一致文を返す

## `route`

- 形式は `cift route <symbol> [inputs...] (--route <route>... | --infer-from-line <line>)`
- `--route` と `--infer-from-line` は排他
- `--route` は 1 個以上指定可能
- `--infer-from-line` は 1-based 行番号を 1 個だけ受ける
- `--infer-from-line` は単一 input file のときだけ指定できる
- `--infer-from-line` は指定 `symbol` のうち、対象行を span に含む関数がちょうど 1 件のときだけ成功する
- `--infer-from-line` は対象行を含む最も深い一意な branch path を推論し、その route を使って抽出する
- 対象行が branch 外にある場合、または最深 path が一意に決まらない場合は失敗する
- route DSL の正本は [route-dsl.md](route-dsl.md)
- 指定 route に沿う枝だけを返す

## JSON

- トップレベルは `tool_version`、`command`、`inputs`、`results`、`diagnostics` を持つ
- `results[*]` は `file`、`symbol`、`kind`、`span`、`language`、`rendered_lines`、`rendered_text`、`diagnostics` を持つ
- `route` は追加で `routes` を持つ

## Text

- 単一結果では従来どおり行番号付き text を返す
- 複数結果では item ごとに `command`、`symbol`、`route`、行範囲を含む file 見出しを挿入する
- `flow` / `route` の省略区間は `...` を使う
