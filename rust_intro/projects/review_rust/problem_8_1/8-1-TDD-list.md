# 作るもの

TODOリストの管理CLIアプリ
コマンドライン引数からTODO管理するアプリ

## 要件

- `add <title>`: TODOを追加
- `list`: 全TODOを表示
- `done <id>`: TODOを完了にする
- `remove <id>`: TODOを削除
- TODOはファイルに保存/読み込み

## 想定UI

```
> cargo run

Select action

- list
- add
- complete
- remove
- save

# Add task

task Name: xxx

Select action

- list
- add
- complete
- remove
- save

# Task List

id task completed
1 xxx false

Select action

- list
- add
- complete
- remove
- save

Save Todos

```

## test element

### 初期処理

- [x] 実行したディレクトリにTODOリストファイルがあるか判定
- [x] 実行したディレクトリにTODOリストファイルがある場合はそれを読み込む
- [x] ファイルを読み込んで正しくTodo型の配列に変換できているか
- [x] TODOリストファイルがない場合に新規ファイル生成がされているか

### タスク追加

- [x] 「taskA」を追加したときに成功が返される
- [x] 同一タスクで完了状態でない場合は、追加がスキップされる

### タスク一覧表示

- [x] 空の状態であれば空のタスクを返す
- [x] タスクが複数ある場合は、idを昇順で返す

### タスク完了

- [x] id: 1を指定したときにid: 1のタスクが完了している
- [x] idが存在しないIDを指定したらエラーを返す

### タスク削除

- [x] id: 1を指定したときにid: 1のタスクが削除されているか
- [x] next_idが2でid: 1のタスクが削除された後のnext_idが1になっているか
- [x] next_idが3でid: 1のタスクが削除されてもnext_idが3のままか
- [x] 存在しないIDを指定したらエラーを返す

### タスクの保存

- [x] taskA追加して保存した後にtodo listファイルを読み込んだら`1 taskA false` を返す
- [x] 書き込み対象のファイルを開こうとして失敗したらエラーが返されるか
