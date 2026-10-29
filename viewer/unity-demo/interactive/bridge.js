(()=>{
const scenes=new Set(['plain','slope','rim','depression','ridge','ejecta','rille']);
const views=new Set(['low','high','orbit','overview','detail']);
const materials=new Set(['mixed','original','moon_01','moon_03','moon_04','moon_flat_macro_01','moon_dusted_01']);
if(parent!==window)document.querySelector('.gesture').hidden=true;
function tell(type){parent.postMessage({type,state:{...PILOT.state,material:TEXTURE_TRIAL.state.material},textures:PILOT.textures},'*')}
function apply(m){if(m.scene&&scenes.has(m.scene)&&m.scene!==PILOT.state.region)PILOT.setRegion(m.scene);if(m.view&&views.has(m.view)&&m.view!==PILOT.state.view)PILOT.setView(m.view);if(m.material&&materials.has(m.material)&&m.material!==TEXTURE_TRIAL.state.material)TEXTURE_TRIAL.setMaterial(m.material);PILOT.render();tell('lunar-state')}
window.addEventListener('message',e=>{if(e.source!==parent||!e.data)return;if(e.data.type==='lunar-set')apply(e.data);else if(e.data.type==='lunar-reset'){PILOT.setView(PILOT.state.view);PILOT.render();tell('lunar-state')}});
window.addEventListener('hashchange',()=>{const scene=location.hash.slice(1);if(scenes.has(scene))apply({scene})});
let readySent=false;const started=performance.now();
const timer=setInterval(()=>{const t=PILOT.textures;document.getElementById('load-progress').textContent=`本地贴图 ${t.loaded} / ${t.expected}`;if(t.failed.length){document.getElementById('error').style.display='grid';document.getElementById('error-detail').textContent='部分本地贴图未能载入，请重新加载或返回 Unity 渲染模式。';tell('lunar-error');clearInterval(timer)}else if(PILOT.loaded&&!readySent){readySent=true;tell('lunar-ready');clearInterval(timer)}else if(performance.now()-started>60000){document.getElementById('load-progress').textContent=`仍在准备三维场景（${t.loaded}/${t.expected}），可返回 Unity 渲染继续演示。`}},250);
document.addEventListener('visibilitychange',()=>{if(!document.hidden){PILOT.render()}});
window.LUNAR_BRIDGE={apply,get state(){return {...PILOT.state,material:TEXTURE_TRIAL.state.material}}};
})();
