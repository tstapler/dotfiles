/// process_request handles an incoming request string and returns a response.
/// NOTE: This is NOT a trait method — ast-grep rename is safe here.
fn process_request(req: &str) -> String {
    format!("processed: {}", req)
}

fn main() {
    let r1 = process_request("hello");
    let r2 = process_request("world");
    println!("{} {}", r1, r2);
}
