// File: com/example/repository/AfterUserRepository.java (after move)
// Moved from com.example.services
// All import statements updated: import com.example.services.UserRepository -> import com.example.repository.UserRepository
package com.example.repository;

import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

public class AfterUserRepository {

    private final Map<String, String> store = new HashMap<>();

    public void save(String id, String name) {
        store.put(id, name);
    }

    public Optional<String> findById(String id) {
        return Optional.ofNullable(store.get(id));
    }

    public static void main(String[] args) {
        AfterUserRepository repo = new AfterUserRepository();
        repo.save("1", "Alice");
        System.out.println(repo.findById("1"));
    }
}
