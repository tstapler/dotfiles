// Standalone entry point for the pwa-node DAP stretch goal — run/debug this
// file directly (node main.ts, or <leader>dc under nvim-dap). See lib.ts
// for why this fixture is separate from the packages/app+lib monorepo one.

import { greet, total } from "./lib.ts";

const msg = greet("World");
console.log(msg);

const nums = [1, 2, 3, 4, 5];
const result = total(nums);
console.log(`Total: ${result}`);
