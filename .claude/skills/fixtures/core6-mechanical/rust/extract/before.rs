fn create_account(username: &str, email: &str, age: u32) -> Result<String, String> {
    // Validation block — candidate for extraction
    if username.is_empty() {
        return Err("username cannot be empty".to_string());
    }
    if username.len() < 3 {
        return Err("username must be at least 3 characters".to_string());
    }
    if email.is_empty() {
        return Err("email cannot be empty".to_string());
    }
    if age < 18 {
        return Err("must be at least 18 years old".to_string());
    }

    Ok(format!("acct_{}", username))
}

fn main() {
    match create_account("alice", "alice@example.com", 25) {
        Ok(id) => println!("Created: {}", id),
        Err(e) => println!("Error: {}", e),
    }
}
