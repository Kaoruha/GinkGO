// Test deploy flow: list portfolios -> pick one -> deploy -> verify result
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.connect('http://192.168.50.10:9222');
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // 1. Go to portfolio list
    console.log('1. Loading portfolio list...');
    await page.goto('http://192.168.50.12:5173/portfolios', { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(2000);

    // 2. Find a BACKTEST portfolio to deploy
    const cards = await page.$$('.portfolio-card');
    console.log(`2. Found ${cards.length} portfolio cards`);

    if (cards.length === 0) {
      console.log('ERROR: No portfolios found');
      process.exit(1);
    }

    // Find a BACKTEST mode portfolio (mode === '回测' or mode tag shows '回测')
    let targetCard = null;
    for (const card of cards) {
      const text = await card.textContent();
      if (text.includes('回测') || text.includes('BACKTEST')) {
        targetCard = card;
        break;
      }
    }

    if (!targetCard) {
      // Try first card if no BACKTEST found
      console.log('WARNING: No BACKTEST portfolio found, trying first card');
      targetCard = cards[0];
    }

    // 3. Click the card to go to detail
    console.log('3. Clicking portfolio card...');
    await targetCard.click();
    await page.waitForTimeout(2000);
    console.log(`   Current URL: ${page.url()}`);

    // 4. Check if deploy button exists
    const deployBtn = await page.$('button:has-text("部署")');
    if (deployBtn) {
      console.log('4. Deploy button found, clicking...');
      await deployBtn.click();
      await page.waitForTimeout(1500);

      // 5. Check if deploy modal appeared
      const modal = await page.$('.modal-overlay, .ant-modal');
      if (modal) {
        console.log('5. Deploy modal appeared');

        // Check modal content
        const modalText = await modal.textContent();
        console.log(`   Modal text: ${modalText.substring(0, 200)}`);

        // Look for mode selector
        const paperOption = await page.$('text=模拟盘, .ant-radio, .ant-select');
        if (paperOption) {
          console.log('   Found mode selector');
        }

        // Look for confirm/submit button in modal
        const submitBtn = await page.$('.modal-footer button:last-child, .ant-modal .ant-btn-primary');
        if (submitBtn) {
          const btnText = await submitBtn.textContent();
          console.log(`   Submit button text: ${btnText}`);
        }
      } else {
        console.log('5. No deploy modal appeared');
      }
    } else {
      console.log('4. No deploy button (portfolio might be PAPER/LIVE already)');

      // Check for stop button instead
      const stopBtn = await page.$('button:has-text("停止")');
      if (stopBtn) {
        console.log('   Stop button found (PAPER/LIVE portfolio)');
      }

      // Check header for status
      const statusTag = await page.$('.status-tag');
      if (statusTag) {
        const status = await statusTag.textContent();
        console.log(`   Portfolio status: ${status}`);
      }
    }

    // 6. Take screenshot for verification
    await page.screenshot({ path: '/tmp/deploy-test-screenshot.png', fullPage: false });
    console.log('6. Screenshot saved to /tmp/deploy-test-screenshot.png');

    // 7. Go back to list and check portfolio states
    await page.goto('http://192.168.50.12:5173/portfolios', { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(2000);

    const allCards = await page.$$('.portfolio-card');
    console.log(`\n7. Portfolio list summary (${allCards.length} portfolios):`);
    for (let i = 0; i < Math.min(allCards.length, 5); i++) {
      const text = await allCards[i].textContent();
      // Extract name and mode
      const nameEl = await allCards[i].$('.card-name, .portfolio-name');
      const modeEl = await allCards[i].$('.tag, .ant-tag');
      const name = nameEl ? await nameEl.textContent() : 'unknown';
      const mode = modeEl ? await modeEl.textContent() : 'unknown';
      console.log(`   [${i}] ${name.trim()} - mode: ${mode.trim()}`);
    }

    console.log('\nDONE: Deploy flow inspection complete');

  } catch (e) {
    console.error('ERROR:', e.message);
    await page.screenshot({ path: '/tmp/deploy-test-error.png', fullPage: false });
  } finally {
    await context.close();
    await browser.close();
  }
})();
