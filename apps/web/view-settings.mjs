import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

  console.log('1. 访问登录页...');
  await page.goto('http://localhost:3001/auth/login', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(2000);

  console.log('2. 填写登录信息...');
  const userInput = page.locator('input[placeholder*="创作身份"]');
  const passInput = page.locator('input[placeholder*="8 位"]');

  if (await userInput.count() > 0) {
    await userInput.fill('zhanglu');
    await passInput.fill('12345678');
    await page.locator('button[type="submit"], button:has-text("登")').first().click();
    console.log('3. 等待登录完成...');
    await page.waitForTimeout(3000);
  }

  console.log('4. 访问项目设置页面...');
  await page.goto('http://localhost:3001/workspace/project/d582fe89-9416-4061-8071-022c491defa6/settings', {
    waitUntil: 'domcontentloaded',
    timeout: 60000
  });
  await page.waitForTimeout(3000);

  console.log('5. 截图保存...');
  await page.screenshot({ path: '/tmp/settings-final.png', fullPage: true });
  console.log('截图已保存: /tmp/settings-final.png');

  await browser.close();
})();
