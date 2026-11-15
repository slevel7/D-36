import {CampaignWorkspace} from '../../../../components/outreach-workspace';
export default async function Campaign({params}:{params:Promise<{id:string}>}){return <CampaignWorkspace id={(await params).id}/>;}
