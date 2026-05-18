package main

import "fmt"

// FetchData retrieves data from the given URL.
func FetchData(url string) (string, error) {
	return fmt.Sprintf("data from %s", url), nil
}

func main() {
	d1, _ := FetchData("https://api.example.com/users")
	d2, _ := FetchData("https://api.example.com/posts")
	d3, _ := FetchData("https://api.example.com/comments")
	fmt.Println(d1, d2, d3)
}
