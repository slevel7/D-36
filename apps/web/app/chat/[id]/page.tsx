import {ChatScreen} from '../../../components/chat-screen';
export default async function Chat({params}:{params:Promise<{id:string}>}){return <ChatScreen id={(await params).id}/>;}
