window.__subs=[];
window.__push=(c,docs)=>{window.__subs.filter(s=>s.c===c).forEach(s=>s.deliver(docs))};
const mkSnap=(docs,prev)=>{const ch=[];const pm=new Map(prev.map(d=>[d.id,d]));const nm=new Map(docs.map(d=>[d.id,d]));
  docs.forEach(d=>{const o=pm.get(d.id);if(!o)ch.push({type:'added',doc:ds(d)});else if(JSON.stringify(o.data)!==JSON.stringify(d.data))ch.push({type:'modified',doc:ds(d)})});
  prev.forEach(o=>{if(!nm.has(o.id))ch.push({type:'removed',doc:ds(o)})});
  return {docs:docs.map(ds),size:docs.length,empty:!docs.length,docChanges:()=>ch,metadata:{fromCache:false,hasPendingWrites:false}}};
const ds=d=>({id:d.id,exists:true,data:()=>JSON.parse(JSON.stringify(d.data)),metadata:{}});
const op=(...a)=>window.__dbop(...a).then(r=>{if(r&&r.err)throw {code:r.err,message:r.err};return r});
const docRef=path=>({id:path.split('/').pop(),path,
  get:async()=>{const r=await op('get',path);return r.data?{id:path.split('/').pop(),exists:true,data:()=>r.data,metadata:{}}:{exists:false,data:()=>undefined}},
  set:d=>op('set',path,d),update:d=>op('update',path,d),delete:()=>op('delete',path),acquire:o=>op('acquire',path,o)});
const colRef=c=>({path:c,doc:id=>docRef(c+'/'+id),
  get:async()=>{const r=await op('list',c);return mkSnap(r,[])},
  onSnapshot:(next)=>{const s={c,prev:[],deliver(docs){const sn=mkSnap(docs,s.prev);s.prev=docs;next(sn)}};window.__subs.push(s);op('list',c).then(r=>s.deliver(r));return()=>{window.__subs=window.__subs.filter(x=>x!==s)}}});
const DB={doc:docRef,collection:colRef};
window.claude={use:async n=>n==='db'?DB:null};
