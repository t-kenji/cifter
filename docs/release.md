# リリース手順

この文書は `cifter` の release PR 作成から GitHub Release 公開までの手順を定義する。

## 事前条件

- `docs/specs/release.md` を正本とする
- release 対象の変更が `CHANGELOG.md` の `Unreleased` に整理されている
- Linux の必須 CI が通る状態である

## release PR

1. `pyproject.toml` の version を次の `0.minor.patch` へ更新する
2. `CHANGELOG.md` の `Unreleased` から対象項目を `## [X.Y.Z] - YYYY-MM-DD` 節へ移す
3. release に伴って README または `docs/specs/` の更新が必要なら同じ PR に含める
4. PR で Linux の必須 CI が通ることを確認する

## tag と公開

1. release PR を merge する
2. merge 済み commit に `vX.Y.Z` tag を作成して push する
3. GitHub Actions の release workflow が Linux の必須ゲートを再実行する
4. workflow が `wheel` と `sdist` を GitHub Release に添付する

## 公開後確認

- GitHub Release に対象 version の `wheel` と `sdist` が両方ある
- release workflow の version / changelog 整合チェックが成功している
- release workflow の配布物検証で `wheel` / `sdist` への `LICENSE` 同梱と MIT メタデータ確認が成功している
- Windows smoke は互換性観測用として結果を確認する
