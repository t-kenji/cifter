# Route DSL

この文書は `path --route` DSL の開発者向け整理である。正本は [docs/specs/path-route-dsl.md](/home/tkenji/Repos/cifter/docs/specs/path-route-dsl.md) を参照する。

## 外部形

- canonical form は `/` 区切りのみ
- segment は `case[...]` / `default` / `if[...]` / `else` / `else-if[...]` / `for` / `for[...]` / `while` / `while[...]` / `do-while` / `do-while[...]`
- 旧 `>` 記法、`else if[...]`、`do while[...]` は受理しない

## Scanner

- route 全体を 1 文字ずつ走査し、`[]` 深さ 0 の `/` だけを segment 区切りとする
- payload 内では入れ子の `[]` を許可する
- 文字列リテラルと文字リテラルを認識し、引用符内の `]` と `/` は区切り扱いしない
- payload のエスケープ解釈は C 文字列相当の最小限で、引用符終端判定にだけ使う

## 内部表現

`RouteSegment` は次を持つ。

- `kind`: `case` / `default` / `if` / `else` / `else_if` / `for` / `while` / `do_while`
- `raw`: 利用者入力の 1 segment
- `payload`: `[]` 内の生文字列。payload なしなら `None`
- `normalized_payload`: kind ごとの比較用正規化結果。不要なら `None`

正規化は次で固定する。

- `case[...]`: trim のみ
- `if[...]` / `else-if[...]` / `while[...]` / `do-while[...]`: trim、連続空白の 1 個化、冗長な外側丸括弧除去
- `for[...]`: trim、連続空白の 1 個化

## Matching

- 各段で現在コンテナ直下の文だけを見る
- `case` / `default` は `switch` 配下の `case_statement` から探す
- `for` / `while` / `do-while` は中間コンテナとして辿れる
- `else-if[...]` は `else_clause` 直下の `if_statement` を独立 segment として照合する
- 一致候補が複数ある場合はソース順最初の一致を採用する
- 一致候補 0 件だけが失敗条件である

## 実装上の注意

- `for[...]` は `for_statement` の `(` と `)` の内側全文字列を比較する
- 条件正規化では文字列・文字リテラル内の空白は壊さない
- route 終端後の通常文保持、共通祖先の統合、`...` の挿入契約は DSL 変更後も維持する
