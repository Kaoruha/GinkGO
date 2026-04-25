const { chromium } = require('/home/kaoru/Ginkgo/web-ui/node_modules/playwright');
const assert = require('assert');

const BASE = 'http://192.168.50.12:5173';

(async () => {
  const browser = await chromium.connectOverCDP('http://192.168.50.10:9222');
  const contexts = browser.contexts();
  const page = contexts[0]?.pages()[0];
  if (!page) { console.log('FAIL: No page'); process.exit(1); }

  const logs = [];
  page.on('console', msg => {
    if (msg.type() === 'error') logs.push(`[console.error] ${msg.text()}`);
  });

  const apiCalls = [];
  page.on('request', req => {
    if (req.url().includes('/api/v1/portfolio') && ['POST', 'PUT'].includes(req.method())) {
      apiCalls.push({ method: req.method(), url: req.url(), postData: req.postData() });
    }
  });
  page.on('response', async resp => {
    if (resp.url().includes('/api/v1/portfolio') && resp.request().method() !== 'GET') {
      try { apiCalls.push({ respStatus: resp.status(), body: (await resp.text()).substring(0, 500) }); } catch {}
    }
  });

  console.log('=== Step 1: Navigate to portfolio list ===');
  await page.goto(`${BASE}/portfolios`);
  await page.waitForTimeout(2000);

  console.log('=== Step 2: Click create portfolio button ===');
  const createBtn = await page.$('button.btn-primary');
  if (!createBtn) { console.log('FAIL: No create button'); process.exit(1); }

  // Check if it's the right button
  const btnText = await createBtn.textContent();
  console.log(`  Found button: "${btnText?.trim()}"`);

  // Look for the create portfolio button specifically
  const buttons = await page.$$('button.btn-primary');
  for (const btn of buttons) {
    const text = (await btn.textContent()).trim();
    if (text.includes('创建组合') || text.includes('创建')) {
      await btn.click();
      console.log('  Clicked create button');
      break;
    }
  }
  await page.waitForTimeout(2000);

  console.log('=== Step 3: Check if modal opened ===');
  const currentUrl = page.url();
  console.log(`  Current URL: ${currentUrl}`);

  // Check for the form - it could be modal or new page
  const nameInput = await page.$('[data-testid="input-portfolio-name"]');
  if (!nameInput) {
    // Try looking for any form
    const formTitle = await page.evaluate(() => {
      const h1 = document.querySelector('h1');
      return h1?.textContent;
    });
    console.log(`  Page title: ${formTitle}`);

    // Maybe we need to navigate to create page
    if (!currentUrl.includes('create') && !currentUrl.includes('edit')) {
      // Try clicking create in the list page
      const links = await page.$$('a');
      for (const link of links) {
        const href = await link.getAttribute('href');
        if (href?.includes('create') || href?.includes('edit')) {
          await link.click();
          await page.waitForTimeout(2000);
          break;
        }
      }
    }
  }

  // Fill form
  const nameField = await page.$('[data-testid="input-portfolio-name"]') ||
                    await page.$('input[placeholder="组合名称"]');
  if (!nameField) {
    console.log('FAIL: Cannot find portfolio name input');
    console.log('Page content:', await page.evaluate(() => document.body.innerText.substring(0, 500)));
    process.exit(1);
  }

  const testName = `e2e_test_${Date.now()}`;
  await nameField.fill(testName);
  console.log(`  Filled name: ${testName}`);

  console.log('=== Step 4: Add strategy component ===');
  // Click strategy tab
  const strategyTab = await page.$('button.type-btn:nth-child(3)') ||
                       await page.evaluateHandle(() => {
    const btns = document.querySelectorAll('.type-btn');
    for (const b of btns) { if (b.textContent.includes('策略')) return b; }
    return null;
  });
  if (strategyTab) {
    await strategyTab.click();
    console.log('  Clicked strategy tab');
    await page.waitForTimeout(1000);
  }

  // Search and select random_signal_strategy
  const searchInput = await page.$('.component-selector input[type="text"], .component-selector input');
  if (searchInput) {
    await searchInput.fill('random_signal');
    console.log('  Searched for random_signal');
    await page.waitForTimeout(2000);

    // Click search result
    const options = await page.$$('.search-option, .dropdown-item, [class*="option"]');
    console.log(`  Found ${options.length} options`);
    for (const opt of options) {
      const text = await opt.textContent();
      if (text?.includes('random_signal')) {
        await opt.click();
        console.log(`  Selected: ${text.trim()}`);
        break;
      }
    }
    await page.waitForTimeout(2000);
  }

  console.log('=== Step 5: Fill code parameter ===');
  // Find code input in strategy config
  const codeInput = await page.evaluateHandle(() => {
    const params = document.querySelectorAll('.param-row');
    for (const row of params) {
      const label = row.querySelector('.param-label');
      if (label?.textContent?.trim() === 'code') {
        return row.querySelector('.param-input');
      }
    }
    return null;
  });

  const codeInputExists = await page.evaluate(el => el !== null, codeInput);
  if (codeInputExists) {
    await codeInput.fill('000001.SZ');
    console.log('  Filled code: 000001.SZ');
  } else {
    console.log('  WARNING: No code parameter found, listing params...');
    const paramNames = await page.evaluate(() => {
      const labels = document.querySelectorAll('.param-label');
      return Array.from(labels).map(l => l.textContent?.trim());
    });
    console.log(`  Available params: ${JSON.stringify(paramNames)}`);
  }

  console.log('=== Step 6: Save portfolio ===');
  const saveBtn = await page.$('[data-testid="btn-save-portfolio"]') ||
                  await page.evaluateHandle(() => {
    const btns = document.querySelectorAll('button');
    for (const b of btns) {
      if (b.textContent?.includes('创建')) return b;
    }
    return null;
  });
  if (saveBtn) {
    await saveBtn.click();
    console.log('  Clicked save');
    await page.waitForTimeout(3000);
  }

  console.log('=== Step 7: Check API calls ===');
  console.log('API calls:', JSON.stringify(apiCalls, null, 2));

  // Get the created portfolio UUID from URL or API response
  const newUrl = page.url();
  console.log(`  Current URL: ${newUrl}`);

  // Extract portfolio UUID
  const uuidMatch = newUrl.match(/portfolios\/([a-f0-9]+)/);
  if (!uuidMatch) {
    console.log('FAIL: Could not find portfolio UUID in URL');
    console.log('Console errors:', logs);
    process.exit(1);
  }
  const portfolioUuid = uuidMatch[1];
  console.log(`  Portfolio UUID: ${portfolioUuid}`);

  console.log('=== Step 8: Navigate to components tab ===');
  await page.goto(`${BASE}/portfolios/${portfolioUuid}/components`);
  await page.waitForTimeout(3000);

  const componentsContent = await page.evaluate(() => {
    const tab = document.querySelector('.components-tab');
    return tab ? tab.innerText : 'no components-tab';
  });
  console.log('Components content:');
  console.log(componentsContent);

  console.log('=== Step 9: Verify code parameter ===');
  const hasStrategy = componentsContent.includes('random_signal_strategy');
  const hasCode = componentsContent.includes('000001.SZ');

  console.log(`  Has strategy: ${hasStrategy}`);
  console.log(`  Has code "000001.SZ": ${hasCode}`);

  // Also check via API directly
  const apiCheck = await page.evaluate(async (uuid) => {
    const res = await fetch(`/api/v1/portfolios/${uuid}`);
    const data = await res.json();
    return data.data?.strategies || [];
  }, portfolioUuid);
  console.log(`  API strategies: ${JSON.stringify(apiCheck, null, 2)}`);

  if (hasStrategy) {
    console.log('\n✅ PASS: Strategy is displayed');
  } else {
    console.log('\n❌ FAIL: Strategy not displayed');
  }

  if (hasCode) {
    console.log('✅ PASS: Code parameter "000001.SZ" is saved');
  } else {
    console.log('❌ FAIL: Code parameter "000001.SZ" is NOT saved');
    // Show what config IS saved
    const strategyConfig = apiCheck.find(s => s.name?.includes('random'));
    if (strategyConfig) {
      console.log(`  Saved config: ${JSON.stringify(strategyConfig.config)}`);
    }
  }

  console.log('\nConsole errors:', logs.length > 0 ? logs.join('\n') : 'none');

  await browser.close();
})();
