package main

import (
	"errors"
	"fmt"
)

// CreateAccount creates a new user account after validating input.
func CreateAccount(username, email string, age int) (string, error) {
	// Validation block — candidate for extraction
	if username == "" {
		return "", errors.New("username cannot be empty")
	}
	if len(username) < 3 {
		return "", errors.New("username must be at least 3 characters")
	}
	if email == "" {
		return "", errors.New("email cannot be empty")
	}
	if age < 18 {
		return "", errors.New("must be at least 18 years old")
	}

	accountID := fmt.Sprintf("acct_%s", username)
	return accountID, nil
}

func main() {
	id, err := CreateAccount("alice", "alice@example.com", 25)
	if err != nil {
		fmt.Println("Error:", err)
		return
	}
	fmt.Println("Created account:", id)
}
