# パイプライン

`cifter` の処理は `input normalize` → `preprocessor` → `parser` → `extract_*` → `render` の順に進みます。

## 0. input normalize

- 入力は UTF-8 と UTF-8 with BOM を受理します
- BOM は除去して後段へ渡します
- 改行は LF へ正規化します
- CRLF や混在改行、BOM 除去は parse quality の `input` 診断対象です

## 1. preprocessor

- `pcpp` を条件式評価器として使います
- 物理行ではなく logical line 単位で `#if` / `#ifdef` / `#ifndef` / `#elif` / `#else` / `#endif` を評価します
- 行末 `\` 継続を畳んで複数行ディレクティブを扱います
- 非選択枝と条件ディレクティブ行は空行化して行番号を維持します
- 有効な `#define` / `#undef` は後続評価へ反映します
- active 領域の未対応ディレクティブは保持しつつ `preprocess` 診断へ記録します

## 2. parser

- 前処理後ソースを `tree-sitter` で構文解析します
- `--language c` / `--language cpp` では指定言語へ固定します
- `--language auto` では拡張子または parse quality で C / C++ を決めます
- `ParsedSource` は `SourceFile`、parse tree、解決言語、quality を束ねます
- 関数探索は `function_definition` と `template_declaration` を走査し、宣言子から関数名を特定します
- `ERROR` / `MISSING` ノードは失敗ではなく `parse` 診断として扱います

## 3. extract_function

- 対象関数の開始行から終了行までをそのまま返します

## 4. extract_flow

- 制御構造と `--track` 一致文だけを残します
- `if` / `switch` / loop / jump / label 系を保持対象とします
- `case` / `default` 直下が `{ ... }` ブロックでも、その内側を中間コンテナとして走査します
- `--track` は構文上の完全一致だけを扱います
- `--highlight` かつ色付き出力のときだけ、`--track` 一致箇所の元ソース範囲を行内強調 span として保持します

## 5. extract_path

- route DSL を `RouteSegment` 列へ変換します
- 現在コンテナ内で各 segment に一致する枝を一意に探します
- 選択枝のみを残し、親構造と route 終端以降の直列文脈を保ちます
- `case` / `default` 直下が `{ ... }` ブロックでも、その内側を探索対象に含めて元の開閉を残します
- `else if` は `else_clause` 直下の `if_statement` を 1 要素として扱います
- `for` / `while CONDITION` / `do while CONDITION` も中間コンテナとして探索と描画を行います
- route の各段では現在コンテナ直下の文だけを照合し、loop や branch を暗黙にはまたぎません

## 6. render

- `ExtractionResult` を行番号付き text へ変換します
- 色なし経路では最終行番号の桁幅で右寄せし、利用者へ文字列として返します
- `flow` / `path` では、保持行の元行番号にギャップがあれば省略区間ごとに 1 行の `...` を合成して差し込みます
- `...` のインデントは、その区間で最初に現れる非空の省略対象行から引き継ぎます
- 色付き経路では同じ可視文字列に対して `rich` のシンタックスハイライトを重ねます
- `flow --highlight` 指定時だけ `--track` の一致箇所を追加強調します
- タブ展開後の表示列と行番号プレフィクス offset は render で吸収します
- 色有無は `--color` / `--no-color` と標準出力の TTY 判定で決まります
- parse quality が `degraded` のときだけ標準エラーへ診断と再現情報を出します
