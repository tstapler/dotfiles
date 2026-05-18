package main

import "strings"

// isValidUsername reports whether a username meets the requirements.
// Used in exactly one place — a candidate for inlining.
func isValidUsername(s string) bool {
	return len(s) >= 3 && !strings.Contains(s, " ")
}

func registerUser(username string) string {
	if !isValidUsername(username) {
		return "invalid username"
	}
	return "registered: " + username
}

func main() {
	println(registerUser("alice"))
	println(registerUser("x"))
}
