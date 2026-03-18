# データモデル

この文書は主要な内部モデルを開発者向けに整理したものです。

## SourceSpan

`SourceSpan(file, start_line, end_line)` は抽出結果の共通トレーサビリティ単位です。

- `file`: 元ファイル path
- `start_line`: 抽出範囲の開始行
- `end_line`: 抽出範囲の終了行

## ParseDiagnostic

`ParseDiagnostic(category, code, message, details)` は parse quality の元診断です。

- `category`: `language` / `parse` / `preprocess` / `input`
- `code`: 集約用の識別子
- `message`: 利用者向け要約
- `details`: 補助情報

## ParseQualityReport

`ParseQualityReport(level, diagnostics)` は解析品質の集約結果です。

- `level`: `clean` または `degraded`
- `diagnostics`: 集約前の診断列

## ExtractedLine

`ExtractedLine(line_no, text, highlights, omitted_after_indent)` は 1 行分の表示単位です。

- `line_no`: 1-based 行番号
- `text`: その行の表示内容
- `highlights`: 色付き出力時にだけ使う行内強調範囲
- `omitted_after_indent`: 直後に `...` を差し込むときのコード側インデント

## InlineHighlightSpan

`InlineHighlightSpan(start_column, end_column, kind)` は 1 行内の追加強調範囲です。

- `start_column` / `end_column`: source line 基準の 0-based 半開区間
- `kind`: 現時点では `track_match` のみ

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

- kind は `case` / `default` / `if` / `else` / `else_if` / `for` / `while` / `do_while`
- `raw` は利用者入力の 1 segment です
- `payload` は `[]` 内の生文字列です。payload なしなら `None` です
- `normalized_payload` は kind ごとの比較用正規化結果です
- 外部 DSL の canonical form は [docs/specs/path-route-dsl.md](/home/tkenji/Repos/cifter/docs/specs/path-route-dsl.md) を参照します

## SourceFile

`SourceFile` は前処理後ソースの参照情報を保持します。

- `text`: 前処理後の全文
- `lines`: 行配列
- `trailing_newline`: 末尾改行の有無
- `line_start_bytes`: 各行の開始 byte offset

byte offset を保持することで、複合行の一部だけを残す `path` のレンダリングを支えます。

## ParsedSource

`ParsedSource(source, tree, language_name, resolved_language, language_resolution, quality)` は前処理後ソースと parse tree を束ねる最上位入力です。

- `language_name`: renderer 用のシンタックス名
- `resolved_language`: 実際に採用した解析言語
- `language_resolution`: `explicit` / `extension` / `quality`
- `quality`: parse quality 集約結果
