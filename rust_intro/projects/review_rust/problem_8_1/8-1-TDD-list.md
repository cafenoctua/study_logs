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

---

## Phase 2: inquire による対話型CLIインターフェース

### 設計方針

現在の `clap` によるサブコマンド方式（`cargo run -- add "taskA"`）から、
`inquire` による対話型ループ方式（`cargo run` で起動後にメニュー選択）へ移行する。

#### アーキテクチャ

```
main()
 └─ run_app_loop(todo_list)        // メインループ（繰り返しメニューを表示）
     ├─ select_action()            // inquire::Select でアクション選択
     └─ match action
         ├─ "add"    → handle_add(todo_list)
         ├─ "list"   → handle_list(todo_list)
         ├─ "done"   → handle_done(todo_list)
         ├─ "remove" → handle_remove(todo_list)
         ├─ "save"   → handle_save(todo_list)
         └─ "quit"   → break
```

#### 責務分離の方針

- `TodoList` のビジネスロジックは変更しない
- UI層（inquire呼び出し）を `handle_*` 関数として分離する
- `handle_*` 関数はビジネスロジックの戻り値（`Result`）を受け取り、ユーザーへのフィードバックを担う

#### 追加する依存

```toml
inquire = "0.7"
```

#### 想定UI詳細

```
? Select action › (矢印キーで選択)
❯ list
  add
  done
  remove
  save
  quit

# addを選択した場合
? Task title: › taskA

✔ Task added: taskA

# listを選択した場合
id  title  completed
1   taskA  false

# doneを選択した場合
? Task ID: › 1
✔ Task completed: id=1

# removeを選択した場合
? Task ID: › 1
✔ Task removed: id=1

# saveを選択した場合
✔ Saved.

# 存在しないIDを指定した場合
✘ Error: Not id in this todo list
```

---

### test element（Phase 2）

#### handle_add

- [ ] タイトルを入力してタスクが追加された後に成功メッセージが出力される
- [ ] 空文字を入力したときにエラーメッセージが出力される

#### handle_list

- [ ] タスクが0件のとき、空リストを表示しても正常終了する
- [ ] タスクが複数件あるとき、id昇順で全件表示される

#### handle_done

- [ ] 存在するIDを入力したときにタスクが完了状態になる
- [ ] 存在しないIDを入力したときにエラーメッセージが出力される

#### handle_remove

- [ ] 存在するIDを入力したときにタスクが削除される
- [ ] 存在しないIDを入力したときにエラーメッセージが出力される

#### handle_save

- [ ] saveを選択したときにファイルへの書き込みが成功する
- [ ] ファイルが存在しない状態でsaveを選択したときにエラーメッセージが出力される

#### run_app_loop

- [ ] quitを選択したときにループが終了する
- [ ] 一連の操作（add → list → save → quit）が正常に完了する
