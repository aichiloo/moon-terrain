(()=>{
'use strict';
const D=window.DEMO_DATA,$=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const hash=new URLSearchParams(location.hash.slice(1));
const state={scene:D.scenes.some(s=>s.id===hash.get('scene'))?hash.get('scene'):'plain',view:['low','orbit'].includes(hash.get('view'))?hash.get('view'):'low',material:D.materials.some(m=>m.id===hash.get('material'))?hash.get('material'):'mixed',mode:'render',layout:'wipe',tour:false};
let revision=0,frameStarted=false,frameReady=false,toastTimer;
const sdata=()=>D.scenes.find(s=>s.id===state.scene),mdata=()=>D.materials.find(m=>m.id===state.material);
const paths=(mat=state.material)=>`renders/${state.scene}_${['low','orbit'].includes(state.view)?state.view:'low'}_${mat}.png`;
const imgReady=url=>new Promise((ok,fail)=>{const i=new Image();i.onload=()=>ok(url);i.onerror=()=>fail(Error(url));i.src=url;});
const toast=msg=>{$('#toast').textContent=msg;$('#toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('#toast').hidden=true,3200);};
$('#scene-nav').innerHTML=D.scenes.map((s,i)=>`<button data-scene="${s.id}" aria-pressed="false"><span class="num">${String(i+1).padStart(2,'0')}</span>${s.name}</button>`).join('');
$('#thumbnail-grid').innerHTML=D.scenes.map((s,i)=>`<button class="thumb" data-scene="${s.id}" aria-pressed="false"><img src="thumbs/${s.id}.jpg" alt="${s.name}的 Unity 混合材质预览" loading="lazy"><span>${String(i+1).padStart(2,'0')} · ${s.name}</span></button>`).join('');
$('#material-primary').innerHTML=D.materials.slice(0,2).map((m,i)=>`<button data-material="${m.id}" aria-pressed="false"><span class="letter">${i===0?'M':'A'}</span><span><span class="title">${m.name}${i===0?' · 已认可':''}</span><small>${i===0?'底层、细节与覆尘混合':'固定条件下的比较基线'}</small></span></button>`).join('');
$('#material-select').innerHTML=D.materials.map(m=>`<option value="${m.id}">${m.name}</option>`).join('');
function sendFrame(){if(!frameStarted)return;$('#interactive-frame').contentWindow?.postMessage({type:'lunar-set',scene:state.scene,view:state.view,material:state.material},'*');}
function ensureFrame(){if(frameStarted)return;frameStarted=true;$('#interactive-frame').src=`interactive/index.html#${state.scene}`;$('#interactive-frame').onload=()=>{frameReady=true;sendFrame();};}
function updateLabels(){const s=sdata(),m=mdata(),index=D.scenes.indexOf(s);const iv=state.mode==='interactive';
 $$('[data-scene]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.scene===state.scene)));
 $$('[data-material]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.material===state.material)));
 $$('[data-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.mode===state.mode)));
 $$('[data-view]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.view===state.view)));
 $$('.interactive-only').forEach(e=>e.hidden=!iv);
 $('#scene-number').textContent=`${String(index+1).padStart(2,'0')} / 07`;
 $('#scene-label').textContent=s.name;$('#scene-note').textContent=s.note;
 $('#source-name').textContent=s.source;$('#source-spacing').textContent=`${s.spacing} m`;$('#source-width').textContent=s.width>=1000?`${s.width/1000} km`:`${s.width} m`;
 $('#image-caption').textContent=`${m.short} · ${state.view==='orbit'?'俯视近景':state.view==='overview'?'地形全貌':state.view==='detail'?'细节近看':'低机位'}`;
 $('#material-select').value=state.material;$('#material-description').textContent=m.desc;
 $('#compare-name').textContent=m.short;$('#main-image').alt=`${s.name} · ${m.name} · ${state.view==='orbit'?'俯视近景':'低机位'} · Unity 实际渲染`;
 $('#base-image').alt=`${s.name} · 相同机位的原材质重建 · Unity 实际渲染`;
 $('#original-link').href=paths();$('#original-link').hidden=iv;
 $('#interactive-wrap').hidden=!iv;$('#image-stage').hidden=iv;
 $('#stage').classList.toggle('interactive',iv);$('#stage').classList.toggle('compare',state.mode==='compare');$('#stage').dataset.layout=state.layout;
 $('#compare-layout').hidden=state.mode!=='compare';$('#compare-layout').textContent=state.layout==='wipe'?'改为并排对比':'改为滑动对比';
 $('#source-badge').innerHTML=iv?'<i></i> 浏览器三维重渲染':'<i></i> Unity 实际渲染';
 $('#mode-explanation').textContent=iv?'拖动旋转 · 滚轮缩放 · 同源地形的浏览器观察':state.mode==='compare'?(state.layout==='wipe'?'拖动分界线 · 左侧原材质，右侧所选材质':'左侧原材质 · 右侧所选材质 · 同机位'):'1920 × 1080 · 原始 Unity 渲染图';
 $('#gesture').textContent=iv?'拖动旋转 · 滚轮缩放':'固定机位 · 点击下方切换视角';
 $('#interactive-disclosure').hidden=!iv;$('#tour').hidden=!state.tour;
 $('#tour-count').textContent=`导览 ${index+1} / 7`;
 $('#tour-note').textContent=`${s.structure}。${s.use}`;
 $('#tour-prev').disabled=index===0;$('#tour-next').textContent=index===6?'结束导览 ✓':'下一个 →';
 const share=new URLSearchParams({scene:state.scene,view:state.view,material:state.material});history.replaceState(null,'','#'+share.toString());
}
async function render(){updateLabels();const token=++revision;$('#image-error').hidden=true;if(state.mode==='interactive'){$('#loading').hidden=true;ensureFrame();sendFrame();return;}
 $('#loading').hidden=false;
 const main=paths(),base=paths('original');
 try{await Promise.all([imgReady(main),...(state.mode==='compare'?[imgReady(base)]:[])]);if(token!==revision)return;$('#main-image').src=main;$('#base-image').src=base;$('#loading').hidden=true;
 }catch(e){if(token!==revision)return;$('#loading').hidden=true;$('#image-error').hidden=false;}
}
function setScene(id){if(!D.scenes.some(s=>s.id===id))return;state.scene=id;render();}
function setMode(mode){state.mode=mode;if(mode!=='interactive'&&!['low','orbit'].includes(state.view))state.view='low';render();}
$$('[data-scene]').forEach(b=>b.onclick=()=>setScene(b.dataset.scene));
$$('[data-material]').forEach(b=>b.onclick=()=>{state.material=b.dataset.material;render();});
$('#material-select').onchange=e=>{state.material=e.target.value;render();};
$$('[data-mode]').forEach(b=>b.onclick=()=>setMode(b.dataset.mode));
$$('[data-view]').forEach(b=>b.onclick=()=>{state.view=b.dataset.view;if(['overview','detail'].includes(state.view))state.mode='interactive';render();});
$('#wipe-range').oninput=e=>{const v=+e.target.value;$('#base-image').style.clipPath=`inset(0 ${100-v}% 0 0)`;$('#split-line').style.left=`${v}%`;};
$('#compare-layout').onclick=()=>{state.layout=state.layout==='wipe'?'side':'wipe';if(state.layout==='side')$('#base-image').style.clipPath='none';else $('#wipe-range').dispatchEvent(new Event('input'));render();};
$('#retry').onclick=render;
$('#reset-view').onclick=()=>{sendFrame();$('#interactive-frame').contentWindow?.postMessage({type:'lunar-reset'},'*');};
$('#tour-toggle').onclick=()=>{state.tour=!state.tour;if(state.tour){state.scene='plain';state.mode='render';state.view='low';state.material='mixed';}render();};
$('#tour-close').onclick=()=>{state.tour=false;render();};
$('#tour-prev').onclick=()=>{const n=D.scenes.findIndex(s=>s.id===state.scene);setScene(D.scenes[Math.max(0,n-1)].id);};
$('#tour-next').onclick=()=>{const n=D.scenes.findIndex(s=>s.id===state.scene);if(n===6){state.tour=false;render();toast('七类地形已展示完毕，可继续自由比较。');}else setScene(D.scenes[n+1].id);};
$('#focus-toggle').onclick=()=>{const on=document.body.classList.toggle('focus');$('#focus-toggle').textContent=on?'退出演示':'演示模式';$('#focus-toggle').setAttribute('aria-pressed',String(on));};
async function fullscreen(){try{if(document.fullscreenElement)await document.exitFullscreen();else await $('#demo-board').requestFullscreen();}catch(e){toast('可点击「演示模式」放大画面，或按浏览器 F11。');}}
$('#fullscreen').onclick=fullscreen;document.addEventListener('fullscreenchange',()=>$('#fullscreen').textContent=document.fullscreenElement?'退出全屏 ⛶':'全屏 ⛶');
$('#about-open').onclick=()=>$('#about').showModal();$('#about-close').onclick=()=>$('#about').close();$('#about').onclick=e=>{if(e.target===$('#about')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close();}};
window.addEventListener('message',e=>{if(e.source!==$('#interactive-frame').contentWindow)return;if(e.data?.type==='lunar-ready'){frameReady=true;sendFrame();}});
document.addEventListener('keydown',e=>{if(/^(INPUT|SELECT|TEXTAREA)$/.test(e.target.tagName)||$('#about').open||e.ctrlKey||e.metaKey||e.altKey)return;
 if(/^[1-7]$/.test(e.key)){e.preventDefault();setScene(D.scenes[+e.key-1].id);}else if(['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();const n=D.scenes.findIndex(s=>s.id===state.scene);setScene(D.scenes[(n+(e.key==='ArrowRight'?1:6))%7].id);}else if(e.key.toLowerCase()==='c'){e.preventDefault();setMode(state.mode==='compare'?'render':'compare');}else if(e.key.toLowerCase()==='f'){e.preventDefault();fullscreen();}
});
window.LUNAR_DEMO={state,render,setScene,setMode,get frameReady(){return frameReady;}};
render();
})();
