import {Suspense} from 'react';
import {ProfileScreen} from '../../components/profile-screen';
export default function Profile(){return <Suspense fallback={<p>Loading profile...</p>}><ProfileScreen/></Suspense>;}
