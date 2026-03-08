use std::fs;
use std::io::BufRead;
use std::io::BufReader;
use std::io::BufWriter;
use std::io::Error;
use std::io::Write;
use std::path::Path;

use inquire::{Select, Text};

#[derive(Debug, PartialEq)]
struct Todo {
    id: u32,
    title: String,
    completed: bool,
}

#[derive(Debug, PartialEq)]
struct TodoList {
    todos: Vec<Todo>,
    next_id: u32,
    file_path: String,
}

impl TodoList {
    fn new(file_path: String) -> Self {
        // TODO: ファイルから読み込み
        TodoList {
            todos: Vec::new(),
            next_id: 1,
            file_path,
        }
    }

    fn init(&mut self) {
        if self.check_todo_list_file() {
            let file_lines = self.load_file();
            if let Ok(lines) = file_lines {
                if !lines.is_empty() {
                    *self = self.translate_to_todo_list(lines).unwrap();
                }
            }
            return;
        }

        self.create_todo_file();
    }

    fn check_todo_list_file(&self) -> bool {
        Path::new(self.file_path.as_str()).exists()
    }

    fn create_todo_file(&self) -> Result<(), Error> {
        if self.check_todo_list_file() {
            return Ok(());
        }

        fs::File::create(self.file_path.as_str())?;
        Ok(())
    }
    fn load_file(&self) -> Result<Vec<String>, String> {
        let mut todo_list = vec![];
        let file = fs::File::open(self.file_path.as_str()).map_err(|e| e.to_string())?;
        let reader = BufReader::new(file);
        for line in reader.lines() {
            let line_content = line.map_err(|e| e.to_string())?;
            todo_list.push(line_content);
        }

        Ok(todo_list)
    }

    fn translate_to_todo_list(&self, todo_list: Vec<String>) -> Result<TodoList, String> {
        let mut next_id = 0;

        let mut todos = vec![];

        for todo in &todo_list {
            let todo_elements: Vec<&str> = todo.split(' ').collect();
            let id = todo_elements[0].parse::<u32>().map_err(|e| e.to_string())?;
            todos.push(Todo {
                id,
                title: todo_elements[1].to_string(),
                completed: todo_elements[2]
                    .parse::<bool>()
                    .map_err(|e| e.to_string())?,
            });

            next_id = id + 1;
        }

        Ok(TodoList {
            todos,
            next_id,
            file_path: self.file_path.clone(),
        })
    }

    fn add(&mut self, title: String) -> Result<(), String> {
        if title.is_empty() {
            return Err(String::from("Set task title."));
        }

        match self.todos.iter().position(|x| x.title == title) {
            Some(index) => {
                if self.todos[index].completed {
                    self.todos.push(Todo {
                        id: self.next_id,
                        title,
                        completed: false,
                    });
                    self.next_id += 1;
                    return Ok(());
                }
                Ok(())
            }
            None => {
                self.todos.push(Todo {
                    id: self.next_id,
                    title,
                    completed: false,
                });
                self.next_id += 1;
                Ok(())
            }
        }
    }

    fn list(&self) -> &Vec<Todo> {
        &self.todos
    }

    fn complete(&mut self, id: u32) -> Result<(), String> {
        match self.todos.iter().position(|x| x.id == id) {
            Some(index) => {
                self.todos[index].completed = true;
                Ok(())
            }
            None => Err(String::from("Not id in this todo list")),
        }
    }

    fn remove(&mut self, id: u32) -> Result<(), String> {
        match self.todos.iter().position(|x| x.id == id) {
            Some(index) => {
                self.todos.remove(index);
                self.next_id = self.todos.iter().map(|t| t.id).max().unwrap_or(0) + 1;
                Ok(())
            }
            None => Err(String::from("Not id in this todo list")),
        }
    }

    fn save(&self) -> Result<(), String> {
        if !(self.check_todo_list_file()) {
            return Err(String::from("not found file"));
        }

        // ファイルの中身初期化
        fs::write(&self.file_path, "").map_err(|e| e.to_string())?;

        // todoを追記処理
        let file = fs::OpenOptions::new()
            .append(true)
            .open(&self.file_path)
            .map_err(|e| e.to_string())?;
        let mut writer = BufWriter::new(file);

        for todo in &self.todos {
            let record = format!("{} {} {}", todo.id, todo.title, todo.completed);
            writeln!(writer, "{}", record).map_err(|e| e.to_string())?;
        }

        Ok(())
    }
}

fn handle_add(todo_list: &mut TodoList, title: String) -> Result<String, String> {
    todo_list.add(title.clone())?;
    Ok(format!("Task added: {}", title))
}

fn handle_done(todo_list: &mut TodoList, id: u32) -> Result<String, String> {
    todo_list.complete(id)?;
    Ok(format!("Task completed: {}", id))
}

fn handle_remove(todo_list: &mut TodoList, id: u32) -> Result<String, String> {
    todo_list.remove(id)?;
    Ok(format!("Task remove: {}", id))
}

fn run_app_loop(todo_list: &mut TodoList) {
    let actions = vec!["list", "add", "done", "remove", "save", "quit"];

    loop {
        let action = Select::new("Select action", actions.clone())
            .prompt()
            .unwrap_or("quit");

        match action {
            "add" => {
                let title = Text::new("Task title:").prompt().unwrap_or_default();
                match handle_add(todo_list, title) {
                    Ok(msg) => println!("{}", msg),
                    Err(e) => println!("Error: {}", e),
                }
            }
            "list" => {
                let list = todo_list.list();
                if list.is_empty() {
                    println!("No tasks.");
                } else {
                    println!("{:<4} {:<20} {}", "id", "title", "completed");
                    for record in list {
                        println!("{:<4} {:<20} {}", record.id, record.title, record.completed);
                    }
                }
            }
            "done" => {
                let id = Text::new("Id:").prompt().unwrap_or_default().parse::<u32>();
                match id {
                    Ok(id) => match handle_done(todo_list, id) {
                        Ok(msg) => println!("{}", msg),
                        Err(e) => println!("Error: {}", e),
                    },
                    Err(_) => println!("Error: invalid id"),
                }
            }
            "remove" => {
                let id = Text::new("Id:").prompt().unwrap_or_default().parse::<u32>();
                match id {
                    Ok(id) => match handle_remove(todo_list, id) {
                        Ok(msg) => println!("{}", msg),
                        Err(e) => println!("Error: {}", e),
                    },
                    Err(_) => println!("Error: invalid id"),
                }
            }
            "save" => match todo_list.save() {
                Ok(_) => println!("Saved."),
                Err(e) => println!("Error: {}", e),
            },
            _ => break,
        }
    }
}

fn main() {
    let mut todo_list = TodoList::new(String::from("./todo_list.txt"));
    todo_list.init();
    run_app_loop(&mut todo_list);
}

#[cfg(test)]

mod tests {
    use core::panic;
    use std::{fs, io::Write};

    use tempfile::NamedTempFile;

    use super::*;

    #[test]
    fn test_judge_todolist_file() {
        let mut file = NamedTempFile::new().unwrap();
        let file_path = String::from(file.path().to_str().unwrap());

        let todo_list = TodoList::new(file_path);

        let find_file = todo_list.check_todo_list_file();
        assert_eq!(true, find_file);
    }

    #[test]
    fn test_load_1_line_file() {
        let mut file = NamedTempFile::new().unwrap();
        file.write_all(b"1 test false").unwrap();
        let file_path = String::from(file.path().to_str().unwrap());

        let todo_list = TodoList::new(file_path);
        let load_result = todo_list.load_file();
        assert_eq!(Ok(vec![String::from("1 test false")]), load_result);
    }

    #[test]
    fn test_translate_todo_data_type() {
        let mut file = NamedTempFile::new().unwrap();
        file.write_all(b"1 test false").unwrap();
        let file_path = String::from(file.path().to_str().unwrap());
        let expects_file_path = file_path.clone();

        let todo_list = TodoList::new(file_path);
        let load_result = todo_list.load_file();

        let translate_result = todo_list.translate_to_todo_list(load_result.unwrap());

        assert_eq!(
            Ok(TodoList {
                todos: vec![Todo {
                    id: 1,
                    title: String::from("test"),
                    completed: false
                }],
                next_id: 2,
                file_path: expects_file_path
            }),
            translate_result
        );
    }

    #[test]
    fn test_if_not_exists_create_file() {
        let file_path = String::from("test-file.txt");
        let clone_file_path = file_path.clone();
        let todo_list = TodoList::new(file_path);

        let create_result = todo_list.create_todo_file();

        assert!(create_result.is_ok());
        fs::remove_file(clone_file_path);
    }

    #[test]
    fn test_add_taskA() {
        let mut todo_list = TodoList::new(String::from("./test-file.txt"));
        let add_result = todo_list.add(String::from("taskA"));

        assert!(add_result.is_ok());
        assert_eq!(String::from("taskA"), todo_list.todos[0].title);
    }

    #[test]
    fn test_skip_add_duplicate_task() {
        let mut todo_list = TodoList::new(String::from("./test-file.txt"));
        todo_list.add(String::from("taskA"));
        todo_list.add(String::from("taskA"));

        assert_eq!(1, todo_list.todos.len());
    }

    #[test]
    fn test_return_empty_list() {
        let mut todo_list = TodoList::new(String::from("./test-file.txt"));
        let task_list: &Vec<Todo> = todo_list.list();
        let expected: Vec<Todo> = vec![];

        assert_eq!(&expected, task_list);
    }

    #[test]
    fn test_return_ascending_todos() {
        let mut todo_list = TodoList::new(String::from("./test-file.txt"));

        todo_list.add(String::from("taskA"));
        todo_list.add(String::from("taskB"));

        let expected_todos: Vec<Todo> = vec![
            Todo {
                id: 1,
                title: String::from("taskA"),
                completed: false,
            },
            Todo {
                id: 2,
                title: String::from("taskB"),
                completed: false,
            },
        ];

        assert_eq!(expected_todos, todo_list.todos);
    }

    #[test]
    fn test_updated_tasks_to_complete() {
        let mut todo_list = TodoList::new(String::from("./test-file.txt"));
        todo_list.add(String::from("taskA"));

        todo_list.complete(1);

        assert!(todo_list.todos[0].completed);
    }

    #[test]
    fn test_return_error_when_set_not_exists_id() {
        let mut todo_list = TodoList::new(String::from("./test-file.txt"));
        let complete_result = todo_list.complete(1);

        assert!(complete_result.is_err());
    }

    #[test]
    fn test_check_remove_id_1_task() {
        let file_path = String::from("./test-file.txt");
        let clone_file_path = file_path.clone();
        let mut todo_list = TodoList::new(file_path);
        todo_list.add(String::from("taskA"));

        todo_list.remove(1);

        let except_result = TodoList::new(clone_file_path);

        assert_eq!(except_result, todo_list);
    }

    #[test]
    fn test_add_two_task_and_remove_id1_remain_second_task() {
        let mut todo_list = TodoList::new(String::from("./test-file.txt"));
        todo_list.add(String::from("taskA"));
        todo_list.add(String::from("taskB"));

        todo_list.remove(1);

        let except_result = TodoList {
            todos: vec![Todo {
                id: 2,
                title: String::from("taskB"),
                completed: false,
            }],
            next_id: 3,
            file_path: String::from("./test-file.txt"),
        };

        assert_eq!(except_result, todo_list);
    }

    #[test]
    fn test_return_error_when_set_not_exists_id_to_remove() {
        let mut todo_list = TodoList::new(String::from("./test-file.txt"));
        let remove_result = todo_list.remove(1);

        assert!(remove_result.is_err());
    }

    #[test]
    fn test_save_taskA_right_write() {
        let mut file = NamedTempFile::new().unwrap();
        file.write_all(b"1 test false").unwrap();
        let file_path = String::from(file.path().to_str().unwrap());

        let mut todo_list = TodoList::new(file_path);

        todo_list.add(String::from("taskA"));
        todo_list.save();

        let load_result = todo_list.load_file();
        assert_eq!(Ok(vec![String::from("1 taskA false")]), load_result);
    }

    #[test]
    fn test_error_open_file_to_save() {
        let file_path = String::from("./not-exists.txt");

        let mut todo_list = TodoList::new(file_path);
        let save_result = todo_list.save();
        assert!(save_result.is_err());
    }

    #[test]
    fn test_handle_add_returns_success_message() {
        let mut todo_list = TodoList::new(String::from("./test-file.txt"));
        let result = handle_add(&mut todo_list, String::from("taskA"));

        assert_eq!(Ok(String::from("Task added: taskA")), result);
    }

    // TODO(human): test_handle_add_returns_error_message_when_empty_title を実装する

    #[test]
    fn test_handle_done_returns_success_message() {
        let mut todo_list = TodoList::new(String::from("./test-file.txt"));

        let result_add = handle_add(&mut todo_list, String::from("taskA"));
        let result_done = handle_done(&mut todo_list, 1);
        assert_eq!(Ok(String::from("Task completed: 1")), result_done);
    }

    #[test]
    fn test_handle_remove_id_1_success_message() {
        let mut todo_list = TodoList::new(String::from("./test-file.txt"));

        let result_add = handle_add(&mut todo_list, String::from("taskA"));
        let result_remove = handle_remove(&mut todo_list, 1);

        assert_eq!(Ok(String::from("Task remove: 1")), result_remove);
    }
}
