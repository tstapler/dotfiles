const { chromium } = require('playwright');

const TARGET_URL = 'https://incidents.cicd.fanatics.bet/incidents/kr-metrics?start_date=2026-01-13&severity=P1+%28SEV-1%29&group_by=domain&end_date=2026-04-14';

(async () => {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext({ viewport: { width: 1600, height: 900 } });
  const page = await context.newPage();

  const consoleErrors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('pageerror', err => consoleErrors.push(`PAGE ERROR: ${err.message}`));

  console.log('Navigating to KR metrics dashboard...');
  await page.goto(TARGET_URL, { waitUntil: 'networkidle', timeout: 60000 });

  // Wait for Streamlit to fully render
  await page.waitForTimeout(5000);

  console.log('Taking full-page screenshot...');
  await page.screenshot({ path: '/tmp/kr-metrics-full.png', fullPage: true });
  console.log('📸 Full page saved: /tmp/kr-metrics-full.png');

  // Scroll to top and take viewport screenshot
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(500);
  await page.screenshot({ path: '/tmp/kr-metrics-top.png' });
  console.log('📸 Top section saved: /tmp/kr-metrics-top.png');

  // Scroll down to find availability section
  await page.evaluate(() => window.scrollTo(0, 800));
  await page.waitForTimeout(500);
  await page.screenshot({ path: '/tmp/kr-metrics-mid1.png' });
  console.log('📸 Mid section 1 saved: /tmp/kr-metrics-mid1.png');

  await page.evaluate(() => window.scrollTo(0, 1600));
  await page.waitForTimeout(500);
  await page.screenshot({ path: '/tmp/kr-metrics-mid2.png' });
  console.log('📸 Mid section 2 saved: /tmp/kr-metrics-mid2.png');

  await page.evaluate(() => window.scrollTo(0, 2400));
  await page.waitForTimeout(500);
  await page.screenshot({ path: '/tmp/kr-metrics-mid3.png' });
  console.log('📸 Mid section 3 saved: /tmp/kr-metrics-mid3.png');

  await page.evaluate(() => window.scrollTo(0, 3200));
  await page.waitForTimeout(500);
  await page.screenshot({ path: '/tmp/kr-metrics-mid4.png' });
  console.log('📸 Mid section 4 saved: /tmp/kr-metrics-mid4.png');

  await page.evaluate(() => window.scrollTo(0, 4000));
  await page.waitForTimeout(500);
  await page.screenshot({ path: '/tmp/kr-metrics-bottom.png' });
  console.log('📸 Bottom section saved: /tmp/kr-metrics-bottom.png');

  // Extract visible text to understand what's on page
  const pageText = await page.evaluate(() => document.body.innerText);
  const lines = pageText.split('\n').filter(l => l.trim().length > 0).slice(0, 100);
  console.log('\n=== PAGE TEXT (first 100 lines) ===');
  lines.forEach(l => console.log(l));

  // Report console errors
  if (consoleErrors.length > 0) {
    console.log('\n=== CONSOLE ERRORS ===');
    consoleErrors.forEach(e => console.log('ERROR:', e));
  } else {
    console.log('\n✅ No console errors detected');
  }

  await browser.close();
})();
