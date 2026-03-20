# データモデル

## `RunResult`

- `tool_version`
- `command`
- `inputs`
- `results`
- `diagnostics`

## `ExtractionItem`

- `file`
- `symbol`
- `kind`
- `span`
- `language`
- `lines`
- `diagnostics`
- `routes`
- `highlights`

## `RunDiagnostic`

- `severity` は `error` または `warning`
- `code` は機械可読識別子
- `message` は利用者向け要約
- `file` は関連 path がある場合だけ持つ

## 既存型

- `SourceSpan` は行番号トレーサビリティ単位
- `ExtractedLine` は text / json 共通の 1 行表現
- `ParseDiagnostic` と `ParseQualityReport` は file 単位の parse 品質情報
- `TrackPath` と `RouteSegment` は外部 DSL の内部表現
