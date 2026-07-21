// Command app is a tiny fixture program: imports lib across a go.work
// module boundary so `gd` on lib.Greet/lib.Sum jumps into ../lib, and its
// Sum() call is a good spot to set a DAP breakpoint via <leader>db.
package main

import (
	"fmt"

	"nvim-fixture.test/lib"
)

func main() {
	msg := lib.Greet("World")
	fmt.Println(msg)

	nums := []int{1, 2, 3, 4, 5}
	total := lib.Sum(nums)
	fmt.Println("Total:", total)
}
