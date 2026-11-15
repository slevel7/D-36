import {test,expect} from '@playwright/test';
test.describe.configure({mode:'serial'});
async function ready(page:import('@playwright/test').Page,path='/'){
 await page.goto(path);await expect(page.getByRole('combobox',{name:'Active department and division'})).toBeVisible();
}
test('shell hierarchy, lotus, account navigation and profile persistence',async({page})=>{
 await ready(page);await expect(page.getByRole('heading',{name:'How can Brahma help?'})).toBeVisible();
 const navigation=page.getByRole('navigation',{name:'Workspaces'});
 await expect(navigation.getByRole('link')).toHaveText(['Projects','Department Work','Documents','Customize','My Tasks']);
 await expect(page.getByRole('img',{name:'Brahma lotus'}).first()).toBeVisible();
 await page.screenshot({path:'../../docs/screenshots/home.png',fullPage:true});
 await page.getByRole('button',{name:'Open profile menu'}).hover();
 await page.getByRole('navigation',{name:'Account'}).getByRole('link',{name:'My Profile',exact:true}).click();
 await expect(page.getByRole('button',{name:'Edit Profile',exact:true})).toBeVisible();
 await page.screenshot({path:'../../docs/screenshots/profile.png',fullPage:true});
 await page.getByRole('button',{name:'Edit Profile',exact:true}).click();
 await page.getByRole('textbox',{name:'Display name',exact:true}).fill('Demo recovery colleague');
 await page.getByRole('button',{name:'Save changes',exact:true}).click();
 await expect(page.getByRole('dialog')).toHaveCount(0);
 await page.reload();await expect(page.getByRole('heading',{name:'Demo recovery colleague',exact:false})).toBeVisible();
 const sections=page.getByRole('navigation',{name:'Profile sections'});
 await expect(sections.getByRole('link')).toHaveCount(9);
 for(const [name,file] of [['Setup & Department Access','profile-access'],['Connected Apps','profile-apps'],['AI & Models','profile-models'],['Security & Permissions','profile-security'],['Notifications','profile-notifications'],['Activity & Usage','profile-activity'],['Preferences','profile-preferences'],['Help & Support','profile-help']]){
  await sections.getByRole('link',{name,exact:true}).click();
  await expect(page.locator('.profile-content').getByRole('heading',{name,exact:true}).first()).toBeVisible();
  await expect(page.getByText('Loading your workspace...', {exact:true})).toHaveCount(0);
  await page.screenshot({path:'../../docs/screenshots/'+file+'.png',fullPage:true});
 }
 await sections.getByRole('link',{name:'Preferences',exact:true}).click();
 await page.getByLabel('Text size',{exact:true}).selectOption('large');
 await page.getByRole('button',{name:'Save preferences',exact:true}).click();
 await expect(page.getByRole('status')).toContainText('Preferences saved');
 await page.reload();await expect(page.getByLabel('Text size',{exact:true})).toHaveValue('large');
 await page.getByLabel('Text size',{exact:true}).selectOption('standard');await page.getByRole('button',{name:'Save preferences',exact:true}).click();
});
test('customize favourites, reordering, requests and distinct connected state',async({page})=>{
 const requestName='DEMO recovery checklist '+Date.now();
 await ready(page,'/customize?tab=all');
 await expect(page.getByRole('heading',{name:'Document workspace',exact:true})).toBeVisible();
 await page.screenshot({path:'../../docs/screenshots/customize-all.png',fullPage:true});
 const docs=page.locator('.tool-card').filter({has:page.getByRole('heading',{name:'Document workspace',exact:true})});
 const star=docs.getByRole('button',{name:/Favourite Document workspace|Remove Document workspace/});
 if((await star.getAttribute('aria-pressed'))==='true')await star.click();
 await expect(docs.getByRole('button',{name:'Favourite Document workspace',exact:true})).toBeVisible();
 await docs.getByRole('button',{name:'Favourite Document workspace',exact:true}).click();
 await expect(page.getByRole('status')).toContainText('Added to favourites');
 await page.getByRole('navigation',{name:'Customize sections'}).getByRole('link',{name:'Favourites',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Document workspace',exact:true})).toBeVisible();
 await page.reload();await expect(page.getByRole('heading',{name:'Document workspace',exact:true})).toBeVisible();
 await page.getByRole('navigation',{name:'Customize sections'}).getByRole('link',{name:'Connected Tools',exact:true}).click();
 await expect(page.getByRole('heading',{name:'No connected tools',exact:true})).toBeVisible();
 await page.getByRole('navigation',{name:'Customize sections'}).getByRole('link',{name:'Recommended',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Recommended for you'})).toBeVisible();
 await page.screenshot({path:'../../docs/screenshots/customize-recommended.png',fullPage:true});
 await page.getByRole('button',{name:'Request a New Tool',exact:true}).click();
 await page.getByRole('textbox',{name:'Tool name',exact:true}).fill(requestName);
 await page.getByRole('textbox',{name:'What do you need it for?',exact:true}).fill('A fictional checklist for the browser recovery scenario.');
 await page.getByRole('button',{name:'Submit tool request',exact:true}).click();
 await expect(page.getByRole('dialog')).toHaveCount(0);
 await expect(page.getByText(requestName,{exact:true})).toBeVisible();
});
test('mobile drawer and profile deep link survive reload without overflow',async({page})=>{
 await page.setViewportSize({width:390,height:844});await ready(page,'/profile?section=profile');
 await page.getByRole('button',{name:'Open navigation',exact:true}).click();
 await expect(page.getByRole('navigation',{name:'Workspaces'})).toBeVisible();
 await page.getByRole('navigation',{name:'Workspaces'}).getByRole('link',{name:'Customize',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Recommended for you'})).toBeVisible();
 await expect(page.locator('.sidebar')).not.toHaveClass(/is-open/);
 await page.screenshot({path:'../../docs/screenshots/mobile.png',fullPage:true});
 expect(await page.locator('body').evaluate(element=>element.scrollWidth<=window.innerWidth)).toBe(true);
 await page.goto('/profile?section=apps');await page.reload();
 await expect(page.locator('.profile-content').getByRole('heading',{name:'Connected Apps',exact:true})).toBeVisible();
});
