# CLI 仕様

## 共通

- `--source PATH` は必須
- `-D NAME[=VALUE]` は複数回指定可能
- 出力は行番号付き text
- Typer の引数エラーは終了コード 2
- 抽出失敗、曖昧一致、未一致、DSL 不正は終了コード 1

## `function`

- 必須引数は `--name`
- 指定関数の実装全体をそのまま抽出する
- 行番号は関数定義の開始行から終了行まで連続で出力する

## `flow`

- 必須引数は `--function`
- 制御構造の骨格だけを残す
- 保持対象は `if` / `else if` / `else` / `switch` / `case` / `default` / `for` / `while` / `do ... while` / `goto` / `break` / `continue` / `return` / ラベル定義
- `--track` は複数回指定可能
- `--track` 一致文は骨格に追加して残す

## `path`

- 必須引数は `--function`
- 必須引数は `--route`
- route は `>` でネストを下る最小 DSL
- 対応要素は `case LABEL` / `default` / `if CONDITION` / `else` / `else if CONDITION`
- `else if CONDITION` は複合 1 要素として扱う
- `else > if CONDITION` は DSL 不正として扱う
- 選択した枝の内部にある通常文は残す
- route が終端に達したコンテナでは、その後に直列で続く通常文を残す
- `else` / `else if CONDITION` を選んだ場合も、対応する親 `if` ヘッダを残す

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
4:     } else {
5:         WorkB();
6:     }
8:     After();
9:     return 3;
10: }
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
