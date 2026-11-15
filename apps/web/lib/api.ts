export type User = {id:string;email:string;role:string;display_name:string;department:string;division:string};
export type Membership = {id:string;department_id:string;department:string;division_id:string;division:string;role:string;status:string;expires:number|null};
export type Preferences = {theme:string;language:string;text_size:string;date_format:string;time_format:string;sidebar:string;home_summary:boolean;task_view:string;week_start:string;reduced_motion:boolean;document_default:string;draft_only_actions:boolean;default_model:string;notifications:Record<string,boolean>;digest:string;quiet_start:string;quiet_end:string};
export type Bootstrap = {user:User;memberships:Membership[];preferences:Preferences;unread:number};
export type Tool = {id:string;title:string;description:string;category:string;href:string;status:string;provider:string|null;department_tool:boolean;favourite:boolean;position:number|null;last_used:number|null;why:string};
export type Profile = User & {phone:string;contact_email:string;office_address:string;bio:string;avatar_url:string|null;designation:string|null;employee_id:string|null;identity_status:string};
export type Notice = {id:string;title:string;category:string;href:string;read:boolean;created:number};
export type Conversation = {id:string;title:string;pinned:boolean;archived:boolean;created:number};
let csrf='';
export function setCsrf(value:string){csrf=value;}
export class ApiError extends Error { constructor(public status:number,message:string,public retryAfter=0){super(message);} }
export async function api<T=unknown>(path:string,method='GET',data?:unknown):Promise<T>{
 const multipart=data instanceof FormData;
 const response=await fetch('/api'+path,{method,credentials:'same-origin',headers:{...(multipart?{}:{'Content-Type':'application/json'}),'x-csrf-token':csrf},body:data===undefined?undefined:multipart?data:JSON.stringify(data)});
 const value=await response.json().catch(()=>null);
 if(!response.ok)throw new ApiError(response.status,typeof value?.detail==='string'?value.detail:'The request could not be completed.',Number(response.headers.get('retry-after'))||0);
 return value as T;
}
export function applyPreferences(p:Preferences){
 document.documentElement.dataset.theme=p.theme;document.documentElement.dataset.textSize=p.text_size;
 document.documentElement.dataset.reducedMotion=String(p.reduced_motion);
 document.documentElement.dataset.sidebar=p.sidebar;document.documentElement.dataset.dateFormat=p.date_format;document.documentElement.dataset.timeFormat=p.time_format;
}
export function date(value:number){const date=new Date(value*1000);const settings=typeof document==='undefined'?{}:document.documentElement.dataset;const day=String(date.getDate()).padStart(2,'0'),month=String(date.getMonth()+1).padStart(2,'0');const formatted=settings.dateFormat==='YYYY-MM-DD'?date.getFullYear()+'-'+month+'-'+day:day+'/'+month+'/'+date.getFullYear();return formatted+' '+date.toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit',hour12:settings.timeFormat==='12h'});}
