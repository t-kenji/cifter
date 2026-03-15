# データモデル

## `SourceSpan`

`SourceSpan(file, start_line, end_line)` を抽出結果の共通トレーサビリティ単位とする。

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

### 条件比較

- `if CONDITION` と `else if CONDITION` の `CONDITION` は外側丸括弧と空白だけ正規化する
- それ以外の意味同値性は扱わない

### 一致方針

- route 各段で一致候補はちょうど 1 個でなければならない
- 0 個または複数候補なら失敗する
