# データモデル

## `SourceSpan`

`SourceSpan(file, start_line, end_line)` を抽出結果の共通トレーサビリティ単位とする。

## `ParseDiagnostic`

- `category` は `language` / `parse` / `preprocess` / `input`
- `code` は同一カテゴリ内の機械可読な識別子
- `message` は利用者向け要約
- `details` は件数や補足値を保持する

## `ParseQualityReport`

- `level` は `clean` または `degraded`
- `diagnostics` は集約前の診断列
- `degraded` は `ParseDiagnostic` を 1 件以上含む

## `InlineHighlightSpan`

- 抽出結果の 1 行内に対する追加強調範囲を表す
- `start_column` / `end_column` は source line 基準の 0-based 半開区間
- タブ展開後の表示列と行番号プレフィクス offset は保持しない
- `kind` は現時点では `track_match` のみ

## `ExtractedLine`

- `line_no` は 1-based 行番号
- `text` はその行の表示内容
- `highlights` は行内の追加強調範囲列
- `omitted_after_indent` は直後に `...` を差し込む場合のコード側インデント
- 色なし出力では `highlights` を可視文字列へ反映しない
- 表示時の列補正は renderer が担う

## `TrackPath`

- 文法は `segment (("." | "->") segment)*`
- `segment` は識別子
- 完全一致のみ
- `state` は `ctx->state` に一致しない
- `ctx->state` は `a->ctx->state` に一致しない

## `RouteSegment`

- `kind` は `case` / `default` / `if` / `else` / `else_if` / `for` / `while` / `do_while`
- `raw` は利用者入力の 1 segment
- `payload` は `[]` 内の生文字列で、payload なしなら `None`
- `normalized_payload` は比較用正規化結果で、不要なら `None`
- 外部 DSL の canonical form は [path-route-dsl.md](/home/tkenji/Repos/cifter/docs/specs/path-route-dsl.md) を参照する

### 条件比較

- `if[...]` / `else-if[...]` / `while[...]` / `do-while[...]` の payload は外側丸括弧と空白だけ正規化する
- `for[...]` は空白だけ正規化する
- それ以外の意味同値性は扱わない

### 一致方針

- 各 route の各段で一致候補が複数ある場合はソース順最初の一致を採用する
- 0 個だけが失敗条件である
- 探索対象は常に現在コンテナの直下文だけで、子孫ノードは暗黙探索しない

## `SourceFile`

- 前処理後ソースの `text` と `lines` を保持する
- 行番号と byte offset の対応を保持する
- 入力正規化後の改行表現を使う

## `ParsedSource`

- `source` は前処理後 `SourceFile`
- `tree` は採用した tree-sitter parse tree
- `language_name` は renderer 用のシンタックス名
- `resolved_language` は実際に採用した解析言語
- `language_resolution` は `explicit` / `extension` / `quality` のいずれか
- `quality` は parse quality 集約結果
