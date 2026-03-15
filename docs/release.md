# リリース手順

この文書は `cifter` の release PR 作成から PyPI 公開、GitHub Release 添付までの開発者向け手順を定義する。

## 事前条件

- 正本は [docs/specs/release.md](/home/tkenji/Repos/cifter/docs/specs/release.md)
- release 対象の変更が `CHANGELOG.md` の `Unreleased` に整理されている
- Linux の必須 CI が通る状態である
- PyPI 側に GitHub Trusted Publisher が設定済みである

## release PR

1. `pyproject.toml` の version を次の `0.minor.patch` へ更新する
2. `CHANGELOG.md` の `Unreleased` から対象項目を `## [X.Y.Z] - YYYY-MM-DD` 節へ移す
3. release に伴って README、`docs/specs/`、`docs/` の更新が必要なら同じ PR に含める
4. PR で Linux の必須 CI が通ることを確認する

## tag と公開

1. release PR を merge する
2. merge 済み commit に `vX.Y.Z` tag を作成して push する
3. release workflow が version / changelog 整合、test、lint、type check、build、配布物検証、install smoke を再実行する
4. workflow が OIDC により PyPI へ publish する
5. PyPI publish 成功後に GitHub Release へ `wheel` と `sdist` を添付する

## GitHub Actions メモ

- release workflow では `id-token: write` を付与する
- publish step は `pypa/gh-action-pypi-publish` を使う
- GitHub Release 添付は PyPI publish 成功後に実行する

## 公開後確認

- PyPI に対象 version の `cifter-cli` が公開されている
- PyPI 上で `wheel` と `sdist` が参照できる
- GitHub Release に対象 version の `wheel` と `sdist` が両方ある
- release workflow の version / changelog 整合チェックが成功している
- release workflow の配布物検証で配布名、`LICENSE`、MIT メタデータ、project URL、keywords、classifiers の確認が成功している
- install smoke で `cift` と `python -m cifter` の起動確認が成功している
