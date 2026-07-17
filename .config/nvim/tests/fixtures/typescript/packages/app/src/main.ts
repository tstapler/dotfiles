// Tiny fixture entry point: imports @fixture/lib across a package boundary
// (nested tsconfig.json, path-mapped) so `gd`/`grr` exercise cross-package
// navigation and vtsls's monorepo root_dir resolution.

import { greet, total } from "@fixture/lib";

const msg = greet("World");
console.log(msg);

const nums = [1, 2, 3, 4, 5];
const result = total(nums);
console.log(`Total: ${result}`);
