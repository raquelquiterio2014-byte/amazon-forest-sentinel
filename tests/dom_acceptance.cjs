const {JSDOM,VirtualConsole}=require('jsdom');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const base=process.env.FOREST_TEST_URL||'http://127.0.0.1:8765';
const outdir=path.join(__dirname,'..','data');fs.mkdirSync(outdir,{recursive:true});
const delay=ms=>new Promise(r=>setTimeout(r,ms));
async function until(fn,ms=15000){const end=Date.now()+ms;while(Date.now()<end){if(fn())return;await delay(50)}throw Error('Timed out: '+fn.toString())}
(async()=>{
const errors=[],console=new VirtualConsole();console.on('jsdomError',e=>errors.push(e.message));
const dom=await JSDOM.fromURL(base,{runScripts:'dangerously',resources:'usable',pretendToBeVisual:true,virtualConsole:console,beforeParse(w){w.fetch=(path,options)=>fetch(new URL(path,base),options);w.File=global.File;w.Blob=global.Blob;w.URL.createObjectURL=()=> 'blob:qa-mock';w.URL.revokeObjectURL=()=>{};w.SVGSVGElement.prototype.createSVGRect=()=>({});}});
const w=dom.window,$=id=>w.document.getElementById(id);global.qaWindow=w;const click=id=>$(id).click();const nav=id=>w.document.querySelector('nav [data-page="'+id+'"]').click();
await until(()=>$('metrics').children.length===4);click('load-demo');await until(()=>$('metrics').textContent.includes('63'));
assert.equal(w.document.querySelector('#metrics strong').textContent,'63');
nav('sources'); click('sample-inpe');await until(()=>$('mode').value==='FIELD'&&w.document.querySelector('#metrics strong').textContent==='8');
nav('map');await delay(250);assert.ok(w.document.querySelector('.leaflet-container'));click('fit-map');
$('mode').value='DEMO';$('mode').dispatchEvent(new w.Event('change'));await until(()=>w.document.querySelector('#metrics strong').textContent==='63');
nav('imagery');click('demo-images');await until(()=>$('image-result').textContent.includes('loaded'));click('analyze');await until(()=>$('image-summary').textContent.includes('10000'));assert.equal(JSON.parse($('image-summary').textContent).result.changed_pixels,10000);
$('image-method').value='ndvi';$('image-method').dispatchEvent(new w.Event('change'));click('demo-images');await until(()=>$('image-result').textContent.includes('NDVI'));click('analyze');await until(()=>$('image-summary').textContent.includes('NDVI decline'));assert.equal(JSON.parse($('image-summary').textContent).result.area_ha,100);
nav('ai');click('local-ai');await until(()=>$('ai-result').textContent.includes('IsolationForest'));assert.equal(JSON.parse($('ai-result').textContent).training_count,50);
nav('evidence');$('search').value='demo-event-0';$('search').dispatchEvent(new w.Event('input'));w.document.querySelector('#evidence-body tr[data-id]').click();nav('review');$('reviewer').value='DOM acceptance reviewer';$('review-note').value='Checked synthetic fixture; no field claim.';click('save-review');await until(()=>$('review-history').textContent.includes('DOM acceptance reviewer'));
nav('sensors');assert.ok($('sites').textContent.includes('DEMO-OFFLINE'));assert.ok($('sites').textContent.includes('STALE'));
nav('reports');assert.ok($('integrity').textContent.includes('true'));nav('method');assert.equal($('method').hidden,false);
const http=await fetch(base);const html=await http.text();const token=html.match(/SESSION_TOKEN='([^']+)'/)[1];
for(const format of ['json','csv','html']){const r=await fetch(base+'/api/export?mode=DEMO&format='+format,{headers:{'X-Session-Token':token}});assert.equal(r.status,200);const text=await r.text();assert.ok(text.length>200);fs.writeFileSync(path.join(outdir,'qa_export.'+format),text)}
const criticalErrors=errors.filter(e=>!e.includes('navigation to another Document')&&!e.includes('Could not parse CSS stylesheet')&&!e.includes('Could not load img: \"blob:qa-mock\"'));
const report={environment:'JSDOM + real local HTTP backend (not a visual browser)',passed:['demo','official INPE sample import','Leaflet map creation','RGB pipeline','NDVI pipeline','local IsolationForest','evidence selection','human review','sensor status','JSON CSV HTML exports','methodology navigation'],javascript_errors:criticalErrors,visual_layout:'DOM checks only; no pixel-layout or image-decoding verification.'};
fs.writeFileSync(path.join(outdir,'dom_acceptance.json'),JSON.stringify(report,null,2));process.stdout.write(JSON.stringify(report,null,2)+'\n');dom.window.close();assert.equal(criticalErrors.length,0);
})().catch(e=>{process.stderr.write(e.stack+'\n');if(global.qaWindow){for(const id of ['toast','import-result','metrics'])process.stderr.write(id+': '+global.qaWindow.document.getElementById(id).textContent+'\n');}process.exit(1)});
