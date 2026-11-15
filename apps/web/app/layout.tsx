import './style.css';
import {AppShell} from '../components/app-shell';
import {SessionProvider} from '../components/session-provider';
export const metadata={title:'BrahmaGPT | Singularity',description:'Internal authorised employee workspace',icons:{icon:'/brand/brahmagpt-lotus.png'}};
export default function Layout({children}:{children:React.ReactNode}){return <html lang="en" suppressHydrationWarning><body><SessionProvider><AppShell>{children}</AppShell></SessionProvider></body></html>;}
