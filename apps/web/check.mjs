import { chromium } from 'playwright';

async function main() {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });

  // 登录
  await page.goto('http://localhost:3001/auth/login', { waitUntil: 'load' });
  await page.waitForTimeout(1500);

  const userInput = page.locator('input[placeholder*="创作身份"]');
  const passInput = page.locator('input[placeholder*="8 位"]');

  if (await userInput.count() > 0) {
    await userInput.fill('zhanglu');
    await passInput.fill('12345678');
    await page.locator('button').first().click();
    await page.waitForTimeout(2000);
  }

  // 进入设置页面
  await page.goto('http://localhost:3001/workspace/project/d582fe89-9416-4061-8071-022c491defa6/settings', { waitUntil: 'load' });
  await page.waitForTimeout(3000);

  console.log('URL:', page.url());
  await page.screenshot({ path: 'screenshot-settings.png', fullPage: true });
  console.log('截图已保存: screenshot-settings.png');

  // 获取页面结构
  const headings = await page.locator('h1, h2, h3').allTextContents();
  console.log('\n标题:', headings);

  const forms = await page.locator('form').count();
  console.log('表单数:', forms);

  const inputs = await page.locator('input, textarea, select').count();
  console.log('输入框数:', inputs);

  const buttons = await page.locator('button').allTextContents();
  console.log('按钮:', buttons);

  await browser.close();
}

main().catch(console.error);
