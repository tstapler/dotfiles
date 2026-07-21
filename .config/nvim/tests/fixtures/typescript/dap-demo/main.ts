// Standalone entry point for the pwa-node DAP stretch goal — run/debug this
// file directly (node main.ts, or <leader>dc under nvim-dap). See lib.ts
// for why this fixture is separate from the packages/app+lib monorepo one.
//
// MANUAL/INTERACTIVE VERIFICATION ONLY: this fixture is not launched or
// exercised by tests/smoke_test.sh — headless Neovim cannot drive a real
// breakpoint/launch/step DAP session. Use it by hand (open this file,
// set a breakpoint in lib.ts's total() loop, <leader>dc) to verify JS/TS
// DAP; see lang/typescript.lua for the known pwa-node handoff flakiness.

import { greet, total } from "./lib.ts";

const msg = greet("World");
console.log(msg);

const nums = [1, 2, 3, 4, 5];
const result = total(nums);
console.log(`Total: ${result}`);
