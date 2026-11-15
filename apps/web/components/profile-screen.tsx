'use client';
import Link from 'next/link';
import {useSearchParams} from 'next/navigation';
import {sections} from './app-shell';
import {Icon} from './icons';
import {ProfileOverview} from './profile-overview';
import {AccessPanel,AppsPanel,HelpPanel} from './profile-access';
import {ActivityPanel,ModelsPanel,PreferencesPanel,SecurityPanel} from './profile-settings';
export function ProfileScreen(){const params=useSearchParams(),section=params.get('section')||'profile';return <div className="profile-layout"><nav className="profile-nav" aria-label="Profile sections">{sections.map(([id,name,icon])=><Link href={'/profile?section='+id} key={id} className={section===id?'active':''} aria-current={section===id?'page':undefined}><Icon name={icon}/>{name}</Link>)}</nav><div className="profile-content">{section==='profile'?<ProfileOverview tab={params.get('tab')||'overview'}/>:<><div className="section-heading"><h2>{sections.find(s=>s[0]===section)?.[1]||'My Profile'}</h2></div>{section==='access'?<AccessPanel/>:section==='apps'?<AppsPanel/>:section==='models'?<ModelsPanel/>:section==='security'?<SecurityPanel/>:section==='notifications'?<PreferencesPanel notifications/>:section==='activity'?<ActivityPanel/>:section==='preferences'?<PreferencesPanel/>:<HelpPanel/>}</>}</div></div>;}
