# ROADMAP

## 目的

この文書は、`cifter` を v0 試作から継続運用可能な CLI へ引き上げるための中長期課題を管理する。
`docs/specs/` の正本を置き換えるものではなく、実装優先順位と完了条件の整理だけを担う。

## フェーズ 2: 品質保証と配布運用

- Linux + Python 3.12 の必須 CI ゲートを GitHub Actions に構成する
- 必須 CI で `uv sync --frozen`、`uv run pytest`、`uv run ruff check .`、`uv run ty check .`、`uv build` を実行する
- 生成 wheel をクリーンな仮想環境へ install し、`cift --help`、`python -m cifter --help`、実コマンド 1 本の smoke を追加する
- Windows は追加対象として同一 wheel の install smoke のみ行う
- GitHub Release を正規配布先とし、tag から `wheel` / `sdist` を公開する
- version、tag、changelog の運用を固定する
- 配布確認手順とリリース手順を文書化する

完了条件:

- PR ごとに Linux の必須 CI ゲートが自動実行される
- 配布物から `cift` と `python -m cifter` が起動できる
- GitHub Release に `wheel` と `sdist` が添付される
- バージョン更新、tag 作成、変更履歴更新の手順が人間に再現可能である

## フェーズ 3: 解析精度と堅牢性強化

- `.h` を含む言語判定方針を見直す
- C++ 固有構文の回帰テストを拡充する
- 前処理の複雑ケースを強化する
- 対象はネスト、複数行ディレクティブ、複雑な `#define` / `#undef` 連鎖、未対応ディレクティブ混在とする
- parse quality を利用者へ返す仕組みを検討・追加する
- 文字コードと改行コードの扱いを明文化する
- 大規模入力に対する性能計測とボトルネック確認を行う
- 診断メッセージの分類と再現情報出力を整える

完了条件:

- C++ と前処理の追加回帰テストが安定して通る
- 解析品質が低い成功ケースを利用者が識別できる
- 既知制約が README または docs に明記されている

## 完了条件

- フェーズ 2 とフェーズ 3 は、今回の v0 仕様未達解消後にのみ着手する
- 各フェーズは、仕様変更が必要なら `docs/specs/` を先に更新する前提で進める
