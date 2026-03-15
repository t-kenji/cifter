# データモデル

この文書は主要な内部モデルを開発者向けに整理したものです。

## SourceSpan

`SourceSpan(file, start_line, end_line)` は抽出結果の共通トレーサビリティ単位です。

- `file`: 元ファイル path
- `start_line`: 抽出範囲の開始行
- `end_line`: 抽出範囲の終了行

## ExtractedLine

`ExtractedLine(line_no, text)` は 1 行分の表示単位です。

- `line_no`: 1-based 行番号
- `text`: その行の表示内容

## ExtractionResult

`ExtractionResult(span, lines)` は公開コマンドが返す共通結果です。

- `span`: 結果全体の最小範囲
- `lines`: 表示対象の行集合

## TrackPath

`TrackPath` は `flow --track` 用の完全一致パターンです。

- 文法は `segment (("." | "->") segment)*`
- `segment` は識別子です
- `raw` は利用者入力、`normalized` は空白除去済み表現です

## RouteSegment

`RouteSegment` は `path --route` を 1 要素ずつ分解した内部表現です。

- kind は `case` / `default` / `if` / `else` / `else_if`
- `case LABEL` は `label` を持ちます
- `if CONDITION` と `else if CONDITION` は正規化済み `condition` を持ちます

## SourceFile

`SourceFile` は前処理後ソースの参照情報を保持します。

- `text`: 前処理後の全文
- `lines`: 行配列
- `trailing_newline`: 末尾改行の有無
- `line_start_bytes`: 各行の開始 byte offset

byte offset を保持することで、複合行の一部だけを残す `path` のレンダリングを支えます。

## ParsedSource

`ParsedSource(source, tree, language_name)` は前処理後ソースと parse tree を束ねる最上位入力です。
