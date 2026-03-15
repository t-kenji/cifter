# 開発者向け概要

実装は次の責務分割を前提にする。

- `preprocessor`: 条件分岐前処理
- `parser`: tree-sitter 解析と関数探索
- `extract_function`: 関数本体抽出
- `extract_flow`: 制御骨格抽出
- `extract_path`: 親構造と直列文脈を保ちながらの route 抽出
- `render`: 行番号付き text レンダリング
- `cli`: Typer ベースの公開 CLI

renderer は人が読む断片コードを返す。
JSON 出力は対象外とする。

運用手順は [release.md](/home/tkenji/Repos/cifter/docs/release.md) を参照する。
