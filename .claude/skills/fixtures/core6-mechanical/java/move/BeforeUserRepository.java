// File: com/example/services/BeforeUserRepository.java (before move)
// This class will be moved to com/example/repository/UserRepository.java
package com.example.services;

import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

public class BeforeUserRepository {

    private final Map<String, String> store = new HashMap<>();

    public void save(String id, String name) {
        store.put(id, name);
    }

    public Optional<String> findById(String id) {
        return Optional.ofNullable(store.get(id));
    }

    public static void main(String[] args) {
        BeforeUserRepository repo = new BeforeUserRepository();
        repo.save("1", "Alice");
        System.out.println(repo.findById("1"));
    }
}
