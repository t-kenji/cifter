# データモデル

## `SourceSpan`

`SourceSpan(file, start_line, end_line)` を抽出結果の共通トレーサビリティ単位とする。

## `InlineHighlightSpan`

- 抽出結果の 1 行内に対する追加強調範囲を表す
- `start_column` / `end_column` は source line 基準の 0-based 半開区間
- タブ展開後の表示列と行番号プレフィクス offset は保持しない
- `kind` は現時点では `track_match` のみ

## `ExtractedLine`

- `line_no` は 1-based 行番号
- `text` はその行の表示内容
- `highlights` は行内の追加強調範囲列
- 色なし出力では `highlights` を可視文字列へ反映しない
- 表示時の列補正は renderer が担う

## `TrackPath`

- 文法は `segment (("." | "->") segment)*`
- `segment` は識別子
- 完全一致のみ
- `state` は `ctx->state` に一致しない
- `ctx->state` は `a->ctx->state` に一致しない

## `RouteSegment`

- `case LABEL`
- `default`
- `if CONDITION`
- `else`
- `else if CONDITION`
- `for`
- `while CONDITION`
- `do while CONDITION`

### 条件比較

- `if CONDITION` / `else if CONDITION` / `while CONDITION` / `do while CONDITION` の `CONDITION` は外側丸括弧と空白だけ正規化する
- それ以外の意味同値性は扱わない

### 一致方針

- route 各段で一致候補はちょうど 1 個でなければならない
- 0 個または複数候補なら失敗する
- 探索対象は常に現在コンテナの直下文だけで、子孫ノードは暗黙探索しない
