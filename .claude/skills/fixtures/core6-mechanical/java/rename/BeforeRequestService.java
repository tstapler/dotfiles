package com.example;

public class BeforeRequestService {

    public String processRequest(String input) {
        return "processed: " + input.trim();
    }

    public void handleMultiple(String[] inputs) {
        for (String input : inputs) {
            String result = processRequest(input);
            System.out.println(result);
        }
    }

    public static void main(String[] args) {
        BeforeRequestService service = new BeforeRequestService();
        service.processRequest("hello");
        service.processRequest("world");
        service.processRequest("test");
    }
}
