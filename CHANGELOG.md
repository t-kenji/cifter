# CHANGELOG

利用者から見える変更だけを記録する。

## [Unreleased]

- `cift route --infer-from-line <line>` を追加し、単一 file 内の行番号から full route を推論して抽出できるようにした

## [1.0.0] - 2026-03-20

- 公開 CLI を `cift function|flow|route <symbol> [inputs...]` に再設計
- `path` を `route` へ改名し、`--source` / `--name` / `--function` を廃止
- file / dir / `--files-from` / stdin による複数入力へ対応
- 出力に `--format auto|text|json` を追加し、JSON を正本化
- package import から CLI import を切り離し、配布 entry point を `cifter.cli:main` へ変更
- `flow` / `route` / `function` を共通 run 基盤へ載せ替え、同一 run 内 parse 再利用を追加

## [0.3.0] - 2026-03-18

- `path --route` で複数 route を指定できるようにし、route DSL を `/` 記法へ更新
- 前処理と `path` 抽出を安定化し、複雑な分岐経路でも route 解決と行番号追跡の回帰を減らした
- `.h` と未知拡張子の自動言語判定、および `degraded` 時の parse quality 診断を追加
- タブ区切り前処理ディレクティブ、複数行ディレクティブ、`case` / `default` をブロックで包んだ `switch` などの解析回帰を改善
- `flow` で `--track` 一致箇所の追加強調を可能にし、`flow` / `path` では省略区間を `...` で表示するようにした
- `path` の route で `for` / `while` / `do while` を中間段としてたどれるようにした
