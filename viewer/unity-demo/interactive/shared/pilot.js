'use strict';
const A=window.REGION_ASSETS,all=window.PILOT_REGIONS,host=document.getElementById('view');
function floats(s){const b=atob(s),a=new Uint8Array(b.length);for(let i=0;i<b.length;i++)a[i]=b.charCodeAt(i);return new Float32Array(a.buffer);}
const scene=new THREE.Scene();scene.background=new THREE.Color(0);
const renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});renderer.setPixelRatio(Math.min(devicePixelRatio,1.35));renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.12;renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;host.prepend(renderer.domElement);
const camera=new THREE.PerspectiveCamera(66,1,.025,30000);camera.up.set(0,0,1);
scene.add(new THREE.AmbientLight(0xffffff,.035));
const sun=new THREE.DirectionalLight(0xfffcf5,3.5);sun.castShadow=true;sun.shadow.mapSize.set(4096,4096);sun.shadow.camera.near=1500;sun.shadow.camera.far=8500;sun.shadow.bias=-.000001;sun.shadow.normalBias=.001;scene.add(sun,sun.target);
let loaded=0,expected=0,failed=[],ready=false,dirty=true,region='plain',preset='D',view='low',normalOn=true,geometryOn=true,layout='clustered',rocksOn=true,yaw=all.plain.yaw,pitch=all.plain.pitch,fov=66,orbitYaw=2.35,orbitElev=.8,distance=15,drag=null;
const loader=new THREE.TextureLoader();
function tex(url,color=false,flip=true){expected++;const t=loader.load(url,()=>{loaded++;dirty=true;},undefined,e=>{failed.push(String(e));console.error('Texture loading failed',e);});t.colorSpace=color?THREE.SRGBColorSpace:THREE.NoColorSpace;t.flipY=flip;t.anisotropy=Math.min(16,renderer.capabilities.getMaxAnisotropy());return t;}
const reg=Object.fromEntries(Object.entries(all).map(([key,d])=>[key,{...d,raw:floats(d.native.z),base:floats(d.field.base),low:floats(d.field.low),coarse:floats(d.context.heights),normalFull:tex(d.field.normal_full),normalFine:tex(d.field.normal_fine)}]));
const r1=A.regolith.moon_01,r2=A.regolith.moon_02;
const scan1=tex(r1.Diffuse,true),scan2=tex(r2.Diffuse,true),norm1=tex(r1.nor_gl),norm2=tex(r2.nor_gl),ao1=tex(r1.AO),ao2=tex(r2.AO);
for(const t of [scan1,scan2,norm1,norm2,ao1,ao2])t.wrapS=t.wrapT=THREE.RepeatWrapping;
const detailUniforms={pilotMap:{value:reg.plain.normalFine},pilotCenter:{value:new THREE.Vector2(...reg.plain.focus)},pilotWidth:{value:12},pilotStrength:{value:1},pilotEnabled:{value:1}};
const groundMaterial=new THREE.MeshStandardMaterial({color:0x959590,roughness:1,normalMap:norm1});
groundMaterial.onBeforeCompile=s=>{
 Object.assign(s.uniforms,{scan1:{value:scan1},scan2:{value:scan2},norm1:{value:norm1},norm2:{value:norm2},ao1:{value:ao1},ao2:{value:ao2}},detailUniforms);
 s.vertexShader='varying vec3 worldGround;\n'+s.vertexShader;
 s.vertexShader=s.vertexShader.replace('#include <worldpos_vertex>','#include <worldpos_vertex>\nworldGround=(modelMatrix*vec4(transformed,1.0)).xyz;');
 s.fragmentShader='varying vec3 worldGround;uniform sampler2D scan1;uniform sampler2D scan2;uniform sampler2D norm1;uniform sampler2D norm2;uniform sampler2D ao1;uniform sampler2D ao2;uniform sampler2D pilotMap;uniform vec2 pilotCenter;uniform float pilotWidth;uniform float pilotStrength;uniform float pilotEnabled;\n'+s.fragmentShader;
 s.fragmentShader=s.fragmentShader.replace('#include <map_fragment>','#include <map_fragment>\nvec2 suv=worldGround.xy/3.1;float blendWeight=.32+.19*sin(worldGround.x*.37+worldGround.y*.23)*cos(worldGround.y*.29-worldGround.x*.17);float scanFade=1.0-smoothstep(12.0,50.0,length(vViewPosition));vec3 scanned=mix(texture2D(scan1,suv).rgb,texture2D(scan2,suv).rgb,blendWeight);float scanGray=dot(scanned,vec3(.333333));float occ=mix(texture2D(ao1,suv).r,texture2D(ao2,suv).r,blendWeight);float gain=clamp(pow(max(scanGray,.001)/.19,.5),.48,1.65);diffuseColor.rgb*=mix(1.0,gain*mix(.66,1.0,occ),scanFade);');
 s.fragmentShader=s.fragmentShader.replace('#include <normal_fragment_maps>',`vec3 detailNormal=mix(texture2D(norm1,suv).xyz,texture2D(norm2,suv).xyz,blendWeight)*2.0-1.0;mat3 tangentFrame=getTangentFrame(-vViewPosition,normal,suv);detailNormal.xy*=.65;normal=normalize(mix(normal,tangentFrame*normalize(detailNormal),scanFade*.65));
 vec2 puv=(worldGround.xy-pilotCenter)/pilotWidth+.5;float pmask=step(0.0,puv.x)*step(puv.x,1.0)*step(0.0,puv.y)*step(puv.y,1.0)*pilotEnabled;
 vec3 pn=texture2D(pilotMap,clamp(puv,0.0,1.0)).xyz*2.0-1.0;pn.xy*=pilotStrength;
 mat3 pf=getTangentFrame(-vViewPosition,normal,worldGround.xy/pilotWidth);normal=normalize(mix(normal,pf*normalize(pn),pmask));`);
};
function geometry(n,width,center,height,hole){
 const p=new Float32Array(n*n*3),uv=new Float32Array(n*n*2),indices=[];const step=width/(n-1);
 for(let r=0;r<n;r++)for(let c=0;c<n;c++){const j=r*n+c,x=center[0]-width/2+c*step,y=center[1]+width/2-r*step;p.set([x,y,height[j]],j*3);uv.set([c/(n-1),1-r/(n-1)],j*2);}
 for(let r=0;r<n-1;r++)for(let c=0;c<n-1;c++){const x=center[0]-width/2+(c+.5)*step,y=center[1]+width/2-(r+.5)*step;if(hole&&Math.abs(x-hole.center[0])<hole.half-1e-7&&Math.abs(y-hole.center[1])<hole.half-1e-7)continue;const j=r*n+c;indices.push(j,j+n,j+1,j+1,j+n,j+n+1);}
 const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(p,3));g.setAttribute('uv',new THREE.BufferAttribute(uv,2));g.setIndex(indices);g.computeVertexNormals();g.computeBoundingSphere();return g;
}
const rockGeos=[],rockMats=[];
A.rockTypes.forEach((t,i)=>{
 const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(floats(t.positions),3));g.setAttribute('uv',new THREE.BufferAttribute(floats(t.uv),2));if(t.indices)g.setIndex(t.indices);if(t.new_normals)g.setAttribute('normal',new THREE.BufferAttribute(floats(t.new_normals),3));else if(t.normals)g.setAttribute('normal',new THREE.BufferAttribute(floats(t.normals),3));else g.computeVertexNormals();
 let lod=g;if(t.pilot_lod){lod=new THREE.BufferGeometry();const p=floats(t.pilot_lod.positions),uv=new Float32Array(p.length/3*2);for(let j=0;j<p.length/3;j++){uv[j*2]=p[j*3]*2;uv[j*2+1]=p[j*3+1]*2;}lod.setAttribute('position',new THREE.BufferAttribute(p,3));lod.setAttribute('uv',new THREE.BufferAttribute(uv,2));lod.setIndex(t.pilot_lod.indices);lod.computeVertexNormals();}
 rockGeos.push({full:g,lod});
 const options={map:tex(t.diffuse,true,!!t.apollo),roughness:1,metalness:0,color:t.apollo?0xb5b4b0:0xbab8b0};if(t.normal){options.normalMap=tex(t.normal,false,false);options.normalScale=new THREE.Vector2(.6,.6);}if(t.arm)options.roughnessMap=tex(t.arm,false,false);
 const mat=new THREE.MeshStandardMaterial(options);mat.onBeforeCompile=s=>{
  s.uniforms.sourceMean={value:Math.max(.003,t.linearMean)};
  s.vertexShader='varying float dustUp;\n'+s.vertexShader;s.vertexShader=s.vertexShader.replace('#include <beginnormal_vertex>','#include <beginnormal_vertex>\ndustUp=clamp(objectNormal.z,0.0,1.0);');
  s.fragmentShader='varying float dustUp;uniform float sourceMean;\n'+s.fragmentShader;
  s.fragmentShader=s.fragmentShader.replace('#include <map_fragment>',`#include <map_fragment>\nvec3 source=texture2D(map,vMapUv).rgb;float lum=dot(source,vec3(.2126,.7152,.0722));float gain=clamp(pow(max(lum,.002)/sourceMean,.62),.48,1.6);vec3 subtleColor=mix(vec3(1.0),source/max(lum,.003),.10);vec3 rock=vec3(.180,.176,.166)*gain*subtleColor;float dust=.22*smoothstep(.1,.85,dustUp);diffuseColor.rgb=mix(rock,vec3(.190,.186,.174)*(.8+.2*gain),dust);`);
  s.fragmentShader=s.fragmentShader.replace('#include <roughnessmap_fragment>','#include <roughnessmap_fragment>\nroughnessFactor=.98;');
 };rockMats.push(mat);
});
let rootGroup=null,detailMesh=null,sets={},meshes=[];
function instances(name,values,lod=false){const group=new THREE.Group();rootGroup.add(group);sets[name]=group;for(let i=0;i<A.rockTypes.length;i++){
 const rs=values.filter(r=>r.type===i);if(!rs.length)continue;
 for(const small of [false,true]){const list=rs.filter(r=>Boolean(lod&&r.width_m<.08)===small);if(!list.length)continue;const mesh=new THREE.InstancedMesh(small?rockGeos[i].lod:rockGeos[i].full,rockMats[i],list.length);mesh.userData.records=list;list.forEach((r,j)=>mesh.setMatrixAt(j,new THREE.Matrix4().fromArray(geometryOn?r.displaced_matrix:r.matrix)));mesh.castShadow=true;mesh.receiveShadow=true;mesh.frustumCulled=false;group.add(mesh);meshes.push(mesh);}
}}
function rebuild(){if(rootGroup){scene.remove(rootGroup);rootGroup.traverse(o=>{if(o.isMesh&&!o.isInstancedMesh)o.geometry.dispose();});}rootGroup=new THREE.Group();scene.add(rootGroup);sets={};meshes=[];const d=reg[region];
 const stride=Math.max(1,d.native.display_stride||1),fn=(d.native.n-1)/stride+1,fh=new Float32Array(fn*fn);
 for(let r=0;r<fn;r++)for(let c=0;c<fn;c++)fh[r*fn+c]=d.raw[r*stride*d.native.n+c*stride];
 const far=new THREE.Mesh(geometry(fn,d.native.width,[0,0],fh,{center:d.origin,half:d.context.width_m/2}),groundMaterial);far.castShadow=true;far.receiveShadow=true;rootGroup.add(far);
 const mid=new THREE.Mesh(geometry(d.context.n,d.context.width_m,d.origin,d.coarse,{center:d.focus,half:6}),groundMaterial);mid.castShadow=true;mid.receiveShadow=true;rootGroup.add(mid);
 detailMesh=new THREE.Mesh(geometry(d.field.n,12,d.focus,d.base),groundMaterial);detailMesh.castShadow=true;detailMesh.receiveShadow=true;rootGroup.add(detailMesh);
 instances('existing',d.existing_rocks);
 const inside=r=>Math.abs(r.matrix[12]-d.focus[0])<6&&Math.abs(r.matrix[13]-d.focus[1])<6;
 instances('outside',d.approved_gravel.filter(r=>!inside(r)));instances('approved',d.approved_gravel.filter(inside));instances('uniform',d.layouts.uniform,true);instances('clustered',d.layouts.clustered,true);
 detailUniforms.pilotCenter.value.set(...d.focus);update();
}
function update(){const d=reg[region],p=detailMesh.geometry.attributes.position;for(let i=0;i<d.base.length;i++)p.array[i*3+2]=d.base[i]+(geometryOn?d.low[i]:0);p.needsUpdate=true;detailMesh.geometry.computeVertexNormals();detailMesh.geometry.computeBoundingSphere();
 detailUniforms.pilotMap.value=geometryOn?d.normalFine:d.normalFull;detailUniforms.pilotEnabled.value=normalOn?1:0;detailUniforms.pilotStrength.value=+document.getElementById('strength').value/100;
 for(const mesh of meshes){mesh.userData.records.forEach((r,j)=>mesh.setMatrixAt(j,new THREE.Matrix4().fromArray(geometryOn?r.displaced_matrix:r.matrix)));mesh.instanceMatrix.needsUpdate=true;}
 for(const [name,group]of Object.entries(sets))group.visible=rocksOn&&(name==='existing'||name==='outside'||name===layout);
 document.getElementById('normal').checked=normalOn;document.getElementById('geometry').checked=geometryOn;document.getElementById('layout').value=layout;document.getElementById('rocks').checked=rocksOn;
 document.getElementById('region-label').textContent=d.label;document.getElementById('mode-label').textContent=preset==='custom'?'自定义对照':({A:'A · 原认可版',B:'B · 法线细节',C:'C · 真实凸起',D:'D · 组合样板'})[preset];
 document.querySelectorAll('[data-preset]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.preset===preset)));document.querySelectorAll('[data-region]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.region===region)));
 document.getElementById('strength-label').textContent=document.getElementById('strength').value+'%';
 document.getElementById('layout-note').textContent=layout==='approved'?'保留原有岩块与细碎石的位置。':`局部新布局 ${d.layouts[layout].length} 块：细碎石 740、中小石 66、较大岩块 5。`;
 dirty=true;
}
function setPreset(p){preset=p;normalOn=p==='B'||p==='D';geometryOn=p==='C'||p==='D';layout=p==='D'?'clustered':'approved';rocksOn=true;document.getElementById('strength').value=100;update();render();}
function setRegion(key){region=key;yaw=reg[key].yaw;pitch=reg[key].pitch;fov=66;orbitYaw=2.35;orbitElev=.8;distance=15;rebuild();sunUpdate();render();}
function setView(v){view=v;yaw=reg[region].yaw;pitch=reg[region].pitch;fov=66;orbitYaw=2.35;orbitElev=.8;distance=15;document.querySelectorAll('[data-view]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.view===v)));document.getElementById('view-label').textContent=({low:'0.55 米近地视角',high:'1.6 米观察视角',detail:'局部细节近看',orbit:'局部区域全貌'})[v];sunUpdate();render();}
function cameraUpdate(){const d=reg[region];if(view==='overview'){const h=d.native.meta,mid=d.coarse[Math.floor(d.coarse.length/2)],target=new THREE.Vector3(0,0,mid);camera.position.copy(target).add(new THREE.Vector3(Math.cos(orbitYaw)*Math.cos(orbitElev),Math.sin(orbitYaw)*Math.cos(orbitElev),Math.sin(orbitElev)).multiplyScalar(d.native.width*1.35));camera.lookAt(target);camera.fov=52;}else if(view==='orbit'){const mid=d.base[Math.floor(d.field.n/2)*d.field.n+Math.floor(d.field.n/2)],target=new THREE.Vector3(...d.focus,mid);camera.position.copy(target).add(new THREE.Vector3(Math.cos(orbitYaw)*Math.cos(orbitElev),Math.sin(orbitYaw)*Math.cos(orbitElev),Math.sin(orbitElev)).multiplyScalar(distance));camera.lookAt(target);camera.fov=52;}else{
 let xy=d.origin,z=d.base_camera_height+(view==='high'?1.6:.55),pa=pitch-(view==='high'?.07:0);
 if(view==='detail'){const target=d.detail_target;xy=[target[0]-.6*Math.cos(d.yaw),target[1]-.6*Math.sin(d.yaw)];z=baseAt(xy[0],xy[1])+.35;pa=Math.atan2(baseAt(...target)-z,.6)+(pitch-d.pitch);}
 camera.position.set(xy[0],xy[1],z);camera.lookAt(xy[0]+15*Math.cos(yaw)*Math.cos(pa),xy[1]+15*Math.sin(yaw)*Math.cos(pa),z+15*Math.sin(pa));camera.fov=fov;
 }camera.updateProjectionMatrix();}
function baseAt(x,y){const d=reg[region],n=d.field.n;let c=Math.max(0,Math.min(n-1.00001,(x-d.focus[0]+6)/.02)),r=Math.max(0,Math.min(n-1.00001,(d.focus[1]+6-y)/.02)),ci=Math.floor(c),ri=Math.floor(r),u=c-ci,v=r-ri;return (1-v)*((1-u)*d.base[ri*n+ci]+u*d.base[ri*n+ci+1])+v*((1-u)*d.base[(ri+1)*n+ci]+u*d.base[(ri+1)*n+ci+1]);}
function sunUpdate(){const alt=+document.getElementById('sunalt').value,az=+document.getElementById('sunaz').value,a=alt*Math.PI/180,b=az*Math.PI/180,d=reg[region];document.getElementById('alt-label').textContent=alt+'°';document.getElementById('az-label').textContent=az+'°';const target=new THREE.Vector3(...d.focus,baseAt(...d.focus));sun.target.position.copy(target);sun.position.copy(target).add(new THREE.Vector3(Math.cos(b)*Math.cos(a),Math.sin(b)*Math.cos(a),Math.sin(a)).multiplyScalar(5000));if(view==='overview'){sun.target.position.set(0,0,d.coarse[Math.floor(d.coarse.length/2)]);sun.position.copy(sun.target.position).add(new THREE.Vector3(Math.cos(b)*Math.cos(a),Math.sin(b)*Math.cos(a),Math.sin(a)).multiplyScalar(5000));}const w=view==='overview'?d.native.width*.7:(view==='orbit'?28:19);Object.assign(sun.shadow.camera,{left:-w,right:w,top:w,bottom:-w});sun.shadow.camera.updateProjectionMatrix();dirty=true;}
function render(){cameraUpdate();drawTextureTrial();dirty=false;}
function resize(){const w=Math.max(1,host.clientWidth),h=Math.max(1,host.clientHeight);renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();dirty=true;}
document.querySelectorAll('[data-region]').forEach(b=>b.onclick=()=>setRegion(b.dataset.region));document.querySelectorAll('[data-preset]').forEach(b=>b.onclick=()=>setPreset(b.dataset.preset));document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>setView(b.dataset.view));
function change(){preset='custom';normalOn=document.getElementById('normal').checked;geometryOn=document.getElementById('geometry').checked;layout=document.getElementById('layout').value;rocksOn=document.getElementById('rocks').checked;update();render();}
for(const id of ['normal','geometry','layout','rocks'])document.getElementById(id).onchange=change;document.getElementById('strength').oninput=change;document.getElementById('sunalt').oninput=sunUpdate;document.getElementById('sunaz').oninput=sunUpdate;
document.getElementById('reset').onclick=()=>{document.getElementById('sunalt').value=25;document.getElementById('sunaz').value=135;setView('low');};
renderer.domElement.addEventListener('pointerdown',e=>{drag=[e.clientX,e.clientY];renderer.domElement.setPointerCapture(e.pointerId);});renderer.domElement.addEventListener('pointerup',()=>drag=null);renderer.domElement.addEventListener('pointercancel',()=>drag=null);renderer.domElement.addEventListener('pointermove',e=>{if(!drag)return;const dx=e.clientX-drag[0],dy=e.clientY-drag[1];if(view==='orbit'||view==='overview'){orbitYaw-=dx*.006;orbitElev=Math.max(.15,Math.min(1.45,orbitElev+dy*.005));}else{yaw-=dx*.004;pitch=Math.max(-1.1,Math.min(.5,pitch+dy*.004));}drag=[e.clientX,e.clientY];dirty=true;});renderer.domElement.addEventListener('wheel',e=>{e.preventDefault();if(view==='overview'){orbitElev=Math.max(.15,Math.min(1.45,orbitElev+e.deltaY*.0005));}else if(view==='orbit')distance=Math.max(6,Math.min(50,distance*Math.exp(e.deltaY*.001)));else fov=Math.max(28,Math.min(90,fov+e.deltaY*.035));dirty=true;},{passive:false});window.addEventListener('resize',resize);
// Reuse the established geometry, rocks, camera, and lights. Only ground shading changes.
const trialConfig=window.TEXTURE_CONFIG,trialMaps={};
for(const [id,c] of Object.entries(trialConfig)){
 trialMaps[id]={};for(const key of ['diff','normal','rough','ao']){const t=tex(c[key],key==='diff');t.wrapS=t.wrapT=THREE.RepeatWrapping;trialMaps[id][key]=t;}
}
const replacement=new THREE.MeshStandardMaterial({color:0xffffff,roughness:1,metalness:0,normalMap:trialMaps.moon_01.normal});
const tu={baseColor:{value:trialMaps.moon_01.diff},baseNormal:{value:trialMaps.moon_01.normal},baseAO:{value:trialMaps.moon_01.ao},baseRough:{value:trialMaps.moon_01.rough},tileWidth:{value:3.1},mixOn:{value:1},textureStrength:{value:.65},tileScale:{value:1},fineColor:{value:trialMaps.moon_flat_macro_01.diff},fineNormal:{value:trialMaps.moon_flat_macro_01.normal},fineRough:{value:trialMaps.moon_flat_macro_01.rough},fineAO:{value:trialMaps.moon_flat_macro_01.ao},dustColor:{value:trialMaps.moon_dusted_01.diff},dustNormal:{value:trialMaps.moon_dusted_01.normal},dustRough:{value:trialMaps.moon_dusted_01.rough},dustAO:{value:trialMaps.moon_dusted_01.ao}};
replacement.onBeforeCompile=s=>{
 Object.assign(s.uniforms,tu);
 s.vertexShader='varying vec3 trialWorld;\n'+s.vertexShader;
 s.vertexShader=s.vertexShader.replace('#include <worldpos_vertex>','#include <worldpos_vertex>\ntrialWorld=(modelMatrix*vec4(transformed,1.0)).xyz;');
 s.fragmentShader='varying vec3 trialWorld;uniform sampler2D baseColor,baseNormal,baseAO,baseRough,fineColor,fineNormal,fineRough,fineAO,dustColor,dustNormal,dustRough,dustAO;uniform float tileWidth,mixOn,textureStrength,tileScale;\n'+s.fragmentShader;
 s.fragmentShader=s.fragmentShader.replace('#include <map_fragment>',`#include <map_fragment>
 vec2 mainUV=trialWorld.xy/(tileWidth*tileScale);vec2 fineUV=trialWorld.xy/(.4*tileScale);
 float dustWeight=mixOn*(.08+.13*smoothstep(-.35,.55,sin(trialWorld.x*.37+trialWorld.y*.23)*cos(trialWorld.y*.29)));
 float fineFade=1.0-smoothstep(2.5,12.0,length(vViewPosition));
 vec3 tint=texture2D(baseColor,mainUV).rgb;
 tint=mix(tint,texture2D(dustColor,fineUV).rgb,dustWeight);
 // Fine texture changes local grain contrast without replacing base-layer mean brightness.
 float fineGray=dot(texture2D(fineColor,fineUV).rgb,vec3(.2126,.7152,.0722));
 tint*=mix(1.0,clamp(sqrt(max(fineGray,.002)/.10),.72,1.28),mixOn*fineFade*.22);
 float occ=mix(texture2D(baseAO,mainUV).r,texture2D(dustAO,fineUV).r,dustWeight);
 diffuseColor.rgb*=tint*mix(.72,1.0,occ);`);
 s.fragmentShader=s.fragmentShader.replace('#include <roughnessmap_fragment>',`#include <roughnessmap_fragment>
 roughnessFactor=clamp(mix(texture2D(baseRough,mainUV).r,texture2D(dustRough,fineUV).r,dustWeight),.12,1.0);`);
 s.fragmentShader=s.fragmentShader.replace('#include <normal_fragment_maps>',`
 vec3 tn=texture2D(baseNormal,mainUV).xyz*2.0-1.0;
 tn=normalize(mix(tn,texture2D(dustNormal,fineUV).xyz*2.0-1.0,dustWeight));
 vec3 fn=texture2D(fineNormal,fineUV).xyz*2.0-1.0;
 tn=normalize(vec3(tn.xy+fn.xy*mixOn*fineFade*.3,tn.z));
 tn.xy*=textureStrength*(1.0-smoothstep(15.0,65.0,length(vViewPosition)));
 normal=normalize(getTangentFrame(-vViewPosition,normal,mainUV)*normalize(tn));`);
};
let trialMaterial='mixed',trialMode='new',trialSplit=.5;
function assignGround(mat){rootGroup?.traverse(o=>{if(o.isMesh&&(o.material===groundMaterial||o.material===replacement))o.material=mat;});}
function drawTextureTrial(){
 const w=renderer.domElement.width,h=renderer.domElement.height,ratio=renderer.getPixelRatio();
 renderer.setScissorTest(false);
 if(trialMode==='split'&&trialMaterial!=='original'){
  renderer.setScissorTest(true);renderer.setScissor(0,0,w*trialSplit/ratio,h/ratio);assignGround(groundMaterial);renderer.render(scene,camera);
  renderer.setScissor(w*trialSplit/ratio,0,w*(1-trialSplit)/ratio,h/ratio);assignGround(replacement);renderer.render(scene,camera);renderer.setScissorTest(false);
 }else{assignGround(trialMode==='original'||trialMaterial==='original'?groundMaterial:replacement);renderer.render(scene,camera);}
}
function setTrialMaterial(id){
 trialMaterial=id;const c=trialConfig[id==='mixed'||id==='original'?'moon_01':id],m=trialMaps[c.id];
 for(const [key,uniform]of [['diff','baseColor'],['normal','baseNormal'],['ao','baseAO'],['rough','baseRough']])tu[uniform].value=m[key];
 tu.tileWidth.value=c.width_m;tu.mixOn.value=id==='mixed'?1:0;
 document.querySelectorAll('[data-material]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.material===id)));
 document.getElementById('selected-name').textContent=id==='mixed'?'混合试用':id==='original'?'原有贴图':id.replaceAll('_',' ').toUpperCase();
 document.getElementById('scale-note').textContent=id==='mixed'?'基础 3.1 m · 细节与覆尘 0.4 m':id==='original'?'沿用原展示材质':`每次平铺 ${c.width_m} m`;
 dirty=true;
}
function trialState(){return {material:trialMaterial,mode:trialMode,split:trialSplit,scale:tu.tileScale.value,normalStrength:tu.textureStrength.value,position:camera.position.toArray(),quaternion:camera.quaternion.toArray(),textureWidth:tu.tileWidth.value,groundGeometry:detailMesh.geometry.attributes.position.count};}

window.TEXTURE_TRIAL={setMaterial:setTrialMaterial,get state(){return trialState();},config:trialConfig};
setTrialMaterial('mixed');

window.PILOT={setPreset,setRegion,setView,render,renderer,camera,scene,get loaded(){return ready&&loaded===expected&&!failed.length;},get textures(){return{loaded,expected,failed};},get state(){return{region,preset,view,normalOn,geometryOn,layout,rocksOn,camera:camera.position.toArray(),quaternion:camera.quaternion.toArray(),fov:camera.fov,sun:[+document.getElementById('sunalt').value,+document.getElementById('sunaz').value],detailVertices:detailMesh.geometry.attributes.position.count};},get detailGeometry(){return detailMesh.geometry;}};
resize();rebuild();if(reg[location.hash.slice(1)])setRegion(location.hash.slice(1));sunUpdate();render();ready=true;
function loop(){requestAnimationFrame(loop);if(dirty)render();if(ready&&loaded===expected&&!failed.length)document.getElementById('loading').style.display='none';}loop();
