'use client';
import {ReactNode,useEffect,useRef,useState} from 'react';
import {api} from '../lib/api';
import {useSession} from './session-provider';
export function useResource<T>(path:string){
 const {data:session}=useSession();const [data,setData]=useState<T>(),[error,setError]=useState('');
 async function reload(){try{setData(await api<T>(path));setError('');}catch(e){setError((e as Error).message);}}
 useEffect(()=>{let cancelled=false;setData(undefined);api<T>(path).then(value=>{if(!cancelled){setData(value);setError('');}}).catch(e=>{if(!cancelled)setError(e.message);});return()=>{cancelled=true};},[path,session?.user.department]);
 return {data,error,reload};
}
export function useAction(){const [busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');async function run(fn:()=>Promise<void>,message='Saved successfully'){setBusy(true);setError('');setNotice('');try{await fn();setNotice(message);}catch(e){setError((e as Error).message);}finally{setBusy(false);}}return {busy,error,notice,run};}
export function Feedback({error,notice}:{error?:string;notice?:string}){return <>{error&&<p className="message error" role="alert">{error}</p>}{notice&&<p className="message" role="status">{notice}</p>}</>;}
export function Card({title,children,className=''}:{title:string;children:ReactNode;className?:string}){return <section className={'card '+className}><h3>{title}</h3>{children}</section>;}
export function Empty({title,children}:{title:string;children?:ReactNode}){return <div className="empty-state"><h3>{title}</h3>{children&&<p>{children}</p>}</div>;}
export function Modal({title,children,onClose}:{title:string;children:ReactNode;onClose:()=>void}){const ref=useRef<HTMLDialogElement>(null);useEffect(()=>{ref.current?.showModal();},[]);return <dialog ref={ref} aria-label={title} onCancel={onClose} onClick={e=>{if(e.target===e.currentTarget)onClose();}}><div className="dialog-heading"><h2>{title}</h2><button type="button" className="icon-button" aria-label="Close dialog" onClick={onClose}>x</button></div>{children}</dialog>;}
export function DataRows({rows}:{rows:[string,ReactNode][]}){return <dl className="data-rows">{rows.map(([name,value])=><div key={name}><dt>{name}</dt><dd>{value||<span className="muted">Not provided</span>}</dd></div>)}</dl>;}
export function Loading(){return <p className="loading" role="status">Loading your workspace...</p>;}
