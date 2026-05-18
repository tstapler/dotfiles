package com.example;

public class BeforeOrderService {

    public double calculateTotal(double price, int quantity) {
        double lineTotal = price * quantity;
        double taxAmount = lineTotal * 0.08;
        double shippingCost = 5.99;
        double grandTotal = lineTotal + taxAmount + shippingCost;
        return grandTotal;
    }

    public static void main(String[] args) {
        BeforeOrderService service = new BeforeOrderService();
        System.out.println(service.calculateTotal(10.00, 3));
    }
}
