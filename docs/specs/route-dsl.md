# `route --route` DSL 仕様

この文書は `cift route --route` と `cift route --infer-from-line` が使う route DSL の正本である。

## 概要

- DSL は `/` 区切り segment 列
- 対象は `route --route` と `route --infer-from-line`
- canonical form は `/` 区切り

## segment

- `case[...]`
- `default`
- `if[...]`
- `else-if[...]`
- `else`
- `for`
- `for[...]`
- `while`
- `while[...]`
- `do-while`
- `do-while[...]`

## 正規化

- `if[...]` / `else-if[...]` / `while[...]` / `do-while[...]` は外側括弧と空白だけ正規化する
- `for[...]` は空白だけ正規化する

## 一致方針

- 各段で一致候補が複数ある場合はソース順最初を採用する
- 1 本でも DSL 不正または未一致があれば run 全体を失敗させる

## `--infer-from-line`

- `--infer-from-line` は元ソースの 1-based 行番号から route を推論する
- 推論結果は full path で返す
- 推論に使う segment 文字列は canonical form を使う
- `if[...]` / `else-if[...]` / `while[...]` / `do-while[...]` は条件正規化後の payload を使う
- `for[...]` は loop header 正規化後の payload を使う
- `case[...]` は case label text、`default` と `else` は payload なしを使う
