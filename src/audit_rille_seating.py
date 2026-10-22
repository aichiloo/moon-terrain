from pathlib import Path
import base64
import json
import numpy as np

from pipeline_config import BASE, OUTPUT
ROOT=OUTPUT
def readjs(p):return json.loads(p.read_text(encoding='utf-8').split('=',1)[1].rstrip(';\r\n'))
def dec(s):return np.frombuffer(base64.b64decode(s),dtype='<f4').astype(float)

class Surface:
    def __init__(self,d):
        self.d=d
        self.raw=dec(d['native']['z']).reshape(d['native']['n'],-1)[::d['native'].get('display_stride',1),::d['native'].get('display_stride',1)]
        self.context=dec(d['context']['heights']).reshape(d['context']['n'],-1)
        self.base=dec(d['field']['base']).reshape(d['field']['n'],-1)
        self.low=dec(d['field']['low']).reshape(d['field']['n'],-1)
    def tri(self,a,x,y,center,width):
        n=len(a);step=width/(n-1)
        c=np.clip((x-center[0]+width/2)/step,0,n-1.0000001)
        r=np.clip((center[1]+width/2-y)/step,0,n-1.0000001)
        ci,ri=np.floor(c).astype(int),np.floor(r).astype(int);u,v=c-ci,r-ri
        h00,h01,h10,h11=a[ri,ci],a[ri,ci+1],a[ri+1,ci],a[ri+1,ci+1]
        return np.where(u+v<=1,h00+u*(h01-h00)+v*(h10-h00),h11+(1-u)*(h10-h11)+(1-v)*(h01-h11))
    def __call__(self,x,y,displaced=False):
        x,y=np.broadcast_arrays(x,y);d=self.d
        h=self.tri(self.raw,x,y,[0,0],d['native']['width'])
        inside=(abs(x-d['origin'][0])<=d['context']['width_m']/2)&(abs(y-d['origin'][1])<=d['context']['width_m']/2)
        h=np.where(inside,self.tri(self.context,x,y,d['origin'],d['context']['width_m']),h)
        inside=(abs(x-d['focus'][0])<=6)&(abs(y-d['focus'][1])<=6)
        patch=(self.base+self.low).astype('f4').astype(float) if displaced else self.base
        return np.where(inside,self.tri(patch,x,y,d['focus'],12),h)

def vertices(assets,r,lod=False):
    t=assets['rockTypes'][r['type']]
    return dec(t['pilot_lod']['positions'] if lod and r.get('width_m',1)<.08 and t.get('pilot_lod') else t['positions']).reshape(-1,3)

def audit(d,assets):
    surface=Surface(d);rows=[]
    for group,records in [('existing',d['existing_rocks']),('approved_gravel',d['approved_gravel']),*d['layouts'].items()]:
        for i,r in enumerate(records):
            v=vertices(assets,r,group in ['uniform','clustered'])
            for displaced in [False,True]:
                m=np.array(r['displaced_matrix'] if displaced else r['matrix']).reshape((4,4),order='F')
                p=v@m[:3,:3].T+m[:3,3];ground=surface(p[:,0],p[:,1],displaced)
                clearance=p[:,2]-ground
                rows.append({'group':group,'index':i,'displaced':displaced,'type':r['type'],'width_m':float(np.ptp(p[:,:2],axis=0).max()),'min_vertex_clearance_m':float(clearance.min()),'q10_vertex_clearance_m':float(np.quantile(clearance,.1)),'q25_vertex_clearance_m':float(np.quantile(clearance,.25)),'height_m':float(np.ptp(p[:,2])),'xy':m[:2,3].tolist()})
    summary=[]
    for group in ['existing','approved_gravel','uniform','clustered']:
        selected=[r for r in rows if r['group']==group and r['displaced']]
        summary.append({'group':group,'count':len(selected),'fully_above_1cm':sum(r['min_vertex_clearance_m']>.01 for r in selected),'fully_above_5cm':sum(r['min_vertex_clearance_m']>.05 for r in selected),'min_clearance_range_m':[min(r['min_vertex_clearance_m'] for r in selected),max(r['min_vertex_clearance_m'] for r in selected)],'worst':sorted(selected,key=lambda r:-r['min_vertex_clearance_m'])[:6]})
    return {'summary':summary,'rows':rows}

if __name__=='__main__':
    d=readjs(ROOT/'data/rille.js');assets=readjs(ROOT/'shared/assets.js')
    result=audit(d,assets)
    (BASE/'build/rille_seating_before.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result['summary'],indent=2))
