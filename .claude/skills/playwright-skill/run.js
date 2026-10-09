#!/usr/bin/env node
// Universal executor: `node run.js <file.js>` or `node run.js "<inline code>"`.
// Inline code may use top-level await; `chromium`, `firefox`, `webkit`, `helpers` and
// `getContextOptionsWithHeaders` are in scope. File scripts `require('playwright')` normally.
const fs = require('fs');
const path = require('path');
const Module = require('module');

const arg = process.argv[2];
if (!arg) {
  console.error('usage: node run.js <script.js | "inline code">');
  process.exit(2);
}

// Resolve `playwright` from this skill's node_modules even when the script lives in /tmp.
process.env.NODE_PATH = [path.join(__dirname, 'node_modules'), process.env.NODE_PATH].filter(Boolean).join(path.delimiter);
Module._initPaths();

let playwright;
try {
  playwright = require('playwright');
} catch (e) {
  console.error('playwright is not installed; run: cd ' + __dirname + ' && npm run setup');
  process.exit(1);
}
const helpers = require('./lib/helpers');

if (fs.existsSync(arg) && fs.statSync(arg).isFile()) {
  require(path.resolve(arg));
} else {
  const { chromium, firefox, webkit } = playwright;
  const { getContextOptionsWithHeaders } = helpers;
  const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
  new AsyncFunction('chromium', 'firefox', 'webkit', 'helpers', 'getContextOptionsWithHeaders', arg)(
    chromium, firefox, webkit, helpers, getContextOptionsWithHeaders
  ).catch((e) => {
    console.error(e);
    process.exit(1);
  });
}
