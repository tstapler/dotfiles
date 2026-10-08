// Helpers referenced by SKILL.md. Required from scripts run through ../run.js.
const http = require('http');

const COMMON_PORTS = [3000, 3001, 3002, 3003, 4200, 5000, 5173, 8000, 8080, 8543, 8888];

function probe(port, timeoutMs = 400) {
  return new Promise((resolve) => {
    const req = http.get({ host: 'localhost', port, path: '/', timeout: timeoutMs }, (res) => {
      res.resume();
      resolve(`http://localhost:${port}`);
    });
    req.on('timeout', () => req.destroy());
    req.on('error', () => resolve(null));
  });
}

/** Returns the URLs of local HTTP servers answering on common dev ports. */
async function detectDevServers(ports = COMMON_PORTS) {
  const found = await Promise.all(ports.map((p) => probe(p)));
  return found.filter(Boolean);
}

/** Extra request headers from PW_HEADER_NAME/PW_HEADER_VALUE or PW_EXTRA_HEADERS (JSON). */
function getExtraHeaders() {
  if (process.env.PW_EXTRA_HEADERS) {
    try {
      return JSON.parse(process.env.PW_EXTRA_HEADERS);
    } catch (e) {
      console.warn('PW_EXTRA_HEADERS is not valid JSON; ignoring');
    }
  }
  if (process.env.PW_HEADER_NAME && process.env.PW_HEADER_VALUE) {
    return { [process.env.PW_HEADER_NAME]: process.env.PW_HEADER_VALUE };
  }
  return {};
}

function getContextOptionsWithHeaders(options = {}) {
  const extra = getExtraHeaders();
  if (!Object.keys(extra).length) return options;
  return { ...options, extraHTTPHeaders: { ...(options.extraHTTPHeaders || {}), ...extra } };
}

async function createContext(browser, options = {}) {
  return browser.newContext(getContextOptionsWithHeaders(options));
}

async function safeClick(page, selector, { retries = 3, timeout = 5000 } = {}) {
  for (let attempt = 1; ; attempt++) {
    try {
      await page.click(selector, { timeout });
      return;
    } catch (e) {
      if (attempt >= retries) throw e;
    }
  }
}

async function safeType(page, selector, text, options = {}) {
  await page.fill(selector, '');
  await page.type(selector, text, options);
}

async function takeScreenshot(page, name, dir = '/tmp') {
  const file = `${dir}/${name}-${new Date().toISOString().replace(/[:.]/g, '-')}.png`;
  await page.screenshot({ path: file, fullPage: true });
  return file;
}

async function handleCookieBanner(page, timeout = 2000) {
  const selectors = ['button:has-text("Accept all")', 'button:has-text("Accept")', '#onetrust-accept-btn-handler'];
  for (const sel of selectors) {
    try {
      await page.click(sel, { timeout });
      return true;
    } catch (e) {
      // try the next selector
    }
  }
  return false;
}

async function extractTableData(page, selector) {
  return page.$$eval(`${selector} tr`, (rows) =>
    rows.map((r) => Array.from(r.querySelectorAll('th,td')).map((c) => c.textContent.trim()))
  );
}

module.exports = {
  detectDevServers,
  getContextOptionsWithHeaders,
  createContext,
  safeClick,
  safeType,
  takeScreenshot,
  handleCookieBanner,
  extractTableData,
};
