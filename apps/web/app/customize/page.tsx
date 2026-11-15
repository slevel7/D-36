import {Suspense} from 'react';
import {CustomizeScreen} from '../../components/customize-screen';
export default function Customize(){return <Suspense fallback={<p>Loading tools...</p>}><CustomizeScreen/></Suspense>;}
