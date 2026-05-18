package main

import "fmt"

// HandleRequest handles an incoming request string and returns a response.
func HandleRequest(req string) string {
	return fmt.Sprintf("processed: %s", req)
}

func main() {
	r1 := HandleRequest("hello")
	r2 := HandleRequest("world")
	fmt.Println(r1, r2)
}
