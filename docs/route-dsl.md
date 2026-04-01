# route DSL

この文書は、`cift route --route` と `cift route --infer-from-line` で使う route DSL の人間向けリファレンスです。
開発者だけでなく、DSL を使いこなしたい利用者も読む前提で書いています。
厳密な正本は [specs/route-dsl.md](specs/route-dsl.md) です。

## route DSL とは何か

route DSL は、「関数の中でどの分岐を通る枝を見たいか」を文字列で指定するための書き方です。

たとえば次のように使います。

```sh
cift route DecideMode examples/quickstart/decide_mode.c --route 'else-if[value == 10]'
```

この例は「`else if (value == 10)` の枝だけを残したい」という意味です。

行番号から逆引きしたいときは、次のように `--infer-from-line` を使えます。

```sh
cift route DecideMode examples/quickstart/decide_mode.c --infer-from-line 8
```

この場合は、8 行目を含む最も深い branch path を内部で推論し、その route で抽出します。

## 基本形

route は segment を `/` でつないだ列です。

```text
case[CMD_OK]/else-if[value == 10]/for[i = 0; i < 4; i++]
```

これは「まず `case[CMD_OK]` を選び、その中の `else-if[value == 10]` を選び、その中の `for[...]` を選ぶ」という意味です。

`/` は path ではなく segment 区切りです。

## 最初に理解しておくこと

- route は一般的な CFG path ではありません
- route は「書かれている構造を順にたどるための指定」です
- 同じ段に候補が複数ある場合は、ソース順で最初に一致したものを採用します
- segment の途中で一致しなければ、その route 全体が失敗します

## 代表的な使い方

### `else` だけ見たい

```c
if (value > 10) {
    A();
} else {
    B();
}
```

```text
else
```

### `else if` の条件付き枝を見たい

```c
if (value > 10) {
    A();
} else if (value == 10) {
    B();
} else {
    C();
}
```

```text
else-if[value == 10]
```

### `switch` の特定 case だけ見たい

```c
switch (cmd) {
case CMD_OK:
    Work();
    break;
default:
    break;
}
```

```text
case[CMD_OK]
```

## segment 一覧

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

以下では各 segment を個別に説明します。

## segment リファレンス

### `case[...]`

形式:

```text
case[CASE_LABEL]
```

対応する構造:

- `switch` の `case`

例:

```text
case[CMD_OK]
```

補足:

- `case[...]` の中身は case label と比較されます
- 同じ label を持つ `case` が複数あれば、最初の一致を採用します

### `default`

形式:

```text
default
```

対応する構造:

- `switch` の `default`

例:

```text
default
```

補足:

- `default` に payload はありません
- `default[...]` のような書き方はできません

### `if[...]`

形式:

```text
if[condition]
```

対応する構造:

- `if (...) { ... }`

例:

```text
if[value > 10]
```

補足:

- `if` は最初の `if` 節を表します
- `else if` 節は `if[...]` ではなく `else-if[...]` を使います

### `else-if[...]`

形式:

```text
else-if[condition]
```

対応する構造:

- `else if (...) { ... }`

例:

```text
else-if[value == 10]
```

補足:

- `if[...]` と `else-if[...]` は別物です
- 迷ったら先に `flow` でコード形を確認すると分かりやすいです

### `else`

形式:

```text
else
```

対応する構造:

- `else { ... }`

例:

```text
else
```

補足:

- `else` に payload はありません

### `for`

形式:

```text
for
```

対応する構造:

- すべての `for (...)`

例:

```text
for
```

補足:

- header を指定せず、「最初に一致する `for`」を broad に選びたいときに使います

### `for[...]`

形式:

```text
for[init; condition; update]
```

対応する構造:

- 特定 header の `for (...)`

例:

```text
for[i = 0; i < 4; i++]
```

補足:

- `for[...]` は header 全体を見ます
- 空白の違いはある程度吸収されます

### `while`

形式:

```text
while
```

対応する構造:

- すべての `while (...)`

例:

```text
while
```

補足:

- 条件まで指定しなくてよい broad な指定です

### `while[...]`

形式:

```text
while[condition]
```

対応する構造:

- 特定条件の `while (...)`

例:

```text
while[count > 0]
```

補足:

- 条件式の外側括弧は一部吸収されます
- 空白の違いもある程度吸収されます

### `do-while`

形式:

```text
do-while
```

対応する構造:

- すべての `do { ... } while (...)`

例:

```text
do-while
```

補足:

- 条件まで指定しない broad な指定です

### `do-while[...]`

形式:

```text
do-while[condition]
```

対応する構造:

- 特定条件の `do { ... } while (...)`

例:

```text
do-while[state < 31]
```

補足:

- `while[...]` と同様に、外側括弧や空白は一部吸収されます

## payload の書き方

payload は `[...]` の中に書きます。

例:

- `if[value > 10]`
- `else-if[value == 10]`
- `case[CMD_OK]`
- `for[i = 0; i < 4; i++]`

ポイント:

- `default` と `else` には payload はありません
- `for[...]` は 3 つの節を含む header 全体を入れます
- `case[...]` は switch の label を入れます

## 正規化の考え方

route DSL では、人間が書いた条件式の差を一部吸収します。

### 空白

空白の量が多少違っても一致します。

たとえば次は同じ意味として扱われます。

```text
else-if[value == 10]
else-if[ value   ==   10 ]
```

```text
for[i = 0; i < 4; i++]
for[ i = 0 ; i < 4 ; i++ ]
```

### 条件式の外側括弧

`if[...]`、`else-if[...]`、`while[...]`、`do-while[...]` では、条件式の外側括弧を一部吸収します。

たとえば次は近い形として扱われます。

```text
while[count > 0]
while[((count > 0))]
```

## 一致方針

- route は左から順に segment を消費します
- 各段で一致候補が複数ある場合は、ソース順最初を採用します
- 途中で一致しなくなった時点で、その route は失敗します
- route 全体の 1 本でも不正または未一致なら command は失敗します

これは「すべての可能 path を探索する」のではなく、「書かれた route を 1 本ずつ順にたどる」方式です。

## 使い方ガイド

### まず broad に試す

最初から厳密に書くより、まず broad に試す方が分かりやすいです。

例:

- `else`
- `for`
- `while`
- `case[CMD_OK]`

### 必要なら payload を足す

対象が複数ありそうなら payload を足して絞ります。

例:

- `for` -> `for[i = 0; i < 4; i++]`
- `while` -> `while[count > 0]`
- `if[...]` -> `else-if[value == 10]`

### 迷ったら `function` や `flow` を先に使う

route 文字列を作る前に、対象関数の形を先に見た方が楽です。

おすすめ手順:

1. `function` で関数全体を見る
2. `flow` で骨格を見る
3. route を組む

## よくある失敗例

### `else-if` と `if` を混同する

`else if (...)` を選びたいときに `if[...]` と書くと一致しません。

```text
if[value == 10]        # これは先頭の if 用
else-if[value == 10]   # こちらが else if 用
```

### `default` に payload を付ける

```text
default[CMD_OK]
```

これは不正です。`default` は payload を持ちません。

### `/` を path 区切りと誤解する

```text
case[CMD_OK]/else
```

この `/` は file path ではなく、segment 区切りです。

### CFG 全探索だと思い込む

route は「到達可能な全 path を列挙する機能」ではありません。
あくまで、利用者が書いた route を順にたどって枝を選択する機能です。

## 正本仕様

この文書は人間向けのリファレンスです。
厳密な外部 DSL 仕様は [specs/route-dsl.md](specs/route-dsl.md) を参照してください。
