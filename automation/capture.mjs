import { chromium } from 'playwright';
import fs from 'node:fs/promises';
const plan=JSON.parse(await fs.readFile('run/plan.json','utf8'));
const browser=await chromium.launch({headless:true});
try {
  const context=await browser.newContext({viewport:{width:390,height:1000},deviceScaleFactor:3,permissions:['clipboard-read','clipboard-write']});
  // Demo production must not be counted as organic visitors.
  await context.route('**://static.cloudflareinsights.com/**',r=>r.abort());
  await context.route('**/cdn-cgi/rum*',r=>r.abort());
  const page=await context.newPage();
  await page.goto('https://pasteguard.pages.dev/#demo',{waitUntil:'networkidle'});
  const input=page.locator('#input'),toggle=page.locator('#demo-toggle');
  await toggle.uncheck(); await input.fill(plan.example.text);
  if(await input.inputValue()!==plan.example.text) throw new Error('Unprotected comparison does not match fixture');
  await input.screenshot({path:'run/before.png'});
  await page.locator('#clear').click(); await toggle.check(); await input.click();
  await input.screenshot({path:'run/empty.png'});
  await page.evaluate(text=>navigator.clipboard.writeText(text),plan.example.text);
  await input.press('Control+v');
  await page.waitForFunction(()=>document.querySelector('#input').value.includes('[REDACTED]'));
  const actual=await input.inputValue();
  if(actual.includes(plan.example.secret)||!actual.includes(plan.example.context)) throw new Error('Demo did not preserve context and redact the fake secret');
  await input.screenshot({path:'run/after.png'});
  await fs.writeFile('run/capture.json',JSON.stringify({date:new Date().toISOString(),source:'Actual website demo, real clipboard paste, fake data. Timing edited; not a latency benchmark.',before:plan.example.text,after:actual,synthetic_analytics_blocked:true},null,2));
} finally { await browser.close(); }
