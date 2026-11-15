'use client';
import {createContext,useContext,useEffect,useState,ReactNode} from 'react';
import {api,ApiError,applyPreferences,Bootstrap,setCsrf} from '../lib/api';
type SessionValue={data:Bootstrap|null;loading:boolean;error:string;refresh:()=>Promise<void>;signOut:()=>Promise<void>};
const Context=createContext<SessionValue|null>(null);
export function SessionProvider({children}:{children:ReactNode}){
 const [data,setData]=useState<Bootstrap|null>(null),[loading,setLoading]=useState(true),[error,setError]=useState('');
 async function refresh(){const info=await api<Bootstrap>('/workspace/bootstrap');setData(info);applyPreferences(info.preferences);}
 async function restore(){
  try {
   let response=await fetch('/api/auth/me',{credentials:'same-origin'});
   if(response.status===401){const demo=await fetch('/api/auth/demo',{method:'POST',headers:{'x-brahma-demo':'local-preview'}});if(demo.ok)response=await fetch('/api/auth/me');}
   if(response.ok){setCsrf((await response.json()).csrf);await refresh();}
   else if(response.status!==401)throw new Error('Your workspace session could not be restored.');
  }catch(e){setError((e as Error).message);}finally{setLoading(false);}
 }
 useEffect(()=>{restore();},[]);
 async function signOut(){await api('/auth/logout','POST');setCsrf('');setData(null);window.location.assign('/login');}
 return <Context.Provider value={{data,loading,error,refresh,signOut}}>{children}</Context.Provider>;
}
export function useSession(){const value=useContext(Context);if(!value)throw Error('Session provider missing');return value;}
