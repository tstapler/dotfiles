struct Item {
    name: String,
    value: f64,
}

fn process(items: &[Item]) -> f64 {
    items.iter().map(|i| i.value).sum()
}

fn main() {
    let items = vec![
        Item { name: "a".to_string(), value: 1.0 },
        Item { name: "b".to_string(), value: 2.5 },
    ];
    let total = process(&items);
    let also_total = process(&items);
    let third = process(&items);
    println!("{} {} {}", total, also_total, third);
}
