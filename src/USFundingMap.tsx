import {useEffect,useMemo,useState} from 'react';
import {geoAlbersUsa,geoPath,geoArea} from 'd3-geo';
type StateFeature={type:'Feature';properties:{name?:string;postal?:string};geometry:any};
type StateTotals={state:string;amount:number;category:string};
// The source GeoJSON uses planar exterior-ring winding. Reverse all rings
// to match D3's spherical convention; a conditional geoArea check was unreliable.
function normalizeWinding(feature:StateFeature):StateFeature {
 // D3 interprets clockwise exterior rings as the complement of a state.
 // Reverse ONLY polygons whose spherical area exceeds a hemisphere.
 if(geoArea(feature as any)<2*Math.PI)return feature;
 const geometry=feature.geometry;
 if(!geometry)return feature;
 if(geometry.type==='Polygon')return {...feature,geometry:{...geometry,coordinates:geometry.coordinates.map((ring:number[][])=>[...ring].reverse())}};
 if(geometry.type==='MultiPolygon')return {...feature,geometry:{...geometry,coordinates:geometry.coordinates.map((poly:number[][][])=>poly.map((ring:number[][])=>[...ring].reverse()))}};
 return feature;
}
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
   .then(d=>setFeatures((d.features||[]).map(normalizeWinding))).catch(e=>{if(e.name!=='AbortError')setError(e.message)});
  return ()=>controller.abort();
 },[]);
 useEffect(()=>{
  const controller=new AbortController();setTotals([]);setSelected('');
  const url=import.meta.env.VITE_SUPABASE_URL;const key=import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;
  if(!url||!key)return;
  fetch(url.replace(/\/$/,'')+'/rest/v1/rpc/preliminary_state_spending',{method:'POST',headers:{apikey:key,'Content-Type':'application/json'},body:JSON.stringify({p_cycle:Number(cycle)}),signal:controller.signal})
   .then(r=>{if(!r.ok)throw Error('Preliminary state data unavailable');return r.json()})
   .then(setTotals).catch(e=>{if(e.name!=='AbortError')setError(e.message)});
  return ()=>controller.abort();
 },[cycle]);
 const amounts=useMemo(()=>{const m:Record<string,number>={};totals.forEach(t=>m[t.state]=(m[t.state]||0)+Number(t.amount));return m},[totals]);
 const max=Math.max(0,...Object.values(amounts));
 // Use D3's calibrated US composite projection. fitSize() on this external
 // GeoJSON collection distorted the viewport and clipped most states.
 const projection=geoAlbersUsa().scale(1230).translate([480,300]);
 const path=geoPath(projection);
 const selectedAmount=amounts[selected]||0;
 const renderedCount=features.filter(f=>Boolean(path(f as any))).length;
 return <div className="us-map"><svg viewBox="0 0 960 600" role="img" aria-label="Interactive United States map showing preliminary, unverified political spending by state">
 {features.map((f,i)=>{const code=states[f.properties.name||'']||f.properties.postal||'';const amount=amounts[code]||0;const intensity=max?amount/max:0;return <path key={code||i} d={path(f as any)||''} fill={amount?'rgba(91,205,245,'+(0.25+0.7*intensity)+')':'#17354d'} stroke="#4b718c" strokeWidth="1.1" onClick={()=>setSelected(code)} style={{cursor:'pointer'}}><title>{f.properties.name}: {amount?new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(amount):'No preliminary records'}</title></path>})}</svg>
 <div className="map-state-info">{selected?<><b>{selected}</b><span>{selectedAmount?new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(selectedAmount):'No preliminary records'}</span></>:<span>{error||'Select a state to inspect preliminary FEC totals.'}</span>}</div>
 <div className="map-disclaimer">{features.length ? `${renderedCount} state boundaries loaded. ` : 'Loading state boundaries. '}PRELIMINARY · UNVERIFIED. State totals may include amendments and pass-throughs; not money received by candidates.</div>
 </div>
}
