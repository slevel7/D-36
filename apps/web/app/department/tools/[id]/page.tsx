import {ConfiguredTool} from '../../../../components/configured-tools';
export default async function Tool({params}:{params:Promise<{id:string}>}){return <ConfiguredTool id={(await params).id}/>;}
