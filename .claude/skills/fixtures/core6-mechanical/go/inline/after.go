package main

import "strings"

func registerUser(username string) string {
	if !(len(username) >= 3 && !strings.Contains(username, " ")) {
		return "invalid username"
	}
	return "registered: " + username
}

func main() {
	println(registerUser("alice"))
	println(registerUser("x"))
}
