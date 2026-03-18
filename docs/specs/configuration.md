# CLI 仕様

## 共通

- `--version` は `cift {version}` を標準出力へ 1 行出力し、終了コード 0 で終了する
- `--version` 実行時は `--source` やサブコマンドを要求しない
- `--source PATH` は必須
- `--language auto|c|cpp` を指定可能
- `--language` の既定値は `auto`
- `auto` では `.c` を C、`.cc` / `.cpp` / `.cxx` / `.c++` / `.hpp` / `.hh` / `.hxx` / `.h++` を C++ として扱う
- `.h` と未知拡張子では、C / C++ の両方で parse quality を比較して採用言語を決める
- `.h` で parse quality が同点なら C を優先する
- `-D NAME[=VALUE]` は複数回指定可能
- 出力は行番号付き text
- ただし `flow` / `path` は、保持した元ソース行どうしが連続しない区間ごとに 1 行の省略表示を挿入できる
- 省略表示は合成行であり元ソース行番号を持たない
- 省略表示の可視文字列は `...` とし、インデントはその区間で最初に現れる非空の省略対象行の先頭空白を引き継ぐ
- 省略対象が空行だけの区間では、省略表示のインデントは直後の保持行に合わせる
- 抽出結果出力だけは `--color` / `--no-color` でシンタックスハイライト有無を制御できる
- `--color` / `--no-color` を省略した場合、標準出力が TTY のときだけ色付きで出力する
- 色付き出力は ANSI エスケープを含むが、可視文字列の内容と行番号契約は変えない
- parse quality は成功時でも標準エラーへ診断を出せる
- parse quality 診断は `degraded` のときだけ出す
- parse quality 診断はカテゴリごとに 1 行へ集約し、続けて再現情報 1 行を出す
- parse quality 診断は終了コードを変えない
- 診断カテゴリは `language` / `parse` / `preprocess` / `input` の 4 種である
- 再現情報は `source path`、解決後言語、`--language` の実効値、`-D` 一覧を含む
- 入力文字コードは UTF-8 と UTF-8 with BOM を受理する
- 非 UTF-8 入力は抽出失敗として扱う
- 改行コードは LF と CRLF を受理し、内部では LF に正規化する
- BOM 付き UTF-8、CRLF、混在改行は成功を許可するが `input` 診断対象である
- Typer の引数エラーは終了コード 2
- 抽出失敗、曖昧一致、未一致、DSL 不正は終了コード 1

## `function`

- 必須引数は `--name`
- `--language` を指定可能
- `--color` / `--no-color` を指定可能
- 指定関数の実装全体をそのまま抽出する
- 行番号は関数定義の開始行から終了行まで連続で出力する

## `flow`

- 必須引数は `--function`
- `--language` を指定可能
- `--color` / `--no-color` を指定可能
- `--highlight` を指定したときだけ `--track` 一致箇所へ追加強調を適用する
- 制御構造の骨格だけを残す
- 保持対象は `if` / `else if` / `else` / `switch` / `case` / `default` / `for` / `while` / `do ... while` / `goto` / `break` / `continue` / `return` / ラベル定義
- `case` / `default` 本体は直下に文が並ぶ形でも `{ ... }` ブロック 1 個で包まれる形でも同等に走査する
- `--track` は複数回指定可能
- `--track` 一致文は骨格に追加して残す
- 省略された通常文や空行は、連続する区間ごとに 1 行の `...` で表示する
- `--highlight` は `--track` がない場合は無効果
- `--highlight` を指定しても `--no-color` または非 TTY では追加強調を行わない

例:

```c
int DecideState(int x)
{
    int state = 0;
    LogStart();

    if (x > 0) {
        Prepare();
        state = 1;
    } else {
        PrepareFallback();
        state = 2;
    }

    Finalize();
    return state;
}
```

```sh
cift flow --function DecideState --source decide_state.c --track state
```

```text
1: int DecideState(int x)
2: {
3:     int state = 0;
        ...
6:     if (x > 0) {
            ...
8:         state = 1;
9:     } else {
            ...
11:         state = 2;
12:     }
        ...
15:     return state;
16: }
```

## `path`

- 必須引数は `--function`
- `--route` は 1 個以上必須で、複数回指定できる
- `--language` を指定可能
- `--color` / `--no-color` を指定可能
- route は `>` でネストを下る最小 DSL
- 対応要素は `case LABEL` / `default` / `if CONDITION` / `else` / `else if CONDITION` / `for` / `while CONDITION` / `do while CONDITION`
- `else if CONDITION` は複合 1 要素として扱う
- `else > if CONDITION` は DSL 不正として扱う
- 複数 route を指定した場合、各 route を独立に解決して OR で union する
- 表示順は元ソース行順で、`--route` の指定順には依存しない
- 共通祖先、重複ノード、同一行は 1 回だけ表示する
- 選択した枝の内部にある通常文は残す
- route 終端の文を含むコンテナでは、その直後に続く通常文を残す
- 同じ階層で次の分岐文またはループ文に達した時点で、route 終端後の通常文保持は打ち切る
- `else` / `else if CONDITION` を選んだ場合も、対応する親 `if` ヘッダを残す
- `case` / `default` 本体は直下に文が並ぶ形でも `{ ... }` ブロック 1 個で包まれる形でも同等に探索する
- `for` / `while CONDITION` / `do while CONDITION` も中間コンテナとして探索できる
- route の探索対象は常に現在コンテナの直下文だけで、loop や branch を暗黙にはまたがない
- 各 route の各段で一致候補はちょうど 1 個でなければならない
- 1 本でも DSL 不正、未一致、曖昧一致があれば全体を失敗とする
- 省略された通常文や空行は、連続する区間ごとに 1 行の `...` で表示する

例:

```c
int RouteTail(int x)
{
    switch (x) {
    case 1:
        Prep();
        if (x > 0) {
            Work();
        }
        After();
        break;
    default:
        break;
    }
}
```

```sh
cift path --function RouteTail --source route_tail.c --route 'case 1 > if x > 0'
```

```text
1: int RouteTail(int x)
2: {
3:     switch (x) {
4:     case 1:
5:         Prep();
6:         if (x > 0) {
7:             Work();
8:         }
9:         After();
10:         break;
        ...
13:     }
14: }
```

```c
int ElseRoute(int x)
{
    if (x > 0) {
        WorkA();
    } else {
        WorkB();
    }

    After();
    return 3;
}
```

```sh
cift path --function ElseRoute --source else_route.c --route 'else'
```

```text
1: int ElseRoute(int x)
2: {
3:     if (x > 0) {
            ...
5:     } else {
6:         WorkB();
7:     }
        ...
9:     After();
10:     return 3;
11: }
```

```sh
cift path --function FooFunction --source foo.c --route 'case CMD_HOGE > else if errno == EINT'
```

```text
10:     case CMD_HOGE:
13:         if (ret == OK) {
15:         } else if (errno == EINT) {
17:             state = RETRY;
18:             return -2;
19:         }
```

```c
int LoopRoute(int sts)
{
    if (status == BAR) {
    } else {
        for (;;) {
            switch (sts) {
            case STS_IDLE:
                Work();
                break;
            }
        }
    }
}
```

```sh
cift path --function LoopRoute --source loop_route.c --route 'else > for > case STS_IDLE'
```

```text
1: int LoopRoute(int sts)
2: {
3:     if (status == BAR) {
4:     } else {
5:         for (;;) {
6:             switch (sts) {
7:             case STS_IDLE:
8:                 Work();
9:                 break;
10:             }
11:         }
12:     }
13: }
```

```sh
cift path --function FooFunction --source examples/demo.c \
  --route 'case CMD_LOOP > while (ctx->retry_count < 2) > if (ctx->retry_count == 1)' \
  --route 'case CMD_LOOP > for'
```

```text
47: int FooFunction(AppContext *ctx, int command)
48: {
        ...
67:     switch (command) {
        ...
90:     case CMD_LOOP:
91:         for (i = 0; i < 4; i++) {
92:             if (i == 1) {
93:                 continue;
94:             }
95:             ret = PollWork(ctx, i);
96:             if (ret == OK) {
97:                 break;
98:             }
99:         }
        ...
101:        while (ctx->retry_count < 2) {
102:            ctx->retry_count = ctx->retry_count + 1;
103:            if (ctx->retry_count == 1) {
104:                continue;
105:            }
106:            break;
107:        }
        ...
119:    }
        ...
128: }
```
