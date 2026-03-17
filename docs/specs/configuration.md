# CLI 仕様

## 共通

- `--version` は `cift {version}` を標準出力へ 1 行出力し、終了コード 0 で終了する
- `--version` 実行時は `--source` やサブコマンドを要求しない
- `--source PATH` は必須
- `-D NAME[=VALUE]` は複数回指定可能
- 出力は行番号付き text
- ただし `flow` / `path` は、保持した元ソース行どうしが連続しない区間ごとに 1 行の省略表示を挿入できる
- 省略表示は合成行であり元ソース行番号を持たない
- 省略表示の可視文字列は `...` とし、インデントはその区間で最初に現れる非空の省略対象行の先頭空白を引き継ぐ
- 省略対象が空行だけの区間では、省略表示のインデントは直後の保持行に合わせる
- 抽出結果出力だけは `--color` / `--no-color` でシンタックスハイライト有無を制御できる
- `--color` / `--no-color` を省略した場合、標準出力が TTY のときだけ色付きで出力する
- 色付き出力は ANSI エスケープを含むが、可視文字列の内容と行番号契約は変えない
- Typer の引数エラーは終了コード 2
- 抽出失敗、曖昧一致、未一致、DSL 不正は終了コード 1

## `function`

- 必須引数は `--name`
- `--color` / `--no-color` を指定可能
- 指定関数の実装全体をそのまま抽出する
- 行番号は関数定義の開始行から終了行まで連続で出力する

## `flow`

- 必須引数は `--function`
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
- 必須引数は `--route`
- `--color` / `--no-color` を指定可能
- route は `>` でネストを下る最小 DSL
- 対応要素は `case LABEL` / `default` / `if CONDITION` / `else` / `else if CONDITION` / `for` / `while CONDITION` / `do while CONDITION`
- `else if CONDITION` は複合 1 要素として扱う
- `else > if CONDITION` は DSL 不正として扱う
- 選択した枝の内部にある通常文は残す
- route が終端に達したコンテナでは、その後に直列で続く通常文を残す
- `else` / `else if CONDITION` を選んだ場合も、対応する親 `if` ヘッダを残す
- `case` / `default` 本体は直下に文が並ぶ形でも `{ ... }` ブロック 1 個で包まれる形でも同等に探索する
- `for` / `while CONDITION` / `do while CONDITION` も中間コンテナとして探索できる
- route の探索対象は常に現在コンテナの直下文だけで、loop や branch を暗黙にはまたがない
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
