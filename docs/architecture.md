# アーキテクチャ

実装は小さな責務ごとに分割しています。公開インターフェースは CLI だけで、内部モジュールはそのための組み立て部品です。

## モジュール責務

- `src/cifter/cli.py`: Typer command 定義、引数解釈、終了コード変換
- `src/cifter/preprocessor.py`: 条件分岐前処理と行番号維持
- `src/cifter/parser.py`: 言語判定、tree-sitter parse、関数探索、source slice 補助
- `src/cifter/extract_function.py`: 関数全体抽出
- `src/cifter/extract_flow.py`: 制御骨格抽出と track 保持判定
- `src/cifter/extract_path.py`: route 解析結果に基づく枝抽出
- `src/cifter/tree_helpers.py`: `flow` / `path` で共有する tree-sitter 補助
- `src/cifter/render.py`: 行番号付き text レンダリング
- `src/cifter/model.py`: 共有データ型、route / track 正規化
- `src/cifter/errors.py`: 利用者向け失敗表現

## 依存方向

- `cli` は `parser`、`extract_*`、`render`、`model`、`errors` に依存します
- `extract_*` は `parser` と `model` を使います
- `extract_flow` / `extract_path` は `tree_helpers` を共有します
- `parser` は `preprocessor` を使います
- `render` は `model` だけに依存します
- `errors` は末端に置き、他モジュールから参照されます

## 設計上の意図

- 前処理と構文解析を分離し、行番号維持の責務を明確にします
- 抽出ロジックを `function` / `flow` / `path` で分け、仕様差分を局所化します
- `flow` / `path` に共通する AST 走査は helper へ寄せ、分岐構造の解釈差分だけを各抽出器へ残します
- 利用者向けの失敗文言は CLI 層で一貫して返します
- 出力形式を `ExtractionResult` に閉じ込め、将来の renderer 差し替え余地を残します
