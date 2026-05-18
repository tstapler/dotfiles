package com.example;

public class AfterRequestService {

    public String handleRequest(String input) {
        return "processed: " + input.trim();
    }

    public void handleMultiple(String[] inputs) {
        for (String input : inputs) {
            String result = handleRequest(input);
            System.out.println(result);
        }
    }

    public static void main(String[] args) {
        AfterRequestService service = new AfterRequestService();
        service.handleRequest("hello");
        service.handleRequest("world");
        service.handleRequest("test");
    }
}
