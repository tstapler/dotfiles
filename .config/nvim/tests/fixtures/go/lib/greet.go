// Package lib is a tiny fixture package for exercising cross-module
// go-to-definition/references and DAP breakpoints under nvim-next's go.work.
package lib

import "fmt"

// Greet returns a greeting for name — a cross-module gd/grr target.
func Greet(name string) string {
	return fmt.Sprintf("Hello, %s!", name)
}

// Sum adds up nums — a good DAP breakpoint target: a loop with a local
// accumulator to set a breakpoint on and inspect mid-loop.
func Sum(nums []int) int {
	total := 0
	for _, n := range nums {
		total += n
	}
	return total
}
