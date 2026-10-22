from pathlib import Path
import base64
import json
import numpy as np

from pipeline_config import OUTPUT
ROOT=OUTPUT
def decode(s):
    return np.frombuffer(base64.b64decode(s),dtype='<f4')
def sample(a,x,y,cx,cy,width):
    n=len(a); step=width/(n-1)
    c=np.clip((x-cx+width/2)/step,0,n-1.000000001)
    r=np.clip((cy+width/2-y)/step,0,n-1.000000001)
    ci,ri=np.floor(c).astype(int),np.floor(r).astype(int)
    u,v=c-ci,r-ri
    h00,h01,h10,h11=a[ri,ci],a[ri,ci+1],a[ri+1,ci],a[ri+1,ci+1]
    return np.where(u+v<=1,h00+u*(h01-h00)+v*(h10-h00),h11+(1-u)*(h10-h11)+(1-v)*(h01-h11))
results=[]
for meta in json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))['regions']:
    key=meta['key']
    d=json.loads((ROOT/'data'/f'{key}.js').read_text(encoding='utf-8').split('=',1)[1].rstrip(';\r\n'))
    n=d['field']['n'];cn=d['context']['n'];cw=d['context']['width_m']
    base=decode(d['field']['base']).reshape(n,n).astype(float)
    context=decode(d['context']['heights']).reshape(cn,cn).astype(float)
    raw=decode(d['native']['z']).reshape(d['native']['n'],-1).astype(float)
    stride=d['native'].get('display_stride',1)
    far=raw[::stride,::stride]
    yy,xx=np.meshgrid(np.linspace(d['focus'][1]+6,d['focus'][1]-6,n),np.linspace(d['focus'][0]-6,d['focus'][0]+6,n),indexing='ij')
    border=np.zeros((n,n),bool);border[[0,-1],:]=True;border[:,[0,-1]]=True
    inner_error=float(np.max(abs(sample(context,xx[border],yy[border],*d['origin'],cw)-base[border])))
    yy,xx=np.meshgrid(np.linspace(d['origin'][1]+cw/2,d['origin'][1]-cw/2,cn),np.linspace(d['origin'][0]-cw/2,d['origin'][0]+cw/2,cn),indexing='ij')
    border=np.zeros((cn,cn),bool);border[[0,-1],:]=True;border[:,[0,-1]]=True
    outer_error=float(np.max(abs(sample(far,xx[border],yy[border],0,0,d['native']['width'])-context[border])))
    assert inner_error<.0001,(key,inner_error)
    assert outer_error<.0001,(key,outer_error)
    native_step=d['native']['width']/(len(far)-1)
    # Context holes must meet complete far-grid edges; no half-cell gaps.
    for center in d['origin']:
        for sign in [-1,1]:
            coord=(center+sign*cw/2+d['native']['width']/2)/native_step
            assert abs(coord-round(coord))<1e-6,(key,coord)
    results.append({'region':key,'detail_to_context_boundary_max_error_m':inner_error,'context_to_displayed_far_boundary_max_error_m':outer_error,'context_hole_edges_aligned':True,'far_display_stride':stride})
report={'passed':True,'regions':results,'checked':'shared border vertices and actual display triangle interpolation; sub-millimetre storage tolerance'}
(ROOT/'seam_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
