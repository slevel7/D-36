import {CaseWorkspace} from '../../../../components/case-workspace';
export default async function Grievance({params}:{params:Promise<{id:string}>}){return <CaseWorkspace kind="grievances" id={(await params).id}/>;}
