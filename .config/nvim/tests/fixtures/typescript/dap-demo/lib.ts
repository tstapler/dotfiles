// Standalone DAP-testable fixture — deliberately NOT part of the
// packages/app+packages/lib monorepo fixture next to this one. That
// fixture's cross-package `@fixture/lib` import is resolved via tsconfig
// `paths` mapping, which TypeScript's compiler understands but Node's own
// runtime module resolver does not — pwa-node debugs a real `node`
// process, so it needs an import Node can actually resolve on its own
// (relative path, explicit .ts extension — Node 22.18+/23+ strips
// TypeScript types natively, no ts-node/tsx required, but still uses
// plain ESM resolution rules).

export function greet(name: string): string {
  return `Hello, ${name}!`;
}

// A good DAP breakpoint target: a loop with a local accumulator to set a
// breakpoint on and inspect mid-loop.
export function total(nums: number[]): number {
  let result = 0;
  for (const n of nums) {
    result += n;
  }
  return result;
}
