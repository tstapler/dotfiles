struct Config {
    multiplier: f64,
}

struct Item {
    name: String,
    value: f64,
}

fn process(items: &[Item], config: &Config) -> f64 {
    items.iter().map(|i| i.value * config.multiplier).sum()
}

fn main() {
    let config = Config { multiplier: 1.0 };
    let items = vec![
        Item { name: "a".to_string(), value: 1.0 },
        Item { name: "b".to_string(), value: 2.5 },
    ];
    let total = process(&items, &config);
    let also_total = process(&items, &config);
    let third = process(&items, &config);
    println!("{} {} {}", total, also_total, third);
}
