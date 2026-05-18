package main

import "fmt"

// ProcessRequest handles an incoming request string and returns a response.
func ProcessRequest(req string) string {
	return fmt.Sprintf("processed: %s", req)
}

func main() {
	r1 := ProcessRequest("hello")
	r2 := ProcessRequest("world")
	fmt.Println(r1, r2)
}
