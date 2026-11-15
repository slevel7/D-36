import {ProjectWorkspace} from '../../../components/project-workspace';
export default async function Project({params}:{params:Promise<{id:string}>}){return <ProjectWorkspace id={(await params).id}/>;}
