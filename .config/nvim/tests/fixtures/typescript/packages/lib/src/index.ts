// Tiny fixture module for exercising cross-package go-to-definition and
// the monorepo root_dir resolution (nearest tsconfig.json, not repo top).

export function greet(name: string): string {
  return `Hello, ${name}!`;
}

// A good DAP breakpoint target (stretch TS/JS DAP goal): a loop with a
// local accumulator to set a breakpoint on and inspect mid-loop.
export function total(nums: number[]): number {
  let result = 0;
  for (const n of nums) {
    result += n;
  }
  return result;
}
