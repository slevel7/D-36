'use client';
import Link from 'next/link';
import {usePathname,useRouter} from 'next/navigation';
import {ReactNode,useEffect,useState} from 'react';
import {api,Conversation,Notice} from '../lib/api';
import {useSession} from './session-provider';
import {Brand,Icon,Lotus} from './icons';
import {Modal} from './ui';
export const sections=[['profile','My Profile','user'],['access','Setup & Department Access','department'],['apps','Connected Apps','apps'],['models','AI & Models','models'],['security','Security & Permissions','security'],['notifications','Notifications','bell'],['activity','Activity & Usage','activity'],['preferences','Preferences','preferences'],['help','Help & Support','help']];
const navigation=[['/projects','Projects','projects'],['/department','Department Work','department'],['/documents','Documents','documents'],['/customize','Customize','customize'],['/tasks','My Tasks','tasks']];
export function AppShell({children}:{children:ReactNode}){
 const {data,loading,error,refresh,signOut}=useSession();const path=usePathname(),router=useRouter();
 const [drawer,setDrawer]=useState(false),[account,setAccount]=useState(false),[bell,setBell]=useState(false),[notices,setNotices]=useState<Notice[]>([]),[recent,setRecent]=useState<Conversation[]>([]),[actionError,setActionError]=useState(''),[focus,setFocus]=useState(false);
 const login=path==='/login',legacy=path==='/legacy';
 useEffect(()=>{if(!loading&&!data&&!login&&!error)router.replace('/login');},[loading,data,login,error,router]);
 useEffect(()=>{setDrawer(false);setAccount(false);setBell(false);},[path]);
 useEffect(()=>{if(data)api<Conversation[]>('/workspace/conversations').then(setRecent).catch(()=>{});},[data,path]);
 useEffect(()=>{const escape=(event:KeyboardEvent)=>{if(event.key==='Escape'){setDrawer(false);setAccount(false);setBell(false);}};document.addEventListener('keydown',escape);return()=>document.removeEventListener('keydown',escape);},[]);
 async function act(fn:()=>Promise<void>){setActionError('');try{await fn();}catch(e){setActionError((e as Error).message);}}
 if(login||legacy)return children;
 if(loading)return <main className="session-loading" role="status"><Lotus/><p>Opening your workspace...</p></main>;
 if(error)return <main className="session-loading"><h1>Workspace unavailable</h1><p role="alert">{error}</p><button onClick={()=>window.location.reload()}>Try again</button></main>;
 if(!data)return null;
 const titles:Record<string,string>={'/':'Brahma','/profile':'My Profile','/customize':'Customize','/projects':'Projects','/department':'Department Work','/documents':'Documents','/tasks':'My Tasks','/search':'Search','/approvals':'Approvals','/admin':'Administration','/notifications':'Notifications'};
 const heading=titles[path]||(path.startsWith('/department/pension')?'Pension':path.startsWith('/department/outreach')?'Outreach Agent':path.startsWith('/department/grievances')?'Public Grievances':path.startsWith('/chat/')?'Brahma':path.startsWith('/projects/')?'Projects':path.startsWith('/tasks/')?'My Tasks':path.startsWith('/documents/')?'Documents':'Department Work');
 const profile=path==='/profile',customize=path==='/customize';
 return <div className={'app-shell'+(focus?' focus-mode':'')}>
  {drawer&&<button className="drawer-overlay" aria-label="Close navigation" onClick={()=>setDrawer(false)}/>}
  <aside className={'sidebar'+(drawer?' is-open':'')} aria-label="Main navigation">
   <Brand/><button className="mobile-close icon-button" aria-label="Close navigation" onClick={()=>setDrawer(false)}><Icon name="close"/></button>
   <Link className="new-chat" href="/"><Icon name="edit"/>New Chat</Link><Link className="side-link" href="/search?type=chats"><Icon name="search"/>Search Chats</Link>
   <span className="nav-caption">WORKSPACE</span>
   <nav aria-label="Workspaces">{navigation.map(([href,name,icon])=><Link className={'side-link'+(path.startsWith(href)?' active':'')} aria-current={path.startsWith(href)?'page':undefined} key={href} href={href}><Icon name={icon}/>{name}</Link>)}</nav>
   <span className="nav-caption">RECENT</span><div className="recent-chats">{recent.slice(0,8).map(chat=><Link key={chat.id} href={'/chat/'+chat.id}><span className="recent-dot"/>{chat.title}</Link>)}{!recent.length&&<small>Your conversations will appear here.</small>}</div>
   <div className="avatar-area" onMouseEnter={()=>setAccount(true)} onMouseLeave={()=>setAccount(false)} onBlur={e=>{if(!e.currentTarget.contains(e.relatedTarget as Node))setAccount(false);}}>
    <button className="avatar-button" aria-label="Open profile menu" aria-expanded={account} aria-controls="avatar-menu" onClick={()=>setAccount(!account)}><Icon name="user" size={23}/></button>
    {account&&<nav id="avatar-menu" className="avatar-popover" aria-label="Account">{sections.map(([id,name,icon])=><Link key={id} href={'/profile?section='+id} onClick={()=>setAccount(false)}><Icon name={icon}/>{name}</Link>)}{data.user.role==='platform_admin'&&<Link href="/admin"><Icon name="security"/>Administration</Link>}<button onClick={()=>act(signOut)}>Sign out</button></nav>}
   </div>
  </aside>
  <div className="main-column"><header className="topbar"><div className="page-heading"><button className="mobile-menu icon-button" aria-label="Open navigation" onClick={()=>setDrawer(true)}><Icon name="menu"/></button><div><h1>{heading}</h1><p>{profile?'Manage your account, access, integrations, AI and workspace preferences':customize?'Discover, organise and personalise your tools and workspace':data.user.department+' - internal demo workspace'}</p></div></div>
   <div className="topbar-actions"><label className="department-control"><span className="sr-only">Active department and division</span><select aria-label="Active department and division" value={data.memberships.find(m=>m.department===data.user.department&&m.division===data.user.division)?.id||''} onChange={e=>act(async()=>{await api('/workspace/switch','POST',{membership_id:e.target.value});await refresh();router.refresh();})}>{data.memberships.map(m=><option key={m.id} value={m.id}>{m.department} / {m.division}</option>)}</select></label><Link className="icon-button" aria-label="Search workspace" href="/search"><Icon name="search" size={22}/></Link>
    <div className="notification-anchor"><button className="icon-button" aria-label="Open notifications" aria-expanded={bell} onClick={()=>act(async()=>{setNotices(await api<Notice[]>('/workspace/notifications'));setBell(!bell);})}><Icon name="bell" size={22}/>{data.unread>0&&<span className="notification-dot"/>}</button>{bell&&<section className="notification-popover"><div className="section-heading"><h3>Notifications</h3><Link href="/notifications">View all</Link></div>{notices.slice(0,5).map(n=><Link href={n.href} key={n.id} onClick={()=>act(async()=>{await api('/workspace/notifications/'+n.id+'/read','POST');await refresh();setBell(false);})}>{!n.read&&<span className="recent-dot"/>}{n.title}</Link>)}{!notices.length&&<p className="muted">You're all caught up.</p>}</section>}</div>
    <details className="overflow-menu"><summary className="icon-button" aria-label="Workspace options"><Icon name="more"/></summary><div className="menu-surface"><Link href="/profile?section=preferences">Appearance & preferences</Link><Link href="/profile?section=help">Help & shortcuts</Link><button onClick={()=>setFocus(!focus)}>{focus?'Exit focus':'Focus workspace'}</button></div></details>
   </div></header>
   <main className="page-content">{actionError&&<p role="alert" className="message error">{actionError}</p>}{children}</main>
   {path!=='/'&&!path.startsWith('/chat/')&&<ContextualBrahma context={heading}/>}
  </div>
 </div>;
}
export function ContextualBrahma({context}:{context:string}){
 const router=useRouter(),path=usePathname(),{data:session}=useSession();
 const [text,setText]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[proposal,setProposal]=useState<{id:string;preview:{title:string;description:string;assignee_email:string;project_id:string|null;case_id:string|null};mode:string}|null>(null);
 const projectId=path.match(/^\/projects\/([^/]+)$/)?.[1],caseId=path.match(/^\/department\/(?:pension|grievances)\/([^/]+)$/)?.[1];
 async function preview(){setBusy(true);setError('');try{setProposal(await api('/configured/actions/propose-task','POST',{title:text,description:'Explicit follow-up requested in '+context,assignee_email:session?.user.email,project_id:projectId||null,case_id:caseId||null}));}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
 return <><div className="contextual-brahma"><Lotus size={30}/><form onSubmit={async e=>{e.preventDefault();setBusy(true);try{const chat=await api<Conversation>('/workspace/conversations','POST',{content:'Context: '+context+'\n'+text});router.push('/chat/'+chat.id);}catch(e){setError((e as Error).message);}finally{setBusy(false);}}}><label className="sr-only" htmlFor="context-message">Ask Brahma about {context}</label><input id="context-message" value={text} onChange={e=>setText(e.target.value)} placeholder={'Ask Brahma about '+context+'...'} maxLength={160} required/><button type="button" onClick={preview} disabled={busy||text.trim().length<3}>Preview task</button><span className="demo-label">AI not configured</span><button className="icon-button" aria-label="Save contextual conversation" disabled={busy}><Icon name="send"/></button></form>{error&&<p role="alert">{error}</p>}</div>{proposal&&<Modal title="Confirm Brahma task proposal" onClose={()=>setProposal(null)}><div className="form-stack"><p className="muted">{proposal.mode}. Nothing is created until you confirm.</p><h3>{proposal.preview.title}</h3><p>{proposal.preview.description}</p><p>Assignee: {proposal.preview.assignee_email}</p>{proposal.preview.project_id&&<p>Linked project: {proposal.preview.project_id}</p>}{proposal.preview.case_id&&<p>Linked case: {proposal.preview.case_id}</p>}{error&&<p role="alert">{error}</p>}<div className="form-actions"><button onClick={()=>setProposal(null)}>Cancel proposal</button><button className="primary-button" disabled={busy} onClick={async()=>{setBusy(true);try{const result=await api<{href:string}>('/configured/actions/'+proposal.id+'/confirm','POST');setProposal(null);setText('');router.push(result.href);}catch(e){setError((e as Error).message);}finally{setBusy(false);}}}>Confirm create task</button></div></div></Modal>}</>;
}
