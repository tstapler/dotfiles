package com.example;

public class BeforeProductService {

    public String formatProductInfo(String name, double price, int stock) {
        return String.format("Product: %s | Price: $%.2f | Available: %s",
            name,
            price * 1.08,
            stock > 0 ? "Yes (qty: " + stock + ")" : "No");
    }

    public static void main(String[] args) {
        BeforeProductService service = new BeforeProductService();
        System.out.println(service.formatProductInfo("Widget", 9.99, 5));
    }
}
