package com.example;

public class AfterProductService {

    public String formatProductInfo(String name, double price, int stock) {
        double priceWithTax = price * 1.08;
        String availability = stock > 0 ? "Yes (qty: " + stock + ")" : "No";
        return String.format("Product: %s | Price: $%.2f | Available: %s",
            name, priceWithTax, availability);
    }

    public static void main(String[] args) {
        AfterProductService service = new AfterProductService();
        System.out.println(service.formatProductInfo("Widget", 9.99, 5));
    }
}
