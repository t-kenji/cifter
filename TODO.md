# TODO

## uv build warning の解消

- 現状、`uv build` 実行時に `build-system.requires` の `uv_build>=0.10.10,<0.11.0` が現在の `uv 0.11.x` を含まないという warning が出る。
- 対応方針は、`uv_build` の要求範囲と現行 `uv` 系列の整合を見直し、warning なしで build できる状態にすること。
- 完了条件は、`uv build` 実行時に当該 warning が出ないこと。
