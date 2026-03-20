# データモデル

`cifter` のデータモデルは、CLI、run、抽出器、renderer の間をつなぐ共有言語です。
ここで重要なのは、型の一覧そのものよりも「どの型がどの層をまたぐか」です。

## 全体像

代表的な型は次の 3 段に分かれます。

- run 全体を表す型
- 1 抽出結果を表す型
- parse / route / line 単位の補助型

## run 全体を表す型

### `RunResult`

`RunResult` は 1 回の実行全体の結果です。

持つ情報:

- 実行した command
- 対象 input 集合
- 抽出できた result 集合
- run 全体の diagnostics
- tool version

役割:

- CLI が最終終了コードを決めるための材料
- renderer が text/json を生成するための入力
- run 成功か warning 付き成功か失敗かを表す単位

### `RunDiagnostic`

`RunDiagnostic` は run レベルの warning / error を表します。

典型例:

- 関数未一致
- DSL 不正
- parse 失敗
- `no_results`

file を持つ場合と持たない場合があります。
つまり「特定 file にひもづく問題」と「run 全体の問題」の両方を表せます。

## 1 抽出結果を表す型

### `ExtractionItem`

`ExtractionItem` は 1 match 分の抽出結果です。

持つ情報:

- file
- symbol
- kind
- span
- language
- lines
- diagnostics
- routes

役割:

- text/json 共通の中間表現
- 抽出器の結果を renderer へ渡す橋渡し
- file ごとの抽出結果と、その file に固有の診断情報を保持する

重要なのは、renderer が source を再解析しないことです。
表示に必要な情報は `ExtractionItem` に集約されます。

### `SourceSpan`

`SourceSpan` は元ソース上の範囲を表します。

`start_line` と `end_line` を持ち、抽出結果が元ソースのどこに対応するかを示します。
これはトレーサビリティの中心です。

### `ExtractedLine`

`ExtractedLine` は 1 行の表示単位です。

持つ情報:

- line number
- text
- inline highlight
- omission marker

抽出器は最終的にこの単位へ落とし込みます。
text/json の違いはあっても、共通の土台は `ExtractedLine` です。

## parse と品質に関わる型

### `ParseDiagnostic`

前処理や parse の過程で生じた品質情報です。

例:

- BOM 正規化
- 改行正規化
- parse error node 検出
- missing node 検出

抽出が成功しても、品質情報として結果へ残る場合があります。

### `ParseQualityReport`

parse 結果の品質をまとめる型です。
`clean` / `degraded` のような水準を持ち、`ParseDiagnostic` 群を束ねます。

## route と track に関わる型

### `TrackPath`

`flow --track` 用の内部表現です。

利用者入力の文字列をそのまま持つだけではなく、比較しやすい正規化済み表現も持ちます。
これにより、抽出器は track 一致判定だけに集中できます。

### `RouteSegment`

route DSL を segment 単位に分解した内部表現です。

例:

- `else`
- `else-if[value == 10]`
- `case[CMD_OK]`

1 本の route 文字列は `RouteSegment` の列として扱われます。
`route` 抽出器はこの列を順に消費しながら枝をたどります。

## 層をまたぐ関係

- CLI は `RunResult` を受けて終了コードと出力形式を決める
- run 層は `ParsedSource` から `ExtractionItem` と `RunDiagnostic` を組み立てる
- 抽出器は `ExtractedLine` と `SourceSpan` を返す
- renderer は `RunResult` / `ExtractionItem` / `ExtractedLine` を読む

この構造により、実装は「何を抽出したか」と「どう見せるか」を分離できます。
