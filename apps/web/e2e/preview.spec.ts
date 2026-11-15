import {test,expect} from '@playwright/test';
test('capture the current website for review',async({page})=>{
 await page.goto('/profile');await expect(page.getByRole('button',{name:'Edit Profile',exact:true})).toBeVisible();
 await page.screenshot({path:'../../docs/screenshots/profile.png',fullPage:true});
 await page.goto('/customize');await expect(page.getByRole('heading',{name:'Recommended for you',exact:true})).toBeVisible();await expect(page.locator('.tool-card').first()).toBeVisible();await expect(page.locator('.workspace-summary')).not.toContainText('...');
 await page.screenshot({path:'../../docs/screenshots/customize-recommended.png',fullPage:true});
 await page.goto('/login');await expect(page.getByRole('button',{name:'Sign in',exact:true})).toBeVisible();
 await page.screenshot({path:'../../docs/screenshots/login.png',fullPage:true});
});
