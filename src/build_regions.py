from pathlib import Path
import base64
import hashlib
import io
import json
import math
import shutil
import struct
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, map_coordinates
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation

from pipeline_config import OUTPUT, BASE_LIBRARY, REFERENCE_ROOT, APPROVED_PILOT
ROOT = OUTPUT
PREV = BASE_LIBRARY
SAMPLE = REFERENCE_ROOT
for folder in ['shared', 'data', 'images', 'exports', 'sources', 'references']:
    (ROOT / folder).mkdir(parents=True, exist_ok=True)

def readjs(p):
    return json.loads(p.read_text(encoding='utf-8').split('=', 1)[1].rstrip(';\r\n'))

def enc(a):
    return base64.b64encode(np.asarray(a, dtype='<f4').tobytes()).decode('ascii')

def dec(s):
    return np.frombuffer(base64.b64decode(s), dtype='<f4')

def writejs(p, name, value):
    p.write_text(name + '=' + json.dumps(value, ensure_ascii=False, separators=(',', ':')) + ';', encoding='utf-8')

def dump(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

assets = readjs(PREV / 'shared' / 'assets.js')
micro = dec(assets['micro']['z']).reshape(assets['micro']['n'], -1)
vertices = [dec(t['positions']).reshape(-1, 3).astype(float) for t in assets['rockTypes']]
shutil.copy2(PREV / 'shared' / 'three.min.js', ROOT / 'shared' / 'three.min.js')
# Keep the approved material bank exactly; add only a small-stone geometry LOD.
for kind, t in enumerate(assets['rockTypes']):
    if t.get('apollo'):
        continue
    v = vertices[kind]
    hull = ConvexHull(v[::max(1, len(v)//160)])
    hv = v[::max(1, len(v)//160)]
    faces = hull.simplices.copy()
    fn = np.cross(hv[faces[:, 1]]-hv[faces[:, 0]], hv[faces[:, 2]]-hv[faces[:, 0]])
    reverse = np.einsum('ij,ij->i', fn, hull.equations[:, :3]) < 0
    faces[reverse] = faces[reverse][:, [0, 2, 1]]
    t['pilot_lod'] = {'positions': enc(hv), 'indices': faces.ravel().tolist()}
writejs(ROOT / 'shared' / 'assets.js', 'window.REGION_ASSETS', assets)
for name in ['V3_acquisition.json', 'V3_SRB-ATTRIBUTIONS.md', 'NAC_DTM_LINNECRATER.LBL', 'NAC_DTM_SHACKRDGE02.LBL', 'NAC_DTM_MERSENIUS1.LBL', 'dem_sources.json']:
    shutil.copy2(PREV / 'sources' / name, ROOT / 'sources' / name)
for p in (SAMPLE / 'references').glob('*.jpg'):
    shutil.copy2(p, ROOT / 'references' / p.name)

def glb(path, world_positions, idx, center):
    # glTF uses Y up. Keep metres and rebase the local patch around its center.
    p = world_positions.copy()
    p[:, :2] -= center[:2]
    p[:, 2] -= center[2]
    p = p[:, [0, 2, 1]]
    p[:, 2] *= -1
    p = p.astype('<f4')
    faces = idx.reshape(-1, 3)
    normals = np.zeros_like(p)
    f = np.cross(p[faces[:, 1]]-p[faces[:, 0]], p[faces[:, 2]]-p[faces[:, 0]])
    for corner in range(3):
        np.add.at(normals, faces[:, corner], f)
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
    arrays = [p.tobytes(), normals.astype('<f4').tobytes(), idx.astype('<u4').tobytes()]
    blob = b''.join(arrays)
    offsets = [0, len(arrays[0]), len(arrays[0])+len(arrays[1])]
    doc = {'asset': {'version': '2.0', 'generator': 'Reproducible lunar detail pilot'},
           'scene': 0, 'scenes': [{'nodes': [0]}], 'nodes': [{'mesh': 0}],
           'meshes': [{'primitives': [{'attributes': {'POSITION': 0, 'NORMAL': 1}, 'indices': 2, 'material': 0}]}],
           'materials': [{'pbrMetallicRoughness': {'baseColorFactor': [.42, .42, .40, 1], 'metallicFactor': 0, 'roughnessFactor': 1}}],
           'buffers': [{'byteLength': len(blob)}],
           'bufferViews': [{'buffer': 0, 'byteOffset': o, 'byteLength': len(a), 'target': 34963 if i == 2 else 34962} for i, (a, o) in enumerate(zip(arrays, offsets))],
           'accessors': [{'bufferView': 0, 'componentType': 5126, 'count': len(p), 'type': 'VEC3', 'min': p.min(axis=0).tolist(), 'max': p.max(axis=0).tolist()},
                         {'bufferView': 1, 'componentType': 5126, 'count': len(p), 'type': 'VEC3'},
                         {'bufferView': 2, 'componentType': 5125, 'count': len(idx), 'type': 'SCALAR'}]}
    js = json.dumps(doc, separators=(',', ':')).encode('utf-8')
    js += b' ' * (-len(js) % 4)
    path.write_bytes(struct.pack('<III', 0x46546C67, 2, 12+8+len(js)+8+len(blob)) + struct.pack('<II', len(js), 0x4E4F534A) + js + struct.pack('<II', len(blob), 0x004E4942) + blob)

def normal_image(height, step):
    gy, gx = np.gradient(height, -step, step)
    a = np.stack([-gx, -gy, np.ones_like(height)], axis=-1)
    a /= np.linalg.norm(a, axis=-1, keepdims=True)
    return np.round((a*.5+.5)*255).clip(0, 255).astype('uint8')

def png_uri(a, path):
    Image.fromarray(a).save(path)
    return 'data:image/png;base64,' + base64.b64encode(path.read_bytes()).decode('ascii')

records = json.loads((APPROVED_PILOT / 'manifest.json').read_text(encoding='utf-8'))['regions']
for index, (key, rid, spot_index, label) in enumerate([
    ('rim', 'crater_rim', 0, '完整坑区与坑缘'),
    ('depression', 'local_depression', 0, '局部凹地'),
    ('ridge', 'polar_ridge', 1, '天然坡折'),
    ('ejecta', 'ejecta_undulations', 2, '坑外连续起伏'),
    ('rille', 'natural_rille', 1, '沟谷与两岸'),
], start=2):
    source = PREV / 'regions' / rid
    d = readjs(source / 'region_data.js')
    old_details = readjs(source / 'gravel.js')
    spot = d['spots'][spot_index]
    origin = np.array([spot['x'], spot['y']])
    yaw = spot['yaw']
    focus = np.round(origin + 4.2*np.array([np.cos(yaw), np.sin(yaw)]), 1)
    raw = dec(d['z']).reshape(d['n'], d['n'])
    rng = np.random.default_rng(2026102121 + index*100)

    def native(x, y):
        x, y = np.broadcast_arrays(x, y)
        return map_coordinates(raw, [(d['width']/2-y.ravel())/d['meta']['native_spacing_m'], (x.ravel()+d['width']/2)/d['meta']['native_spacing_m']], order=1, mode='nearest').reshape(x.shape)

    def ground(x, y):
        x, y = np.broadcast_arrays(x, y)
        out = native(x, y).astype(float)
        for s in d['spots']:
            dx, dy = x-s['x'], y-s['y']
            fade = np.clip((d['micro_half_m']-np.maximum(abs(dx), abs(dy)))/5, 0, 1)
            fade = fade*fade*(3-2*fade)
            out += map_coordinates(micro, [((12-dy.ravel()) % 24)/24*(micro.shape[0]-1), ((dx.ravel()+12) % 24)/24*(micro.shape[1]-1)], order=1, mode='nearest').reshape(x.shape)*fade
        return out

    width, step = 12., .02
    n = round(width/step)+1
    x = np.linspace(focus[0]-width/2, focus[0]+width/2, n)
    y = np.linspace(focus[1]+width/2, focus[1]-width/2, n)
    xx, yy = np.meshgrid(x, y)
    low = np.zeros((n, n), float)
    mounds = []
    for j in range(190):
        cx, cy = rng.uniform(-5.6, 5.6, 2) + focus
        rx = rng.uniform(.065, .22)
        ry = rx*rng.uniform(.65, 1.35)
        angle = rng.uniform(0, 2*np.pi)
        amp = rng.uniform(.004, .019)
        c0 = max(0, int((cx-3*rx-x[0])/step)); c1 = min(n, int((cx+3*rx-x[0])/step)+1)
        r0 = max(0, int((y[0]-cy-3*ry)/step)); r1 = min(n, int((y[0]-cy+3*ry)/step)+1)
        # Use a circular support larger than either rotated principal radius.
        radius = 3*max(rx, ry)
        c0=max(0, int((cx-radius-x[0])/step)); c1=min(n,int((cx+radius-x[0])/step)+1)
        r0=max(0, int((y[0]-cy-radius)/step)); r1=min(n,int((y[0]-cy+radius)/step)+1)
        dx, dy = xx[r0:r1, c0:c1]-cx, yy[r0:r1, c0:c1]-cy
        u, v = np.cos(angle)*dx+np.sin(angle)*dy, -np.sin(angle)*dx+np.cos(angle)*dy
        low[r0:r1, c0:c1] += amp*np.exp(-1.7*((u/rx)**2+(v/ry)**2))
        mounds.append({'x_m': float(cx), 'y_m': float(cy), 'radii_m': [float(rx), float(ry)], 'peak_m': float(amp), 'angle_rad': float(angle)})
    fine = gaussian_filter(rng.normal(0, 1, (n, n)), 1.15)
    fine *= .00055 / np.std(fine)
    fine = np.clip(fine, -.0016, .0016)
    fade = np.clip((width/2-np.maximum(abs(xx-focus[0]), abs(yy-focus[1])))/.65, 0, 1)
    fade = fade*fade*(3-2*fade)
    low *= fade
    fine *= fade
    base = ground(xx, yy)
    # Match the 10 cm surrounding grid exactly along the high-resolution border.
    context_width = 49. if abs(d['meta']['native_spacing_m']-3.5) < .01 else 48.
    cn = round(context_width/.1)+1
    cx = np.linspace(origin[0]-context_width/2, origin[0]+context_width/2, cn)
    cy = np.linspace(origin[1]+context_width/2, origin[1]-context_width/2, cn)
    cxx, cyy = np.meshgrid(cx, cy)
    coarse = ground(cxx, cyy)
    # Blend the context boundary to the actual displayed far-field triangles.
    stride = int(d.get('display_stride', 1))
    far = raw[::stride, ::stride]
    fs = d['meta']['native_spacing_m']*stride
    fc = np.clip((cxx+d['width']/2)/fs, 0, len(far)-1.00000001)
    fr = np.clip((d['width']/2-cyy)/fs, 0, len(far)-1.00000001)
    fi, fj = np.floor(fc).astype(int), np.floor(fr).astype(int)
    fu, fv = fc-fi, fr-fj
    f00, f01, f10, f11 = far[fj,fi], far[fj,fi+1], far[fj+1,fi], far[fj+1,fi+1]
    far_height = np.where(fu+fv<=1, f00+fu*(f01-f00)+fv*(f10-f00), f11+(1-fu)*(f10-f11)+(1-fv)*(f01-f11))
    context_fade = np.clip((context_width/2-np.maximum(abs(cxx-origin[0]),abs(cyy-origin[1])))/4,0,1)
    context_fade = context_fade*context_fade*(3-2*context_fade)
    coarse = far_height*(1-context_fade)+coarse*context_fade
    coarse_interp = map_coordinates(coarse, [(cy[0]-yy.ravel())/.1, (xx.ravel()-cx[0])/.1], order=1, mode='nearest').reshape(xx.shape)
    border_blend = np.clip((width/2-np.maximum(abs(xx-focus[0]), abs(yy-focus[1])))/.3, 0, 1)
    border_blend = border_blend*border_blend*(3-2*border_blend)
    base = coarse_interp*(1-border_blend)+base*border_blend

    def triangle_height(a, xq, yq):
        # Match the actual two planar triangles used by the browser and GLB.
        xq, yq = np.broadcast_arrays(xq, yq)
        c = np.clip((xq-x[0])/step, 0, n-1.000000001)
        r = np.clip((y[0]-yq)/step, 0, n-1.000000001)
        ci, ri = np.floor(c).astype(int), np.floor(r).astype(int)
        u, v = c-ci, r-ri
        h00, h01, h10, h11 = a[ri,ci], a[ri,ci+1], a[ri+1,ci], a[ri+1,ci+1]
        return np.where(u+v <= 1, h00+u*(h01-h00)+v*(h10-h00), h11+(1-u)*(h10-h11)+(1-v)*(h01-h11))

    def displayed_base(xq, yq):
        xq, yq = np.broadcast_arrays(xq, yq)
        out = ground(xq, yq)
        inside = (abs(xq-focus[0]) <= 6) & (abs(yq-focus[1]) <= 6)
        sampled = triangle_height(base, xq, yq)
        return np.where(inside, sampled, out)

    def delta(xq, yq):
        xq, yq = np.broadcast_arrays(xq, yq)
        inside = (abs(xq-focus[0]) <= 6) & (abs(yq-focus[1]) <= 6)
        return np.where(inside, triangle_height(low, xq, yq), 0)

    normal_full = normal_image(low+fine, step)
    normal_fine = normal_image(fine, step)
    uri_full = png_uri(normal_full, ROOT / 'exports' / f'{key}_normal_opengl.png')
    uri_fine = png_uri(normal_fine, ROOT / 'exports' / f'{key}_fine_normal_opengl.png')
    normal_dx = normal_full.copy(); normal_dx[:, :, 1] = 255-normal_dx[:, :, 1]
    Image.fromarray(normal_dx).save(ROOT / 'exports' / f'{key}_normal_directx.png')
    height_min, height_max = -.004, .04
    height16 = np.round((low+fine-height_min)/(height_max-height_min)*65535).clip(0, 65535).astype('uint16')
    Image.fromarray(height16).save(ROOT / 'exports' / f'{key}_detail_height16.png')
    np.savez_compressed(ROOT / 'exports' / f'{key}_height_fields.npz', x_m=x, y_m=y, base_height_m=base.astype('f4'), low_detail_m=low.astype('f4'), fine_detail_m=fine.astype('f4'))
    ids = np.arange(n*n).reshape(n, n)
    j = ids[:-1, :-1].ravel()
    triangles = np.stack([j, j+n, j+1, j+1, j+n, j+n+1], axis=1).astype('u4').ravel()
    center = [float(focus[0]), float(focus[1]), float(ground(*focus))]
    glb(ROOT / 'exports' / f'{key}_surface.glb', np.stack([xx, yy, base+low], axis=-1).reshape(-1, 3), triangles, center)

    obstacles = []
    existing = []
    for rock in d['rocks']:
        matrix = np.array(rock['matrix']).reshape((4, 4), order='F')
        if np.linalg.norm(matrix[:2, 3]-focus) > 48:
            continue
        transformed = vertices[rock['type']] @ matrix[:3, :3].T
        radius = float(np.linalg.norm(transformed[:, :2], axis=1).max())
        obstacles.append([*matrix[:2, 3], radius])
        r = dict(rock)
        moved = matrix.copy()
        # Preserve approved seating; only lift by the new support-height change.
        lower = transformed[:, 2] < np.quantile(transformed[:, 2], .3)
        lift = float(np.max(delta(transformed[lower, 0]+matrix[0, 3], transformed[lower, 1]+matrix[1, 3])))
        moved[2, 3] += lift
        r['displaced_matrix'] = moved.T.ravel().tolist()
        existing.append(r)
    obstacles = np.array(obstacles, float)
    approved = old_details['gravel_spots'][spot_index]['instances']
    old_gravel = []
    for r in approved:
        if np.linalg.norm(np.array(r['matrix'][12:14])-origin) > 27:
            continue
        rr = dict(r)
        m = np.array(r['matrix']).reshape((4, 4), order='F')
        v = vertices[r['type']] @ m[:3, :3].T
        lift = float(np.max(delta(v[:, 0]+m[0, 3], v[:, 1]+m[1, 3])))
        m[2, 3] += lift
        rr['displaced_matrix'] = m.T.ravel().tolist()
        old_gravel.append(rr)

    # Keep sampled dimensions and orientations shared across the two layouts.
    templates = []
    for group, count, minimum, maximum, b in [('fine', 740, .018, .08, 1.8), ('medium', 66, .08, .42, 2.1), ('large', 5, .45, .95, 2.0)]:
        for j in range(count):
            u = rng.random()
            diameter = float((minimum**-b + u*(maximum**-b-minimum**-b))**(-1/b))
            kind = int(rng.integers(7))
            shape = rng.uniform([.75, .75, .65], [1.25, 1.25, 1.10])
            euler = rng.uniform([-10, -10, 0], [10, 10, 360])
            buried = float(rng.uniform(.1, .3)) if rng.random() < .4 else 0.
            templates.append({'group': group, 'diameter': diameter, 'type': kind, 'shape': shape, 'euler': euler, 'buried': buried})
    templates.sort(key=lambda t: -t['diameter'])

    layout_stats = {}
    sets = {}
    for layout_index, layout in enumerate(['uniform', 'clustered']):
        prng = np.random.default_rng(2026102181+index*100+layout_index)
        clusters = prng.uniform(-4.6, 4.6, (9, 2))+focus
        placed = []
        result = []
        skipped = []
        min_gap = float('inf')
        gaps0, gaps1 = [], []
        group_counts = {'fine': 0, 'medium': 0, 'large': 0}
        for template_index, t in enumerate(templates):
            kind = t['type']
            v = dec(assets['rockTypes'][kind]['pilot_lod']['positions']).reshape(-1, 3).astype(float) if t['diameter'] < .08 else vertices[kind]
            for attempt in range(60):
                if layout == 'clustered' and prng.random() < .68:
                    xy = clusters[prng.integers(len(clusters))]+prng.normal(0, .65, 2)
                else:
                    xy = prng.uniform(-5.85, 5.85, 2)+focus
                if np.linalg.norm(xy-origin) < .65:
                    continue
                eps = .08
                gx = float(displayed_base(xy[0]+eps, xy[1])-displayed_base(xy[0]-eps, xy[1]))/(2*eps)
                gy = float(displayed_base(xy[0], xy[1]+eps)-displayed_base(xy[0], xy[1]-eps))/(2*eps)
                normal = np.array([-gx, -gy, 1]); normal /= np.linalg.norm(normal)
                axis = np.cross([0, 0, 1], normal); length = np.linalg.norm(axis)
                align = Rotation.from_rotvec(axis/max(length, 1e-12)*np.arctan2(length, normal[2]))
                rotation = (align * Rotation.from_euler('xyz', t['euler'], degrees=True)).as_matrix()
                linear = rotation @ np.diag(t['shape'])
                w = v @ linear.T
                factor = t['diameter']/np.ptp(w[:, :2], axis=0).max()
                linear *= factor; w *= factor
                radius = float(np.linalg.norm(w[:, :2], axis=1).max())
                if np.max(abs(xy-focus))+radius > 5.9:
                    continue
                p = np.array(placed) if placed else np.empty((0, 3))
                all_obstacles = np.vstack([obstacles, p])
                distances = np.linalg.norm(all_obstacles[:, :2]-xy, axis=1)-all_obstacles[:, 2]-radius
                if len(distances) and distances.min() < .004:
                    continue
                grounds = displayed_base(w[:, 0]+xy[0], w[:, 1]+xy[1])
                burial = np.ptp(w[:, 2])*t['buried']
                z0 = float(np.max(grounds-w[:, 2])-burial)
                z1 = float(np.max(grounds+delta(w[:, 0]+xy[0], w[:, 1]+xy[1])-w[:, 2])-burial)
                mat = np.eye(4); mat[:3, :3] = linear; mat[:3, 3] = [*xy, z0]
                moved = mat.copy(); moved[2, 3] = z1
                result.append({'type': kind, 'matrix': mat.T.ravel().tolist(), 'displaced_matrix': moved.T.ravel().tolist(), 'width_m': t['diameter'], 'group': t['group'], 'buried_fraction': t['buried'], 'template_id': template_index})
                placed.append([*xy, radius]); group_counts[t['group']] += 1
                if len(distances): min_gap = min(min_gap, float(distances.min()))
                gaps0.append(float(np.min(w[:, 2]+z0-grounds)))
                gaps1.append(float(np.min(w[:, 2]+z1-grounds-delta(w[:, 0]+xy[0], w[:, 1]+xy[1]))))
                break
            else:
                skipped.append(template_index)
        sets[layout] = result
        layout_stats[layout] = {'requested': len(templates), 'placed': len(result), 'skipped_template_ids': skipped, 'counts': group_counts,
            'minimum_bounding_circle_gap_m': min_gap, 'vertex_clearance_base_range_m': [min(gaps0), max(gaps0)],
            'vertex_clearance_displaced_range_m': [min(gaps1), max(gaps1)], 'partial_burial_count': sum(r['buried_fraction'] > 0 for r in result),
            'diameter_range_m': [min(r['width_m'] for r in result), max(r['width_m'] for r in result)],
            'spatial_model': 'uniform candidates plus rejection' if layout == 'uniform' else '68 percent cluster candidates plus 32 percent uniform candidates and rejection'}
        assert min_gap >= .004-1e-10

    context_width = 49. if abs(d['meta']['native_spacing_m']-3.5) < .01 else 48.
    cn = round(context_width/.1)+1
    cx = np.linspace(origin[0]-context_width/2, origin[0]+context_width/2, cn)
    cy = np.linspace(origin[1]+context_width/2, origin[1]-context_width/2, cn)
    cxx, cyy = np.meshgrid(cx, cy)
    normal_step = .02
    desired = focus - np.array([np.cos(yaw), np.sin(yaw)])
    targets = [m for m in mounds if m['peak_m'] > .012 and np.max(abs(np.array([m['x_m'], m['y_m']])-focus)) < 4.5 and all(np.linalg.norm(np.array([m['x_m'],m['y_m']])-o[:2]) > o[2]+.35 for o in obstacles)]
    target = min(targets, key=lambda m: np.linalg.norm(np.array([m['x_m'],m['y_m']])-desired))
    result = {'key': key, 'label': label, 'region_id': rid, 'origin': origin.tolist(), 'focus': focus.tolist(), 'detail_target': [target['x_m'], target['y_m']],
        'yaw': yaw, 'pitch': spot['pitch'], 'native': d, 'base_camera_height': float(ground(*origin)),
        'field': {'width_m': width, 'step_m': step, 'n': n, 'base': enc(base), 'low': enc(low), 'fine': enc(fine),
                  'normal_full': uri_full, 'normal_fine': uri_fine},
        'context': {'width_m': context_width, 'n': cn, 'heights': enc(coarse)},
        'existing_rocks': existing, 'approved_gravel': old_gravel, 'layouts': sets, 'layout_stats': layout_stats}
    writejs(ROOT / 'data' / f'{key}.js', f'window.PILOT_REGIONS.{key}', result)
    dump(ROOT / 'exports' / f'{key}_rock_instances.json', {'coordinate_system': 'source local XYZ, Z up, metres', 'matrix_order': 'column-major', 'seed': 2026102181+index*100, 'existing_rocks': existing, 'uniform': sets['uniform'], 'clustered': sets['clustered']})
    shutil.copy2(source / 'data' / 'native_dem.npz', ROOT / 'sources' / f'{key}_native_dem.npz')
    shutil.copy2(source / 'metadata.json', ROOT / 'sources' / f'{key}_native_metadata.json')
    stats = {'key': key, 'name': label, 'source_region': rid, 'source_dem_spacing_m': d['meta']['native_spacing_m'],
        'source_dem_sha256': sha(source / 'data' / 'native_dem.npz'), 'source_copy_identical': sha(source / 'data' / 'native_dem.npz') == sha(ROOT / 'sources' / f'{key}_native_dem.npz'),
        'field_width_m': width, 'field_step_m': step, 'field_vertices': n*n, 'field_triangles': len(triangles)//3,
        'low_detail_height_range_m': [float(low.min()), float(low.max())], 'fine_detail_height_range_m': [float(fine.min()), float(fine.max())],
        'edge_height_m': float(np.max(abs(np.r_[low[0], low[-1], low[:, 0], low[:, -1], fine[0], fine[-1], fine[:, 0], fine[:, -1]]))),
        'mound_count': len(mounds), 'synthetic': True, 'site_statistics_calibrated': False, 'seed': 2026102121+index*100,
        'height16_decode': {'minimum_m': height_min, 'maximum_m': height_max, 'formula': 'height_m = pixel / 65535 * (maximum_m-minimum_m) + minimum_m', 'includes': 'low plus fine detail; no base DEM'},
        'glb_coordinate_system': 'Y up, metres; local glTF=(source_x-focus_x, source_z-center_z, -(source_y-focus_y))',
        'source_patch_center_xyz_m': center, 'glb_contains': 'approved base height plus low detail; no rocks or textures',
        'normal_convention': 'RGB tangent-space OpenGL +Y; DirectX copy flips green',
        'normal_combination': 'normal-only uses low+fine; displaced surface uses fine only to avoid repeating low-frequency slopes',
        'layouts': layout_stats, 'engine': 'Three.js WebGL', 'image_model_called': False, 'mesh_model_called': False,
        'mujoco_run': False, 'ue_run': False, 'physics_stability_tested': False, 'experimental_crop': False}
    dump(ROOT / 'exports' / f'{key}_metadata.json', stats)
    dump(ROOT / 'sources' / f'{key}_mounds.json', mounds)
    records.append(stats)
    print(json.dumps({'built': key, 'vertices': n*n, 'layouts': {k: v['placed'] for k, v in layout_stats.items()}, 'height_range': stats['low_detail_height_range_m']}, ensure_ascii=False), flush=True)

manifest = {'date': '2026-10-21', 'purpose': 'Seven terrain classes with approved material, switchable detail, and layered rock placement', 'regions': records,
    'runtime_dependencies': ['numpy', 'scipy', 'Pillow'],
    'generation': 'GPT-authored deterministic numerical height fields, derived normal maps, and actual GLB surfaces',
    'external_image_or_mesh_model_used': False, 'existing_library_modified': False, 'previous_plain_and_slope_preserved': True, 'detail_observation_points_per_region': 1}
dump(ROOT / 'manifest.json', manifest)
(ROOT / 'START_HERE.cmd').write_text('@echo off\r\nstart "" "%~dp0index.html"\r\n', encoding='ascii')
print('PILOT_DATA_READY', flush=True)
