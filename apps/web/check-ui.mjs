import { chromium } from 'playwright';

import { copyFileSync } from 'fs';
import { join } from 'path';

async function main() {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });

  const errors = [];
  const warnings = [];

  page.on('console', msg => {
    if (msg.type() === 'error') errors.push(`[Console] ${msg.text()}`);
    if (msg.type() === 'warning') warnings.push(`[Console] ${msg.text()}`);
  });

  page.on('pageerror', err => errors.push(`[Page] ${err.message}`);

  console.log('=== Playwright UI 检查 ===\n');

  // 1. 首页
  console.log('1. 检查首页...');
  await page.goto('http://localhost:3003', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: 'screenshot-home.png' });
  console.log('   ✓ screenshot-home.png');

  // 2. 工作区
  console.log('\n2. 检查工作区...');
  await page.goto('http://localhost:3003/workspace', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: 'screenshot-workspace.png' });
  console.log('   ✓ screenshot-workspace.png');

  // 3. Studio 页面
  console.log('\n3. 检查 Studio 页面...');
  await page.goto('http://localhost:3003/workspace/project/cm8h2p4d10000vbdp4c1d4k0e/studio', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2500);

  console.log('   页面标题:', await page.title());
  console.log('   页面容器:', await page.$('[class*="page"]') ? '✓' : '✗');
  console.log('   侧边栏:', await page.$('[class*="sidebar"]') ? '✓' : '✗');
    console.log('   内容区:', await page.$('[class*="content"]') ? '✓' : '✗');
  console.log('   聊天面板:', await page.$('[class*="chat"]') ? '✓' : '✗');

  await page.screenshot({ path: 'screenshot-studio.png' });
    console.log('   ✓ screenshot-studio.png');

  // 4. 测试模型选择器
  console.log('\n4. 测试模型选择器...');
  const buttons = await page.$$('button');
  for (const btn of buttons) {
    const text = await btn.textContent();
    if (text && text.includes('模型')) {
      console.log('   找到按钮:', text.trim());
      await btn.click();
      await page.waitForTimeout(500);
      const picker = await page.$('[class*="modelPicker"]');
      if (picker) {
        const box = await picker.boundingBox();
        if (box) {
          console.log('   选择器位置: top=' + Math.round(box.y) + ', height=' + Math.round(box.height));
          if (box.y < 0) {
            errors.push('模型选择器被遮挡在屏幕上方');
          } else {
            console.log('   ✓ 选择器位置正常，未被遮挡');
          }
        }
        await page.screenshot({ path: 'screenshot-model-picker.png' });
        console.log('   ✓ screenshot-model-picker.png');
      } else {
        errors.push('模型选择器未出现');
      }
      break;
    }
  }

  // 5. 测试上下文选择器
  console.log('\n5. 测试上下文选择器...');
  for (const btn of buttons) {
    const text = await btn.textContent();
    if (text && text.includes('上下文')) {
      console.log('   找到按钮:', text.trim());
      await btn.click();
      await page.waitForTimeout(500);
      const selector = await page.$('[class*="contextSelector"]');
      if (selector) {
        const searchInput = await selector.$('input');
        console.log('   搜索框:', searchInput ? '✓' : '✗');
        const groups = await selector.$$('[class*="contextGroup"]');
        console.log('   分组数:', groups.length);
        await page.screenshot({ path: 'screenshot-context-selector.png' });
        console.log('   ✓ screenshot-context-selector.png');
      } else {
        errors.push('上下文选择器未出现');
      }
      break;
    }
  }

  // 6. 测试文档树
  console.log('\n6. 测试文档树...');
  const treeNodes = await page.$$('[class*="treeNode"]');
  console.log('   文档节点数:', treeNodes.length);

  // 7. 测试编辑器
  console.log('\n7. 测试编辑器...');
  const textarea = await page.$('textarea');
  if (textarea) {
    console.log('   ✓ 编辑器存在');
    const placeholder = await textarea.getAttribute('placeholder');
    console.log('   占位符:', placeholder);
  } else {
    errors.push('编辑器未找到');
  }

  // 错误汇总
  console.log('\n=== 错误汇总 ===');
  if (errors.length === 0) {
    console.log('✓ 无错误');
  } else {
    errors.forEach(e => console.log('✗', e));
  }

  // 警告汇总
  console.log('\n=== 警告汇总 ===');
  if (warnings.length === 0) {
    console.log('✓ 无警告');
  } else {
    warnings.forEach(w => console.log('⚠', w.substring(0, 100)));
  }

  // 复制截图到项目根目录
  const webDir = '/home/zl/code/easyStory/apps/web';
  const rootDir = '/home/zl/code/easyStory';
  copyFileSync(join(webDir, 'screenshot-home.png'), join(rootDir, 'screenshot-home.png'));
  copyFileSync(join(webDir, 'screenshot-workspace.png'), join(rootDir, 'screenshot-workspace.png'));
  copyFileSync(join(webDir, 'screenshot-studio.png'), join(rootDir, 'screenshot-studio.png'));
  copyFileSync(join(webDir, 'screenshot-model-picker.png'), join(rootDir, 'screenshot-model-picker.png'));
  copyFileSync(join(webDir, 'screenshot-context-selector.png'), join(rootDir, 'screenshot-context-selector.png'));

  console.log('\n截图已复制到项目根目录');

  await browser.close();
  console.log('\n=== 检查完成 ===');
}

main().catch(console.error);
