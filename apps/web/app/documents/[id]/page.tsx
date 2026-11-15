import {DocumentWorkspace} from '../../../components/document-workspace';
export default async function Document({params,searchParams}:{params:Promise<{id:string}>;searchParams:Promise<{version?:string}>}){return <DocumentWorkspace id={(await params).id} initialVersion={(await searchParams).version}/>;}
