import {TaskDetail} from '../../../components/task-workspace';
export default async function Task({params}:{params:Promise<{id:string}>}){return <TaskDetail id={(await params).id}/>;}
