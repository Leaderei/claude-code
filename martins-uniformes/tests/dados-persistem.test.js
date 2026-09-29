// Teste de regressão: dados reais nunca se perdem em atualizações.
// Rodar: NODE_PATH=$(npm root -g) node martins-uniformes/tests/dados-persistem.test.js
const { chromium } = require('playwright');const fs=require('fs'),path=require('path');
const APP='file://'+path.resolve(__dirname,'../app.html');let falhas=0;const ok=(c,m)=>{console.log((c?'  ✔ ':'  ✘ ')+m);if(!c)falhas++};
const store=new Map(),pages=[];
const merge=(a,b)=>{for(const k of Object.keys(b)){if(b[k]&&typeof b[k]==='object'&&!Array.isArray(b[k])&&a[k]&&typeof a[k]==='object')merge(a[k],b[k]);else a[k]=b[k]}return a};
const list=c=>[...store.entries()].filter(([p])=>p.split('/').length===2&&p.split('/')[0]===c).map(([p,d])=>({id:p.split('/')[1],data:d}));
async function bc(c){for(const p of pages)await p.evaluate(([c,d])=>window.__push&&window.__push(c,d),[c,list(c)]).catch(()=>{})}
async function dbop(o,p,data){if(o==='get')return {data:store.get(p)||null};if(o==='list')return list(p);if(o==='acquire')return {acquired:true};
  const c=p.split('/')[0];if(o==='set')store.set(p,JSON.parse(JSON.stringify(data)));if(o==='update'){if(!store.has(p))return {err:'invalid_argument'};merge(store.get(p),data)}if(o==='delete')store.delete(p);setTimeout(()=>bc(c),10);return {}}
const conta=c=>list(c).length;
(async()=>{const b=await chromium.launch();const fake=fs.readFileSync(path.join(__dirname,'fakedb.js'),'utf8');const erros=[];
  async function aparelho(n){const ctx=await b.newContext({viewport:{width:1000,height:850}});await ctx.exposeFunction('__dbop',dbop);await ctx.addInitScript(fake);
    await ctx.addInitScript(()=>{try{if(!localStorage.getItem('martins-sessao'))localStorage.setItem('martins-sessao',JSON.stringify({id:'u-helena',email:'helenanenimga67@gmail.com'}))}catch(e){}});
    const p=await ctx.newPage();p.on('pageerror',e=>erros.push(n+': '+e.message));pages.push(p);await p.goto(APP);await p.waitForTimeout(1200);const e=await p.$('text=Entendi');if(e)await e.click();return p}
  console.log('1) Começar na nuvem e cadastrar um pedido real');
  const A=await aparelho('A');await A.click('[data-a=inicio][data-v=exemplo]');await A.waitForTimeout(2500);
  await A.click('[data-a=novo]');await A.fill('#wCli','Cliente Real Ltda');await A.click('[data-a=wVend] >> nth=0');await A.click('[data-a=wNext]');await A.click('[data-a=wAdd][data-p=cam-mc]');
  await A.evaluate(()=>{const it=ui.sheet.w.itens[0];it.cor='Marinho';it.tecido='Malha PV';it.g={M:10,G:5};ui.sheet.w.step=3;ui.sheet.w.entrega=Date.now()+20*864e5;render()});await A.evaluate(()=>A.wCriar());await A.waitForTimeout(2000);
  const real=await A.evaluate(()=>state.pedidos.find(p=>p.cliente==='Cliente Real Ltda')?.id);ok(!!real&&store.has('pedidos/'+real),'pedido real está na nuvem');
  const antes=new Set(store.keys());
  console.log('2) Atualização do app (recarregar a página com o código novo)');
  await A.reload();await A.waitForTimeout(2500);const B=await aparelho('B');await B.waitForTimeout(2500);
  const sumiu=[...antes].filter(k=>!store.has(k)&&!k.startsWith('log/'));ok(!sumiu.length,'nenhum documento sumiu da nuvem'+(sumiu.length?': '+sumiu.join(', '):''));
  ok(await B.evaluate(r=>!!pedById(r),real),'outro aparelho vê o pedido real');
  console.log('3) Cópia de segurança diária');
  await B.waitForTimeout(3000);const bk=list('backup');ok(bk.some(x=>/^\d{4}-\d\d-\d\d$/.test(x.id)),'cópia do dia guardada na nuvem');
  console.log('4) Apagar só os exemplos');
  await A.evaluate(()=>{ui.tela='cadastros';ui.cad='ajustes';render()});await A.click('[data-a=apagaEx]');await A.click('[data-a=apagaEx][data-ok="1"]');await A.waitForTimeout(3500);
  ok(store.has('pedidos/'+real),'pedido real continua');ok(!store.has('pedidos/0412'),'pedido de exemplo saiu');
  ok(list('backup').some(x=>x.id.includes('antes-de-apagar-exemplos')),'cópia feita antes de apagar');ok(conta('lixeira')>=8,'apagados foram para a lixeira ('+conta('lixeira')+')');
  console.log('5) Restaurar da lixeira');
  await A.evaluate(()=>{const p=state.pessoas.find(x=>x.nome==='Zezé');snap();state.pessoas=state.pessoas.filter(x=>x!==p);commit()});await A.waitForTimeout(1500);
  const doc=list('lixeira').find(x=>x.data.col==='pessoas');ok(!!doc,'pessoa apagada está na lixeira');
  await A.evaluate(v=>A.lixRest({v}),doc.id);await A.waitForTimeout(1500);ok(await A.evaluate(()=>state.pessoas.some(x=>x.nome==='Zezé')),'pessoa restaurada');
  console.log('6) Trava contra reinicializar por cima');
  store.delete('config/main');const C=await aparelho('C');await C.waitForTimeout(4000);console.log('    debug',await C.evaluate(()=>[NV.modo,NV.st,state.pedidos.map(p=>p.id).join(','),!!ui.inicio]));
  ok(await C.evaluate(()=>!ui.inicio),'não mostra "Vamos começar" quando já há dados');ok(await C.evaluate(r=>!!pedById(r),real),'dados carregados');
  console.log('7) Restaurar a cópia de antes de apagar');
  const nome=list('backup').find(x=>x.id.includes('antes-de-apagar')).id;await C.evaluate(async n=>{await restaurar(await lerBackup(n))},nome);await C.waitForTimeout(2500);
  ok(store.has('pedidos/0412')&&store.has('pedidos/'+real),'cópia restaurada com exemplos e o pedido real');
  ok(!erros.length,'sem erros de JavaScript'+(erros.length?': '+erros.join(' | '):''));
  await b.close();console.log(falhas?`\n${falhas} FALHA(S)`:'\nTudo certo.');process.exit(falhas?1:0)})();
