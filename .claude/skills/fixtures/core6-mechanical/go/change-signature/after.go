package main

import (
	"context"
	"fmt"
)

// FetchData retrieves data from the given URL using the provided context.
// context.Context is always the first parameter by Go convention.
func FetchData(ctx context.Context, url string) (string, error) {
	return fmt.Sprintf("data from %s", url), nil
}

func main() {
	ctx := context.Background()
	d1, _ := FetchData(ctx, "https://api.example.com/users")
	d2, _ := FetchData(ctx, "https://api.example.com/posts")
	d3, _ := FetchData(ctx, "https://api.example.com/comments")
	fmt.Println(d1, d2, d3)
}
