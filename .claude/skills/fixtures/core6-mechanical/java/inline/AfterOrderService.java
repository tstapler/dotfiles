package com.example;

public class AfterOrderService {

    public double calculateTotal(double price, int quantity) {
        return price * quantity + price * quantity * 0.08 + 5.99;
    }

    public static void main(String[] args) {
        AfterOrderService service = new AfterOrderService();
        System.out.println(service.calculateTotal(10.00, 3));
    }
}
