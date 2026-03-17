# パイプライン

`cifter` の処理は `preprocessor` → `parser` → `extract_*` → `render` の順に進みます。

## 1. preprocessor

- `pcpp` を条件式評価器として使います
- `#if` / `#ifdef` / `#ifndef` / `#elif` / `#else` / `#endif` を評価します
- 非選択枝と条件ディレクティブ行は空行化して行番号を維持します
- 有効な `#define` / `#undef` は後続評価へ反映します

## 2. parser

- 前処理後ソースを `tree-sitter` で構文解析します
- 拡張子により C / C++ の parser を切り替えます
- `ParsedSource` は `SourceFile` と parse tree を束ねます
- 関数探索は `function_definition` を走査し、宣言子から関数名を特定します

## 3. extract_function

- 対象関数の開始行から終了行までをそのまま返します

## 4. extract_flow

- 制御構造と `--track` 一致文だけを残します
- `if` / `switch` / loop / jump / label 系を保持対象とします
- `case` / `default` 直下が `{ ... }` ブロックでも、その内側を中間コンテナとして走査します
- `--track` は構文上の完全一致だけを扱います

## 5. extract_path

- route DSL を `RouteSegment` 列へ変換します
- 現在コンテナ内で各 segment に一致する枝を一意に探します
- 選択枝のみを残し、親構造と route 終端以降の直列文脈を保ちます
- `case` / `default` 直下が `{ ... }` ブロックでも、その内側を探索対象に含めて元の開閉を残します
- `else if` は `else_clause` 直下の `if_statement` を 1 要素として扱います

## 6. render

- `ExtractionResult` を行番号付き text へ変換します
- 色なし経路では最終行番号の桁幅で右寄せし、利用者へ文字列として返します
- 色付き経路では同じ可視文字列に対して `rich` のシンタックスハイライトを重ねます
- 色有無は `--color` / `--no-color` と標準出力の TTY 判定で決まります
