---
name: update-study-notes-index
description: Keep this repository's root index.html synchronized with its study-note HTML files. Use after adding, deleting, renaming, moving, or substantially editing a note, including requests that modify note HTML without explicitly mentioning the index. Also use for index refreshes, category changes, search metadata updates, note-count checks, and broken-link audits.
---

# Update Study Notes Index

ルートの `index.html` を、リポジトリ内の学習ノートHTMLと同期する。
ユーザーが明示的に除外しない限り、ノートを変更した同じ作業内でindexも更新する。

## Workflow

1. `git status --short` と `git diff` を確認し、ユーザーの未コミット変更を把握する。無関係な変更は戻さない。
2. 次のコマンドを実行し、未掲載ページ、重複、リンク切れ、件数、カテゴリの問題を確認する。

```powershell
python .agents/skills/update-study-notes-index/scripts/check_index.py --root .
```

3. 追加・変更されたHTMLから、`<title>`、`<h1>`、明示された日付、冒頭の説明、主要な見出しを読む。ファイル名や更新日時だけから日付を推測しない。
4. 既存のカード構造とデザインを保って `index.html` を編集する。
5. 検証コマンドを再実行し、エラーが0件になるまで修正する。
6. `git diff --check` と `git diff -- index.html` を確認する。

## Update Rules

### ノートを追加した場合

- `.note-card` を1ページにつき1件追加する。
- 明示された日付があるカードは新しい順に並べる。
- 日付がない技術解説は、関連するまとまりの末尾または日付付き記録の後に置く。
- `#visible-count` を `.note-card` の総数に合わせる。

### ノートを修正した場合

- タイトル、主題、日付、主要キーワードが変わったときだけ、対応するカードの表示内容を同期する。
- 軽微な誤字修正やコード修正では、カードの説明が不正確にならない限りindexを変更しない。
- カードの掲載順は、日付または分類上の理由がない限り維持する。

### ノートを改名・移動・削除した場合

- 改名・移動では既存カードの `href` を更新し、古いカードを残さない。
- 削除では対応カードを削除し、件数も更新する。
- 使用されなくなったカテゴリボタンは削除する。複数カードで使うカテゴリは維持する。

## Card Contract

各カードで次を維持する。

- `data-category`: ASCIIのカテゴリslug。複数なら空白区切り。各slugに対応する `.filter-button[data-filter]` を用意する。
- `data-search`: タイトルだけでは検索しにくい日本語・英語の用語、技術名、同義語を空白区切りで含める。
- `.category`: 読みやすい表示名。複数カテゴリは ` / ` で区切る。
- `<time datetime="YYYY-MM-DD">`: ソースに明示された日付がある場合だけ使う。表示は `YYYY.MM.DD` とする。
- 日付がない場合: `<time>` を捏造せず、`<span>技術整理</span>` など内容に合うラベルを使う。
- `<h2>`: ノートの主題が分かる簡潔なタイトル。
- `.description`: 学べる内容を1文で要約する。本文にない内容を追加しない。
- `.tags`: 主要キーワードを原則3〜4件。
- `.card-link`: リポジトリルートからの相対パスを `/` 区切りで指定する。

新しいカテゴリは複数ページをまとめる意味がある場合に追加する。一時的な細分類を増やしすぎない。

## Scope

- ユーザーの依頼がindex更新だけなら、ノート本文は編集しない。
- `.git`、`.agents` などの隠しディレクトリ内のHTMLは学習ノートとして扱わない。
- CSSやJavaScriptを全面的に作り直さず、既存の検索、カテゴリ絞り込み、レスポンシブ表示を保つ。
- 新しいカードのためだけに外部ライブラリやビルド処理を追加しない。

## Validation

HTMLの検証にPlaywrightやその他のブラウザ自動操作ツールを使用しない。
検証は、以下の静的確認と必要に応じたローカルHTTPレスポンス確認で行う。

`scripts/check_index.py` は次をエラーとして検出する。

- `index.html` に掲載されていない学習ノートHTML
- 存在しないファイルへのカードリンク
- 同じHTMLへの重複カード
- カード数と `#visible-count` の不一致
- `data-category` に対応する絞り込みボタンの不足

追加で次を確認する。

- `git diff --check` で空白エラーや競合マーカーがないこと
- HTML内の目次リンク先IDが存在し、IDが重複していないこと
- CSSや画像などの相対参照先が存在すること
- 必要な場合のみ、一時ローカルHTTPサーバーへのリクエストが200を返すこと

検証が失敗した状態を完了として報告しない。意図的に掲載しないHTMLが必要になった場合は、黙って無視せず、検証スクリプトの除外設計も同時に更新する。
