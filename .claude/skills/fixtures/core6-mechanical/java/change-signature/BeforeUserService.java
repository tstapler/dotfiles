package com.example;

public class BeforeUserService {

    public String createUser(String email, String name) {
        return "user:" + name + ":" + email;
    }

    public void setupDefaults() {
        createUser("admin@example.com", "Admin");
        createUser("guest@example.com", "Guest");
        createUser("test@example.com", "Tester");
    }

    public static void main(String[] args) {
        BeforeUserService service = new BeforeUserService();
        System.out.println(service.createUser("alice@example.com", "Alice"));
    }
}
