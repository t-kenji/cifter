# `route --route` DSL 仕様

この文書は `cift route --route` の外部 DSL 仕様の正本である。

## 概要

- DSL は `/` 区切り segment 列
- 対象は `route --route` のみ
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
