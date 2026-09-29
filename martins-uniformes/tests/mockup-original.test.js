// Teste de regressão: o mockup original NUNCA pode se perder nem perder definição.
// Rodar: NODE_PATH=$(npm root -g) node martins-uniformes/tests/mockup-original.test.js
const { chromium } = require('playwright');const fs=require('fs'),path=require('path'),crypto=require('crypto');
const APP='file://'+path.resolve(__dirname,'../app.html');
const FX={marinho:path.join(__dirname,'fixtures/mockup-marinho.png'),royal:path.join(__dirname,'fixtures/mockup-royal.png')};
const md5=b=>crypto.createHash('md5').update(b).digest('hex');
const ORIG={marinho:'data:image/png;base64,'+fs.readFileSync(FX.marinho).toString('base64'),royal:'data:image/png;base64,'+fs.readFileSync(FX.royal).toString('base64')};
let falhas=0;const ok=(c,msg)=>{console.log((c?'  ✔ ':'  ✘ ')+msg);if(!c)falhas++};
// banco "nuvem" falso, compartilhado entre aparelhos
const store=new Map(),pages=[];
const merge=(a,b)=>{for(const k of Object.keys(b)){if(b[k]&&typeof b[k]==='object'&&!Array.isArray(b[k])&&a[k]&&typeof a[k]==='object')merge(a[k],b[k]);else a[k]=b[k]}return a};
const list=c=>[...store.entries()].filter(([p])=>p.split('/').length===2&&p.split('/')[0]===c).map(([p,d])=>({id:p.split('/')[1],data:d}));
async function bc(c){for(const p of pages)await p.evaluate(([c,d])=>window.__push&&window.__push(c,d),[c,list(c)]).catch(()=>{})}
async function dbop(o,p,data){if(o==='get')return {data:store.get(p)||null};if(o==='list')return list(p);if(o==='acquire')return {acquired:true};
  const c=p.split('/')[0];if(o==='set')store.set(p,JSON.parse(JSON.stringify(data)));if(o==='update'){if(!store.has(p))return {err:'invalid_argument'};merge(store.get(p),data)}if(o==='delete')store.delete(p);setTimeout(()=>bc(c),10);return {}}
const nuvemMock=id=>{const m=store.get('mock/'+id);if(!m)return null;let s='';for(let k=0;k<m.n;k++){const d=store.get(`mockp/${id}~${k}`);if(!d)return null;s+=d.d}return s};
(async()=>{const b=await chromium.launch();const fake=fs.readFileSync(path.join(__dirname,'fakedb.js'),'utf8');const erros=[];
  async function aparelho(nome,{nuvem=true,semIDB=false}={}){const ctx=await b.newContext({viewport:{width:1000,height:850}});
    if(nuvem){await ctx.exposeFunction('__dbop',dbop);await ctx.addInitScript(fake)}
    if(semIDB)await ctx.addInitScript(()=>{Object.defineProperty(window,'indexedDB',{get(){throw new Error('sem IndexedDB')}})});
    await ctx.addInitScript(()=>{try{if(!localStorage.getItem('martins-sessao'))localStorage.setItem('martins-sessao',JSON.stringify({id:'u-helena',email:'helenanenimga67@gmail.com'}))}catch(e){}});
    const p=await ctx.newPage();p.on('pageerror',e=>erros.push(nome+': '+e.message));pages.push(p);await p.goto(APP);await p.waitForTimeout(900);const e=await p.$('text=Entendi');if(e)await e.click();return {ctx,p}}
  const zoomDe=async(p,ped,n)=>{await p.evaluate(x=>openSheet({t:'pedido',id:x}),ped);await p.waitForTimeout(300);await p.click(`.sheet svg.mock[data-z] >> nth=${n}`);await p.waitForTimeout(1500);
    const r=await p.$eval('.zm-area img',i=>({w:i.naturalWidth,src:i.src}));await p.click('[data-zm="x"]');return r};
  console.log('1) Importar os dois mockups no aparelho A (com nuvem)');
  const A=await aparelho('A');await A.p.click('[data-a=inicio][data-v=exemplo]');await A.p.waitForTimeout(2500);
  await A.p.evaluate(()=>openSheet({t:'pedido',id:'0419'}));
  for(const [n,f] of [[0,FX.marinho],[1,FX.royal]]){await A.p.click(`[data-a=mockUm] >> nth=${n}`);await A.p.setInputFiles('#fImpM1',f);await A.p.waitForTimeout(2500)}
  await A.p.waitForTimeout(1000);
  ok(nuvemMock('0419-1')===ORIG.marinho,'nuvem guardou o original Marinho byte a byte');
  ok(nuvemMock('0419-2')===ORIG.royal,'nuvem guardou o original Royal byte a byte');
  ok(!!nuvemMock('0419-1~c')&&nuvemMock('0419-1~c').length>100000,'nuvem guardou o recorte sem perda para os documentos');
  console.log('2) Aparelho A depois de apagar o armazenamento local');
  await A.p.evaluate(async()=>{Object.keys(localStorage).filter(k=>k.startsWith('martins-bin:')).forEach(k=>localStorage.removeItem(k));await new Promise(r=>{const q=indexedDB.deleteDatabase('martins-mock');q.onsuccess=q.onerror=q.onblocked=r})});
  await A.p.reload();await A.p.waitForTimeout(1500);
  let z=await zoomDe(A.p,'0419',0);ok(z.w===762&&z.src===ORIG.marinho,`zoom mostra o original (${z.w}px)`);
  console.log('3) Aparelho B novo');
  const B=await aparelho('B');await B.p.waitForTimeout(1200);
  z=await zoomDe(B.p,'0419',1);ok(z.w===562&&z.src===ORIG.royal,`zoom no outro aparelho mostra o original (${z.w}px)`);
  const docs=await B.p.evaluate(async()=>{const ls=lotesDe('0419');await Promise.all(ls.map(pegaMock));const h=docMockPag(ls[0],pedById('0419'),1,2);const m=h.match(/<img src="([^"]+)"/);return m?m[1].length:0});
  ok(docs>100000,`página de mockup do PDF usa a imagem grande (${docs} caracteres), não a miniatura`);
  const ficha=await B.p.evaluate(async()=>{const l=lotesDe('0419')[0];await pegaMock(l);return mockGrande(l).length});ok(ficha>100000,'ficha de produção usa a imagem grande');
  console.log('4) Formato antigo (mockups guardados na coleção "mockups") é recuperado');
  store.set('mockups/0419-1',{img:ORIG.marinho});['mock/0419-1','mockp/0419-1~0','mockp/0419-1~1','mockp/0419-1~2'].forEach(k=>store.delete(k));
  const C=await aparelho('C');await C.p.waitForTimeout(3000);ok(nuvemMock('0419-1')===ORIG.marinho,'original antigo migrado de volta para a nuvem');
  console.log('5) Aparelho sem IndexedDB e sem nuvem (usa a reserva local)');
  const D=await aparelho('D',{nuvem:false,semIDB:true});await D.p.evaluate(()=>openSheet({t:'pedido',id:'0419'}));await D.p.click('[data-a=mockUm] >> nth=0');await D.p.setInputFiles('#fImpM1',FX.royal);await D.p.waitForTimeout(2500);
  await D.p.reload();await D.p.waitForTimeout(1000);z=await zoomDe(D.p,'0419',0);ok(z.w===562&&z.src===ORIG.royal,`sem IndexedDB o original continua depois de recarregar (${z.w}px)`);
  ok(!erros.length,'sem erros de JavaScript'+(erros.length?': '+erros.join(' | '):''));
  await b.close();console.log(falhas?`\n${falhas} FALHA(S)`:'\nTudo certo.');process.exit(falhas?1:0)})();
