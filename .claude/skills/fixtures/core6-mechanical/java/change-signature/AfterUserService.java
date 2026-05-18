package com.example;

public class AfterUserService {

    // Parameters reordered: createUser(name, email) instead of createUser(email, name)
    public String createUser(String name, String email) {
        return "user:" + name + ":" + email;
    }

    public void setupDefaults() {
        createUser("Admin", "admin@example.com");
        createUser("Guest", "guest@example.com");
        createUser("Tester", "test@example.com");
    }

    public static void main(String[] args) {
        AfterUserService service = new AfterUserService();
        System.out.println(service.createUser("Alice", "alice@example.com"));
    }
}
