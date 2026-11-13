"""Bounded co-registered image screening. Pixel change is not ground truth."""
import io
from datetime import datetime
import numpy as np
from PIL import Image
from engine import number,time_value

MAX_PIXELS=4_000_000

def rgb_read(data):
    with Image.open(io.BytesIO(data)) as im:
        if im.width*im.height>MAX_PIXELS:raise ValueError('Image limit: 4 million pixels; crop the AOI first')
        return np.asarray(im.convert('RGB'),dtype=np.float32)/255

def dates(meta):
    before=time_value(meta.get('before_time'));after=time_value(meta.get('after_time'))
    if datetime.fromisoformat(before)>=datetime.fromisoformat(after):raise ValueError('After image must be newer than before image')
    if meta.get('aligned') is not True:raise ValueError('Confirm that input images are co-registered to the same grid')
    return before,after

def mask_png(data,size):
    if not data:raise ValueError('A common clear/valid mask is required (white=usable in BOTH dates; black=exclude)')
    with Image.open(io.BytesIO(data)) as im:
        if im.size!=(size[1],size[0]):raise ValueError('Mask grid size differs from imagery')
        return np.asarray(im.convert('L'))>=128

def summarize(before,after,valid,threshold,baseline):
    valid=valid & np.isfinite(before) & np.isfinite(after)
    n=int(valid.sum())
    if n==0:raise ValueError('No common valid pixels')
    # Coverage denominators are explicit; change fraction uses vegetated baseline only.
    eligible=valid & (before>=baseline); changed=eligible & ((before-after)>=threshold)
    denom=int(eligible.sum())
    if denom==0:raise ValueError('No baseline vegetation pixels meet the screening threshold')
    return {'total_pixels':int(valid.size),'valid_pixels':n,'valid_coverage_pct':round(n/valid.size*100,4),'baseline_pixels':denom,'changed_pixels':int(changed.sum()),'change_pct':round(float(changed.sum())/denom*100,4),'mean_before':round(float(before[valid].mean()),5),'mean_after':round(float(after[valid].mean()),5),'threshold':threshold,'baseline_threshold':baseline},changed,valid

def png(array):
    im=Image.fromarray(array.astype('uint8'));buf=io.BytesIO();im.save(buf,format='PNG');return buf.getvalue()

def rgb_pair(before_bytes,after_bytes,mask_bytes,meta):
    dates(meta);b=rgb_read(before_bytes);a=rgb_read(after_bytes)
    if b.shape!=a.shape:raise ValueError('Image dimensions differ; co-register before analysis')
    m=mask_png(mask_bytes,b.shape[:2])
    # Green leaf index: visible-band screening, not NDVI and not a canopy classifier.
    def gli(x):
        r,g,bl=x[:,:,0],x[:,:,1],x[:,:,2];den=2*g+r+bl
        return np.divide(2*g-r-bl,den,out=np.zeros_like(g),where=den>1e-6)
    summary,changed,valid=summarize(gli(b),gli(a),m,number(meta.get('threshold',0.15),0.01,1,'threshold'),number(meta.get('baseline',0.1),-1,1,'baseline'))
    out=(a*255).astype('uint8');out[~valid]=[80,80,80];out[changed]=[255,78,78]
    return dict(summary,method='RGB Green Leaf Index decline screening (not NDVI)',limitations=['Manual co-registration and supplied common clear mask are prerequisites.','Shadows, seasonality, illumination, water and land management can mimic vegetation loss.','No automatic cloud detection, ground truth, illegal-logging finding or prevented-deforestation estimate.'],area_ha=None),png(out)

def ndvi_pair(before_bytes,after_bytes,mask_bytes,meta):
    import rasterio
    from rasterio.io import MemoryFile
    dates(meta)
    red=int(meta.get('red_band',1));nir=int(meta.get('nir_band',2))
    if red==nir or red<1 or nir<1:raise ValueError('Select distinct 1-based red and NIR bands')
    scale=number(meta.get('scale'),1e-9,1,'reflectance scale');offset=number(meta.get('offset',0),-1,1,'offset')
    def read(data):
        with MemoryFile(data) as mem:
            with mem.open() as ds:
                if ds.width*ds.height>MAX_PIXELS:raise ValueError('GeoTIFF limit: 4 million pixels; crop first')
                if not ds.crs:raise ValueError('GeoTIFF needs a CRS')
                if max(red,nir)>ds.count:raise ValueError('Selected band exceeds raster band count')
                r=ds.read(red,masked=True).astype('float32')*scale+offset;n=ds.read(nir,masked=True).astype('float32')*scale+offset
                valid=~(np.ma.getmaskarray(r)|np.ma.getmaskarray(n))
                r=r.filled(np.nan);n=n.filled(np.nan)
                valid &= np.isfinite(r)&np.isfinite(n)&(r>=0)&(r<=1)&(n>=0)&(n<=1)&((n+r)>1e-7)
                v=np.divide(n-r,n+r,out=np.full(r.shape,np.nan),where=valid)
                return v,valid,ds.crs,ds.transform
    b,bm,bc,bt=read(before_bytes);a,am,ac,at=read(after_bytes)
    if b.shape!=a.shape or bc!=ac or not bt.almost_equals(at):raise ValueError('GeoTIFF grids differ (size, CRS or transform); co-register externally first')
    if not mask_bytes:raise ValueError('A common clear mask GeoTIFF is required')
    with MemoryFile(mask_bytes) as mem:
        with mem.open() as ds:
            if (ds.height,ds.width)!=b.shape or ds.crs!=bc or not ds.transform.almost_equals(bt):raise ValueError('Clear-mask grid differs from imagery')
            mask=ds.read(1,masked=True);valid=bm&am&~np.ma.getmaskarray(mask)&(mask.filled(0)>0)
    summary,changed,valid=summarize(b,a,valid,number(meta.get('threshold',0.2),0.01,2,'threshold'),number(meta.get('baseline',0.4),-1,1,'baseline'))
    area=None
    if bc.is_projected and bc.linear_units=='metre':area=round(summary['changed_pixels']*abs(bt.a*bt.e-bt.b*bt.d)/10000,6)
    out=np.zeros((*b.shape,3),dtype='uint8');out[:]=[80,80,80];out[valid]=[32,115,75];out[changed]=[255,78,78]
    from rasterio.warp import transform
    x,y=bt*(b.shape[1]/2,b.shape[0]/2)
    lons,lats=transform(bc,'EPSG:4326',[x],[y])
    return dict(summary,method='NDVI decline screening with common clear mask',center_wgs84={'latitude':lats[0],'longitude':lons[0]},crs=str(bc),grid_transform=list(bt),area_ha=area,area_note='Projected grid area only; not a validated deforestation area. Geographic grids omit hectares.',limitations=['Supplied masks and reflectance calibration must be checked.','A decline in NDVI does not uniquely identify deforestation; seasonal and hydrological effects require review.','No automatic coregistration or cloud classification is performed.']),png(out)
