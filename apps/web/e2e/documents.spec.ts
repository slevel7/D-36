import {test,expect} from '@playwright/test';
import path from 'node:path';
test('uploaded originals, exact citations, revisions, human return and approval',async({page,browser})=>{
 test.setTimeout(90000);
 const password=process.env.E2E_PASSWORD;
 test.skip(!password,'Set E2E_PASSWORD to the local seeded demo password for separate-reviewer testing');
 await page.goto('/documents');await expect(page.getByRole('heading',{name:'Document Library',exact:true})).toBeVisible();
 for(const filename of ['demo-circular.pdf','demo-correspondence.docx']){
  await page.getByLabel('Upload source',{exact:true}).setInputFiles(path.join(__dirname,'fixtures',filename));
  await expect(page.getByRole('status')).toContainText('Source uploaded');
 }
 await page.getByRole('button',{name:'Draft with sources',exact:true}).click();
 await page.getByRole('textbox',{name:'Document title',exact:true}).fill('DEMO browser office note '+Date.now());
 await page.getByRole('dialog').getByText('demo-circular.pdf',{exact:true}).last().click();
 await page.getByRole('dialog').getByText('demo-correspondence.docx',{exact:true}).last().click();
 await page.getByRole('button',{name:'Generate DEMO draft',exact:true}).click();
 await expect(page.getByRole('button',{name:'Submit for Review',exact:true})).toBeVisible();
 await expect(page.locator('.citation-chip')).toHaveCount(2);
 await page.getByRole('button',{name:'Source [1]',exact:true}).click();
 await expect(page.getByRole('dialog').locator('mark')).toContainText('Supporting records');
 await expect(page.getByRole('dialog').locator('iframe')).toHaveAttribute('src',/#page=1$/);
 await page.screenshot({path:'../../docs/screenshots/document-citations.png',fullPage:true});
 await page.getByRole('button',{name:'Close dialog',exact:true}).click();
 await page.getByRole('button',{name:'Accept',exact:true}).first().click();
 await expect(page.getByRole('status')).toContainText('Suggestion accepted');
 const editor=page.getByRole('textbox',{name:'Document content',exact:true});
 await editor.fill((await editor.inputValue())+'\nRecommendation: maintain a human follow-up list.');
 await page.getByRole('button',{name:'Save new version',exact:true}).click();
 await expect(page.getByRole('status')).toContainText('New immutable version saved');
 await page.getByRole('button',{name:'Compare versions',exact:true}).click();
 await expect(page.getByRole('dialog').locator('pre')).toContainText('human follow-up list');
 await page.getByRole('button',{name:'Close dialog',exact:true}).click();
 const documentUrl=page.url();
 async function submit(){await page.getByRole('button',{name:'Submit for Review',exact:true}).click();await page.getByRole('dialog').getByRole('combobox',{name:'Designated reviewer',exact:true}).selectOption('reviewer@example.test');await page.getByRole('button',{name:'Confirm submission',exact:true}).click();await expect(page.getByRole('status')).toContainText('reviewer notified');}
 await submit();
 const context=await browser.newContext();
 const auth=await context.request.post('http://localhost:3000/api/auth/login',{data:{email:'reviewer@example.test',password}});
 expect(auth.status()).toBe(200);
 const reviewPage=await context.newPage();await reviewPage.goto('/approvals');
 await expect(reviewPage.getByRole('heading',{name:'Human Review Queue',exact:true})).toBeVisible();
 const title=await page.locator('.section-heading h2').first().innerText();
 const row=reviewPage.locator('.list-row').filter({has:reviewPage.getByText(title,{exact:true})}).last();
 await row.getByRole('button',{name:'Review version',exact:true}).click();
 await reviewPage.getByRole('textbox',{name:'Review comment',exact:true}).fill('Please refine the proposed follow-up wording.');
 await reviewPage.getByRole('button',{name:'Confirm human decision',exact:true}).click();
 await expect(reviewPage.getByRole('status')).toContainText('Review decision recorded');
 await page.goto(documentUrl);await expect(editor).toBeVisible();
 await editor.fill((await editor.inputValue())+'\nRecommendation: follow up only after a human review.');await page.getByRole('button',{name:'Save new version',exact:true}).click();await expect(page.getByRole('status')).toContainText('New immutable version saved');await submit();
 await reviewPage.reload();
 const next=reviewPage.locator('.list-row').filter({has:reviewPage.getByText(title,{exact:true})}).filter({has:reviewPage.getByText('UNDER REVIEW',{exact:true})}).last();
 await next.getByRole('button',{name:'Review version',exact:true}).click();
 await reviewPage.getByRole('dialog').getByRole('combobox',{name:'Decision',exact:true}).selectOption('APPROVED');
 await reviewPage.getByRole('textbox',{name:'Review comment',exact:true}).fill('Reviewed the fictional source excerpts and recommendations.');
 await reviewPage.getByRole('button',{name:'Confirm human decision',exact:true}).click();await expect(reviewPage.getByRole('status')).toContainText('Review decision recorded');
 await reviewPage.screenshot({path:'../../docs/screenshots/approvals.png',fullPage:true});
 for(const format of ['docx','pdf']){const download=page.waitForEvent('download');await page.getByRole('combobox',{name:'Export document',exact:true}).selectOption(format);expect((await download).suggestedFilename()).toBe('review-copy.'+format);}
 await context.close();
});
