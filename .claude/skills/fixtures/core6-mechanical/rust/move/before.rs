// File: src/services.rs (before move)
// UserService will be moved to src/core/user.rs

pub struct UserService {
    users: std::collections::HashMap<String, String>,
}

impl UserService {
    pub fn new() -> Self {
        UserService {
            users: std::collections::HashMap::new(),
        }
    }

    pub fn add_user(&mut self, id: String, name: String) {
        self.users.insert(id, name);
    }

    pub fn get_user(&self, id: &str) -> Option<&String> {
        self.users.get(id)
    }
}

fn main() {
    let mut svc = UserService::new();
    svc.add_user("1".to_string(), "Alice".to_string());
    println!("{:?}", svc.get_user("1"));
}
