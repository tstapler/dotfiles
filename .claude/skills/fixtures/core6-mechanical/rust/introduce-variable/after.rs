struct Config {
    timeout_secs: u64,
}

fn compute_max_wait(config: &Config, retry_count: u64) -> u64 {
    let max_wait = config.timeout_secs * retry_count;
    if max_wait > 300 {
        max_wait
    } else {
        300
    }
}

fn main() {
    let config = Config { timeout_secs: 30 };
    println!("Max wait: {}s", compute_max_wait(&config, 5));
}
