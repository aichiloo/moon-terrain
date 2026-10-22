from pathlib import Path
import json
import shutil
import numpy as np
from audit_rille_seating import ROOT,BASE,readjs,dec,Surface,vertices

path=ROOT/'data/rille.js'
(BASE/'build').mkdir(parents=True,exist_ok=True)
backup=BASE/'build/rille_before_fix.js'
if not backup.exists():shutil.copy2(path,backup)
for suffix in ['A','B','C','D','detail','orbit','high']:
    dst=BASE/'build'/f'rille_before_{suffix}.jpg'
    if not dst.exists():shutil.copy2(ROOT/'images'/f'rille_{suffix}.jpg',dst)
d=readjs(backup);assets=readjs(ROOT/'shared/assets.js');surface=Surface(d)

def underside_samples(v,t,lod):
    """Uniform horizontal sampling of the mesh's lower envelope, not vertex density."""
    src=t['pilot_lod'] if lod else t
    idx=np.asarray(src.get('indices',np.arange(len(v))),int).reshape(-1,3)
    lo,hi=v[:,:2].min(axis=0),v[:,:2].max(axis=0)
    xx,yy=np.meshgrid(np.linspace(lo[0],hi[0],19),np.linspace(lo[1],hi[1],19))
    xy=np.stack([xx.ravel(),yy.ravel()],axis=1);z=np.full(len(xy),np.inf)
    for tri in v[idx]:
        a,b,c=tri
        den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(den)<1e-12:continue
        selected=np.where((xy[:,0]>=min(tri[:,0]))&(xy[:,0]<=max(tri[:,0]))&(xy[:,1]>=min(tri[:,1]))&(xy[:,1]<=max(tri[:,1])))[0]
        p=xy[selected]
        u=((b[1]-c[1])*(p[:,0]-c[0])+(c[0]-b[0])*(p[:,1]-c[1]))/den
        w=((c[1]-a[1])*(p[:,0]-c[0])+(a[0]-c[0])*(p[:,1]-c[1]))/den
        valid=(u>=-1e-8)&(w>=-1e-8)&(u+w<=1+1e-8)
        selected=selected[valid];zz=u[valid]*a[2]+w[valid]*b[2]+(1-u[valid]-w[valid])*c[2]
        z[selected]=np.minimum(z[selected],zz)
    good=np.isfinite(z)
    return np.column_stack([xy[good],z[good]])

changes=[]
for group,records in [('existing',d['existing_rocks']),('approved_gravel',d['approved_gravel']),*d['layouts'].items()]:
    for i,r in enumerate(records):
        lod=group in ['uniform','clustered'] and r.get('width_m',1)<.08
        v=vertices(assets,r,lod)
        mat=np.array(r['matrix']).reshape((4,4),order='F');linear=v@mat[:3,:3].T
        xy=mat[:2,3];height=float(np.ptp(linear[:,2]));width=float(np.ptp(linear[:,:2],axis=0).max())
        footprint=underside_samples(linear,assets['rockTypes'][r['type']],lod) if width>=.15 else None
        variants=[];burial=max(height*(.15 if width>=.15 else .12),.00025)
        for displaced in [False,True]:
            grounds=surface(linear[:,0]+xy[0],linear[:,1]+xy[1],displaced)
            z_contact=float(np.max(grounds-linear[:,2]))
            if footprint is not None and len(footprint):
                under=footprint[:,2]+z_contact-surface(footprint[:,0]+xy[0],footprint[:,1]+xy[1],displaced)
                burial=max(burial,float(np.quantile(under,.22)))
            variants.append((z_contact,grounds))
        # Preserve a visible rock body while embedding enough of its underside.
        burial=min(burial,height*.35)
        coverage=[];shifts=[]
        for displaced,(z_contact,grounds) in zip([False,True],variants):
            key='displaced_matrix' if displaced else 'matrix';m=np.array(r[key]).reshape((4,4),order='F')
            oldz=float(m[2,3]);m[2,3]=z_contact-burial;r[key]=m.T.ravel().tolist();shifts.append(float(m[2,3]-oldz))
            if footprint is not None and len(footprint):
                gap=footprint[:,2]+m[2,3]-surface(footprint[:,0]+xy[0],footprint[:,1]+xy[1],displaced)
                coverage.append(float(np.mean(gap<=.0001)))
        r['buried_fraction']=burial/max(height,1e-12)
        r['seating_revision']={'method':'actual displayed far/context/detail triangles; vertical correction with partly embedded underside','burial_depth_m':burial,'xy_and_orientation_preserved':True,'underside_sample_count':0 if footprint is None else len(footprint),'underside_embedded_fraction_base_displaced':coverage}
        if 'min_ground_clearance_m' in r:r['min_ground_clearance_m']=-burial
        changes.append({'group':group,'index':i,'width_m':width,'height_m':height,'z_change_base_displaced_m':shifts,'burial_depth_m':burial,'underside_embedded_fraction_base_displaced':coverage})
    print(json.dumps({'reseated':group,'count':len(records)}),flush=True)
d['seating_revision']={'version':2,'corrected_groups':['existing','approved_gravel','uniform','clustered'],'terrain_changed':False,'rock_xy_or_orientation_changed':False,'minimum_burial_fraction':.12,'large_rock_underside_target_fraction':.22}
for name,records in d['layouts'].items():
    d['layout_stats'][name]['partial_burial_count']=len(records)
    d['layout_stats'][name]['seating_method']='all stones partly embedded; checked against actual displayed triangles'
path.write_text('window.PILOT_REGIONS.rille='+json.dumps(d,ensure_ascii=False,separators=(',',':'))+';',encoding='utf-8')
instances={'coordinate_system':'source local XYZ, Z up, metres','matrix_order':'column-major','existing_rocks':d['existing_rocks'],'approved_gravel':d['approved_gravel'],**d['layouts'],'seating_revision':d['seating_revision']}
(ROOT/'exports/rille_rock_instances.json').write_text(json.dumps(instances,ensure_ascii=False,indent=2),encoding='utf-8')
meta=json.loads((ROOT/'exports/rille_metadata.json').read_text(encoding='utf-8'));meta['seating_revision']=d['seating_revision'];meta['layouts']=d['layout_stats']
(ROOT/'exports/rille_metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
manifest['revision']='02: rille stones reseated on the displayed surface, including inherited rocks and gravel'
for r in manifest['regions']:
    if r['key']=='rille':r.update(meta)
(ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(BASE/'build/rille_seating_changes.json').write_text(json.dumps(changes,indent=2),encoding='utf-8')
print('RILLE_ALL_STONES_RESEATED')
