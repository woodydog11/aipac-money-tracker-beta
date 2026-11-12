import {useEffect,useMemo,useState} from 'react';
import {geoAlbersUsa,geoPath} from 'd3-geo';
type StateFeature={type:'Feature';properties:{name?:string;postal?:string};geometry:any};
type StateTotals={state:string;amount:number;category:string};
const states:Record<string,string>={'Alabama':'AL','Alaska':'AK','Arizona':'AZ','Arkansas':'AR','California':'CA','Colorado':'CO','Connecticut':'CT','Delaware':'DE','Florida':'FL','Georgia':'GA','Hawaii':'HI','Idaho':'ID','Illinois':'IL','Indiana':'IN','Iowa':'IA','Kansas':'KS','Kentucky':'KY','Louisiana':'LA','Maine':'ME','Maryland':'MD','Massachusetts':'MA','Michigan':'MI','Minnesota':'MN','Mississippi':'MS','Missouri':'MO','Montana':'MT','Nebraska':'NE','Nevada':'NV','New Hampshire':'NH','New Jersey':'NJ','New Mexico':'NM','New York':'NY','North Carolina':'NC','North Dakota':'ND','Ohio':'OH','Oklahoma':'OK','Oregon':'OR','Pennsylvania':'PA','Rhode Island':'RI','South Carolina':'SC','South Dakota':'SD','Tennessee':'TN','Texas':'TX','Utah':'UT','Vermont':'VT','Virginia':'VA','Washington':'WA','West Virginia':'WV','Wisconsin':'WI','Wyoming':'WY'};
export default function USFundingMap({cycle}:{cycle:string}){
 const [features,setFeatures]=useState<StateFeature[]>([]);
 const [totals,setTotals]=useState<StateTotals[]>([]);
 const [selected,setSelected]=useState('');
 const [error,setError]=useState('');
 useEffect(()=>{
  const controller=new AbortController();
  fetch('https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json',{signal:controller.signal})
   .then(r=>{if(!r.ok)throw Error('Map boundaries unavailable');return r.json()})
   .then(d=>setFeatures(d.features||[])).catch(e=>{if(e.name!=='AbortError')setError(e.message)});
  return ()=>controller.abort();
 },[]);
 useEffect(()=>{
  const controller=new AbortController();setTotals([]);setSelected('');
  const url=import.meta.env.VITE_SUPABASE_URL;const key=import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;
  if(!url||!key)return;
  fetch(url.replace(/\/$/,'')+'/rest/v1/verified_state_spending?select=state,category,amount&election_cycle=eq.'+cycle,{headers:{apikey:key},signal:controller.signal})
   .then(r=>{if(!r.ok)throw Error('Verified state data unavailable');return r.json()})
   .then(setTotals).catch(e=>{if(e.name!=='AbortError')setError(e.message)});
  return ()=>controller.abort();
 },[cycle]);
 const amounts=useMemo(()=>{const m:Record<string,number>={};totals.forEach(t=>m[t.state]=(m[t.state]||0)+Number(t.amount));return m},[totals]);
 const max=Math.max(0,...Object.values(amounts));
 const projection=geoAlbersUsa().fitSize([960,600],{type:'FeatureCollection',features} as any);
 const path=geoPath(projection);
 const selectedAmount=amounts[selected]||0;
 return <div className="us-map"><svg viewBox="0 0 960 600" role="img" aria-label="Interactive United States map showing verified political spending by state">
 {features.map((f,i)=>{const code=states[f.properties.name||'']||f.properties.postal||'';const amount=amounts[code]||0;const intensity=max?amount/max:0;return <path key={code||i} d={path(f as any)||''} fill={amount?'rgba(91,205,245,'+(0.25+0.7*intensity)+')':'#17354d'} stroke="#4b718c" strokeWidth="1.1" onClick={()=>setSelected(code)} style={{cursor:'pointer'}}><title>{f.properties.name}: {amount?new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(amount):'No verified amount'}</title></path>})}</svg>
 <div className="map-state-info">{selected?<><b>{selected}</b><span>{selectedAmount?new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(selectedAmount):'No verified transactions'}</span></>:<span>{error||'Select a state to inspect verified spending.'}</span>}</div>
 <div className="map-disclaimer">Only approved FEC transactions appear in state totals. No verified transactions are currently published.</div>
 </div>
}
