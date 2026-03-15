# パイプライン

処理順は次のとおり。

> 生ソースファイル -> 条件分岐前処理 -> tree-sitter 解析 -> 抽出 -> レンダー -> 出力

## 条件分岐前処理

- `pcpp` を条件式評価器として使う
- 評価対象は `#if` / `#ifdef` / `#ifndef` / `#elif` / `#else` / `#endif`
- `#include` / `#define` / `#undef` は行を保持したまま後段へ渡す
- ただし有効な `#define` / `#undef` は後続の条件式評価には反映する
- 無効化された枝と条件分岐ディレクティブ行は空行化する

## tree-sitter 解析

- 前処理後ソースを tree-sitter で構文解析する
- `ERROR` ノードは許容する
- 対象関数や対象枝を一意に特定できない場合だけ失敗する

## 抽出

- `function` は対象関数の source slice を返す
- `flow` は制御構造骨格と `--track` 一致文を返す
- `path` は route に沿う枝だけを返し、非選択 sibling branch は削る
- `path` は選択した枝の内部にある通常文を残す
- `path` は route が終端に達したコンテナでは、その後に直列で続く通常文を残す
- `path` で `else` / `else if CONDITION` を選んだ場合も、対応する親 `if` ヘッダを残す
- `path` は親構造の開閉と元行番号を維持したまま、非選択枝だけを落とす
- `else if CONDITION` は AST 上の `else_clause` 直下 `if_statement` を 1 要素として照合する

## レンダーと出力

- 色なし経路の正本は行番号付き text 文字列である
- 色付き経路は同じ可視文字列に ANSI エスケープを重ねる
- シンタックスハイライトは抽出コード本体だけへ適用し、行番号プレフィクスの書式は維持する
- 色有無は `--color` / `--no-color` と標準出力 TTY 判定で決める
