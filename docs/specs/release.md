# 配布とリリース仕様

この文書は `cifter` の配布物、CI 対象、バージョン運用、PyPI と GitHub Release の公開運用の正本を定義する。

## 配布物

- すべてのリリースで `wheel` と `sdist` を生成する
- 配布名は `cifter-cli` とする
- 正規配布先は PyPI と GitHub Release の両方とする
- 正規ライセンスは MIT とする
- ルートの `LICENSE` を配布物へ同梱する
- 配布メタデータに MIT を明示する
- 配布メタデータに project URL、keywords、classifiers を含める
- 配布物から利用者が `cift` を起動できることを保証対象に含める
- 配布物から利用者が `python -m cifter` を起動できることを保証対象に含める
- 配布物から利用者が `cift --version` を実行できることを保証対象に含める
- 配布物から利用者が `python -m cifter --version` を実行できることを保証対象に含める

## CI 対象

- 必須対象は Linux + Python 3.12 とする
- Linux の必須 CI は `uv sync --frozen`、`uv run pytest`、`uv run ruff check .`、`uv run ty check .`、`uv build` を順に実行する
- Linux の必須 CI は build 後に生成 `wheel` / `sdist` について配布名、`LICENSE` 同梱、MIT メタデータ、project URL、keywords、classifiers を検証する
- Linux の必須 CI は build 後に生成 wheel をクリーンな仮想環境へ install し、`cift --help`、`python -m cifter --help`、`cift --version`、`python -m cifter --version`、実コマンド 1 本の smoke を行う
- Windows は追加対象とし、同じ wheel に対する install smoke で `cift --help`、`python -m cifter --help`、`cift --version`、`python -m cifter --version`、実コマンド 1 本を観測する
- Windows の結果は互換性観測用であり、release の必須ゲートには含めない

## バージョンとタグ

- version は `0.minor.patch` とする
- `minor` は CLI、出力、対応範囲など利用者影響のある変更で更新する
- `patch` は不具合修正、文書、CI、内部整理など利用者影響のない変更で更新する
- release tag は `vX.Y.Z` とし、`pyproject.toml` の version と一致しなければならない

## changelog

- `CHANGELOG.md` を changelog の正本とする
- changelog は人手で更新する
- 先頭に `## [Unreleased]` 節を置く
- リリース済み version は `## [X.Y.Z] - YYYY-MM-DD` 形式の見出しで記録する
- changelog には利用者から見える変更だけを書く

## 公開フロー

- release は `v*` tag push を起点に実行する
- release 前に Linux の必須 CI ゲートを再実行する
- release 作成時は対象 version の changelog 節が存在することを確認する
- release workflow は Trusted Publishing により PyPI publish を行う
- PyPI publish は build、配布物検証、install smoke 成功後に行う
- GitHub Release には対象 version の `wheel` と `sdist` を添付する
- GitHub Release 添付は PyPI publish 成功後に行う
- release 成功条件には PyPI 上で対象 version の `wheel` / `sdist` が公開されていることを含める
