package com.example;

public class BeforeUserProcessor {

    public String registerUser(String username, String email, int age) {
        // Validation block — candidate for extraction
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

        return "user_" + username;
    }

    public static void main(String[] args) {
        BeforeUserProcessor processor = new BeforeUserProcessor();
        System.out.println(processor.registerUser("alice", "alice@example.com", 25));
    }
}
