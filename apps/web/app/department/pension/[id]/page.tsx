import {CaseWorkspace} from '../../../../components/case-workspace';
export default async function Pension({params}:{params:Promise<{id:string}>}){return <CaseWorkspace kind="pension" id={(await params).id}/>;}
