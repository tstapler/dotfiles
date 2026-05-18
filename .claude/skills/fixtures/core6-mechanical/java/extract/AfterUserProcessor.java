package com.example;

public class AfterUserProcessor {

    private void validateInput(String username, String email, int age) {
        if (username == null || username.isEmpty()) {
            throw new IllegalArgumentException("username cannot be empty");
        }
        if (username.length() < 3) {
            throw new IllegalArgumentException("username must be at least 3 characters");
        }
        if (email == null || !email.contains("@")) {
            throw new IllegalArgumentException("invalid email address");
        }
        if (age < 18) {
            throw new IllegalArgumentException("must be at least 18 years old");
        }
    }

    public String registerUser(String username, String email, int age) {
        validateInput(username, email, age);
        return "user_" + username;
    }

    public static void main(String[] args) {
        AfterUserProcessor processor = new AfterUserProcessor();
        System.out.println(processor.registerUser("alice", "alice@example.com", 25));
    }
}
