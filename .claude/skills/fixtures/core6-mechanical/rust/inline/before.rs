fn normalize_email(email: &str) -> String {
    email.trim().to_lowercase()
}

fn create_user(name: &str, email: &str) -> (String, String) {
    let normalized_email = normalize_email(email);
    (name.to_string(), normalized_email)
}

fn main() {
    let (name, email) = create_user("Alice", "  Alice@Example.COM  ");
    println!("User: {} <{}>", name, email);
}
