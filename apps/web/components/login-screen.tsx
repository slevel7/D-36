'use client';
import {useState} from 'react';
import {useRouter} from 'next/navigation';
import {api,ApiError,setCsrf} from '../lib/api';
import {Brand} from './icons';
import {Feedback,useAction} from './ui';
import {useSession} from './session-provider';
export function LoginScreen(){
 const router=useRouter(),{refresh}=useSession(),action=useAction();const [visible,setVisible]=useState(false);
 return <main className="login-page"><Brand/><p>Authorised employee workspace - DEMO</p><form onSubmit={e=>{e.preventDefault();const f=new FormData(e.currentTarget);action.run(async()=>{await api('/auth/login','POST',{email:f.get('email'),password:f.get('password')});const me=await api<{csrf:string}>('/auth/me');setCsrf(me.csrf);await refresh();router.push('/');},'');}}><label>Account email<input type="email" name="email" autoComplete="username" required/></label><label>Password<input name="password" type={visible?'text':'password'} autoComplete="current-password" required/></label><button type="button" onClick={()=>setVisible(!visible)}>{visible?'Hide password':'Show password'}</button><button className="primary-button" disabled={action.busy}>{action.busy?'Signing in...':'Sign in'}</button><Feedback error={action.error}/><small>Use a seeded demo account from the local setup guide. Password recovery requires an administrator; no public registration.</small></form></main>;
}
