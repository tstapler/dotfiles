fn create_user(name: &str, email: &str) -> (String, String) {
    let normalized_email = email.trim().to_lowercase();
    (name.to_string(), normalized_email)
}

fn main() {
    let (name, email) = create_user("Alice", "  Alice@Example.COM  ");
    println!("User: {} <{}>", name, email);
}
