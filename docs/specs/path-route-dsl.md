# `path --route` DSL 仕様

この文書は `cift path --route` の外部 DSL 仕様の正本である。

## 目的と適用範囲

- `path` で関数内の特定の制御構造パスを指定する
- `flow` で把握した枝から必要な経路だけを機械的に切り出す
- 人間可読性を保ちつつ、実装が曖昧にならない canonical form を提供する
- 対象は `path --route` のみであり、`flow --track` や他オプションには適用しない

## 全体文法

```ebnf
route := segment ( "/" segment )*
```

- 区切りは `/` のみ
- route 全体の前後空白は無視する
- `/` 前後の空白は無視する
- 旧 `>` 区切りは非対応であり DSL 不正とする

例:

```text
case[CMD_LOOP]/while/if[(ctx->retry_count == 1)]
case[CMD_LOOP] / while / if[(ctx->retry_count == 1)]
```

## Segment

許可する segment は次の canonical form のみである。

- `case[TEXT]`
- `default`
- `if[TEXT]`
- `else`
- `else-if[TEXT]`
- `for`
- `for[TEXT]`
- `while`
- `while[TEXT]`
- `do-while`
- `do-while[TEXT]`

次は DSL 不正とする。

- `case CMD_LOOP`
- `else if[(ret == 11)]`
- `do while[(state < 31)]`
- `switch[...]`

## Payload

`case[...]`、`if[...]`、`else-if[...]`、`for[...]`、`while[...]`、`do-while[...]` の `[...]` 内側を payload と呼ぶ。

- `case[...]` / `if[...]` / `else-if[...]` / `for[...]` / `while[...]` / `do-while[...]` は payload 必須
- `default` / `else` / `for` / `while` / `do-while` は payload 禁止
- 空 payload は不正
- payload は最外 `[` `]` の内側全文字列であり、比較前に必要な正規化だけを行う
- payload 内では入れ子の `[` `]` を許可する
- payload 内の `/` は区切りとして扱わない
- payload の走査では文字列リテラルと文字リテラルを認識し、引用符内の `]` と `/` は区切りとして扱わない

例:

```text
if[arr[i] > limit]
if[s[i] == ']']
if[strcmp(path, "/") == 0]
```

## 比較規則

### `case[TEXT]`

- 対象は `switch` 配下の `case`
- `TEXT` は `case` ラベル文字列と比較する
- 比較前処理は前後空白の trim のみ

### `default`

- 対象は `switch` 配下の `default`

### `if[TEXT]` / `else-if[TEXT]` / `while[TEXT]` / `do-while[TEXT]`

- 対象はそれぞれ `if` / `else if` / `while` / `do { ... } while (...)`
- 比較前に次だけを適用する
  - 前後空白 trim
  - 連続空白の 1 個化
  - 冗長な外側丸括弧の除去
- 意味同値性は扱わない

同一視する例:

```text
ret == OK
(ret == OK)
((ret == OK))
```

同一視しない例:

```text
a == b
b == a
ret == 0
!ret
```

### `for[TEXT]`

- 対象は `for (...)`
- `TEXT` は `for (...)` 内の全文字列と比較する
- 比較前に次だけを適用する
  - 前後空白 trim
  - 連続空白の 1 個化
- 外側丸括弧の除去や意味同値性は扱わない

### `for` / `while` / `do-while`

- payload なしの loop segment は簡易指定である
- 現在階層にある同種 loop のうち、ソース順で最初の 1 個を選ぶ

## 探索規則

- route は上位から順に segment を辿る
- 各段の探索対象は、直前に一致したコンテナの直下文だけである
- loop や branch を暗黙に飛び越えない
- `case` / `default` は直下に文が並ぶ形でも `{ ... }` ブロック 1 個で包まれる形でも同等に探索する
- `else-if[TEXT]` は外部 DSL では独立 segment とし、内部実装では `else_clause` 直下の `if_statement` として扱ってよい

## 複数一致と未一致

- 一致候補が 0 個なら失敗する
- 一致候補が複数あっても失敗しない
- 複数一致時は、現在階層でソース順最初の一致を採用する

## 複数 `--route`

- `--route` は 1 個以上必須で、複数回指定できる
- 複数 route は OR として解決し、保持行集合を union する
- 共通祖先、重複ノード、同一行は 1 回だけ出力する
- route 終端の文を含むコンテナでは、その直後に続く通常文だけを残す
- 同じ階層で次の分岐文または loop 文に達した時点で、route 終端後の通常文保持は打ち切る
- 省略区間は `...` で表示する

## 正常例

```text
case[CMD_HOGE]
case[CMD_LOOP]/while
case[CMD_LOOP]/while[(ctx->retry_count < 2)]
case[CMD_LOOP]/while/if[(ctx->retry_count == 1)]
case[CMD_HOGE]/else-if[(ret == 11)]
case[CMD_LOOP]/do-while[(state < 31)]
if[arr[i] > limit]
case[CMD_LOOP]/for[i = 0; i < 4; i++]
```

## 不正例

```text
switch[command]
loop
case
if[]
default[x]
else[x]
else if[(ret == 11)]
do while[(state < 31)]
case CMD_LOOP > while > if (x)
```

## Non-Goals

- 自然文入力
- `switch[...]` segment
- `goto` ラベル指定
- CFG 探索
- データフロー解析
- 意味同値性判定
- 到達可能性解析
- マクロ展開後の比較
