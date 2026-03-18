# パイプライン

処理順は次のとおり。

> 生ソースファイル -> 条件分岐前処理 -> tree-sitter 解析 -> 抽出 -> レンダー -> 出力

## 入力正規化

- UTF-8 と UTF-8 with BOM を受理する
- UTF-8 with BOM は BOM を除去して後段へ渡す
- 非 UTF-8 は失敗する
- LF と CRLF を受理し、内部では LF へ正規化する
- 混在改行は許容するが parse quality へ `input` 診断を追加する

## 条件分岐前処理

- `pcpp` を条件式評価器として使う
- 物理行ではなく logical line 単位で処理する
- logical line は行末 `\` 継続を畳んで構築する
- 評価対象は `#if` / `#ifdef` / `#ifndef` / `#elif` / `#else` / `#endif`
- active な `#define` / `#undef` は、複数行でも後続の条件式評価へ反映する
- `#include` / `#pragma` / `#error` などの非評価ディレクティブは active 領域では行を保持したまま後段へ渡す
- active 領域の未対応ディレクティブは失敗させず、parse quality へ `preprocess` 診断を追加する
- 無効化された枝と条件分岐ディレクティブ行は空行化する
- 空行化は physical line ごとに行い、元行番号を維持する

## tree-sitter 解析

- 前処理後ソースを tree-sitter で構文解析する
- `--language c` / `--language cpp` 指定時は、その言語で固定して parse する
- `--language auto` では、既知拡張子は拡張子で即決し、`.h` と未知拡張子は C / C++ の両方で parse して parse quality を比較する
- parse quality 比較は `has_error`、`ERROR` ノード数、`MISSING` ノード数で行う
- `.h` で parse quality が同点なら C を採用する
- `ERROR` ノードは許容する
- `ERROR` または `MISSING` を含む parse は parse quality へ `parse` 診断を追加する
- 対象関数や対象枝を一意に特定できない場合だけ失敗する

## 抽出

- `function` は対象関数の source slice を返す
- `flow` は制御構造骨格と `--track` 一致文を返す
- `flow` は `--highlight` かつ色付き経路のときだけ `--track` 一致箇所の元ソース範囲を抽出結果へ保持する
- `flow` の `case` / `default` は、必要なら直下の `{ ... }` を中間コンテナとして辿り、元行番号を保ったまま骨格を残す
- `path` は各 route に沿う枝だけを返し、どの route でも選ばれなかった sibling branch は削る
- 複数 route を指定した場合、各 route を独立に解決して保持行集合を union する
- `path` は選択した枝の内部にある通常文を残す
- `path` は route 終端の文を含むコンテナで、その直後に続く通常文を残す
- `path` は同じ階層で次の分岐文またはループ文に達した時点で、route 終端後の通常文保持を打ち切る
- `path` で `else` / `else-if[...]` を選んだ場合も、対応する親 `if` ヘッダを残す
- `path` は親構造の開閉と元行番号を維持したまま、非選択枝だけを落とす
- `path` は共通祖先、重複ノード、同一行を 1 回だけ描画する
- `path` の `case` / `default` も、必要なら直下の `{ ... }` を中間コンテナとして探索と描画を行う
- `else-if[...]` は AST 上の `else_clause` 直下 `if_statement` を 1 要素として照合する
- `path` の `for` / `for[...]` / `while` / `while[...]` / `do-while` / `do-while[...]` も中間コンテナとして探索と描画を行う
- `path` は各 route の各段で現在コンテナ直下の文だけを照合し、loop や branch を暗黙にはまたがない
- `path` は各段で一致候補が複数あっても失敗せず、ソース順最初の一致を採用する

## レンダーと出力

- 色なし経路の正本は行番号付き text 文字列である
- 抽出結果の標準出力契約は parse quality 診断の有無で変えない
- `flow` / `path` は、隣接する保持行の元行番号が連続しないたびに、省略区間ごと 1 行の合成 `...` を差し込む
- 合成 `...` 行は元ソース行番号を持たず、行番号プレフィクス相当幅の空白とコード側インデントだけを表示する
- `...` 行のコード側インデントは、省略区間で最初に現れる非空行の先頭空白を使い、非空行がなければ直後の保持行に合わせる
- 色付き経路は同じ可視文字列に ANSI エスケープを重ねる
- シンタックスハイライトは抽出コード本体だけへ適用し、行番号プレフィクスの書式は維持する
- `flow --track` 一致箇所は、`--highlight` を指定した色付き経路でのみ追加強調する
- `flow --track` の追加強調は一致したシンボル文字列だけへ適用し、statement 全体や行番号プレフィクスへは適用しない
- 追加強調の適用位置は `rich` の `tab_size=4` に従って決める
- `InlineHighlightSpan` の source 列座標から、タブ展開後の表示列と行番号プレフィクス offset への変換は renderer が行う
- 色有無は `--color` / `--no-color` と標準出力 TTY 判定で決める
- parse quality が `degraded` のときだけ、カテゴリ要約と再現情報を標準エラーへ出す
