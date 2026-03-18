# 性能計測

フェーズ3では、性能回帰を CI gate にはせず、再実行可能な計測手順と現状記録を残します。

## 計測コマンド

```sh
uv run python tools/benchmark_phase3.py
```

必要なら関数数や反復回数を上書きできます。

```sh
uv run python tools/benchmark_phase3.py --functions 600 --iterations 5
```

## 計測内容

- `parse_source(c)`
- `parse_source(cpp)`
- `function(c)` / `flow(c)` / `path(c)`
- `function(cpp)` / `flow(cpp)` / `path(cpp)`

入力はスクリプトが一時ディレクトリへ生成します。大きめの C / C++ ソースを毎回同じ条件で作り、中央値を出します。

## 現状記録

`2026-03-18`、`uv run python tools/benchmark_phase3.py`、`functions=400`、`iterations=3` の結果:

| case | median ms | runs ms |
| --- | ---: | --- |
| `parse_source(c)` | 42.20 | `42.20, 34.47, 43.53` |
| `parse_source(cpp)` | 34.89 | `37.32, 34.89, 33.07` |
| `function(c)` | 336.67 | `413.21, 336.67, 320.93` |
| `flow(c)` | 320.80 | `331.94, 311.63, 320.80` |
| `path(c)` | 359.48 | `359.48, 391.83, 312.69` |
| `function(cpp)` | 331.48 | `585.08, 323.05, 331.48` |
| `flow(cpp)` | 327.49 | `326.47, 327.49, 360.31` |
| `path(cpp)` | 373.08 | `349.63, 415.10, 373.08` |

観察:

- parse 単体は 35-45ms 前後で、CLI end-to-end より十分小さい
- 現時点の支配コストは Python 起動を含む end-to-end 実行
- `path` は C / C++ ともに他サブコマンドよりやや重い
