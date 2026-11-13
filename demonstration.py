"""Repeatable synthetic fixtures, explicitly labelled DEMO."""
from datetime import timedelta
import io
import json
from pathlib import Path
import numpy as np
from PIL import Image
from engine import now,digest

def create_demo(store):
    base=now().replace(microsecond=0);inserted=0
    store.set_site({'id':'DEMO-RIVER','mode':'DEMO','latitude':-3.1,'longitude':-60.0,'expected_interval_s':10})
    store.set_site({'id':'DEMO-OFFLINE','mode':'DEMO','latitude':-3.13,'longitude':-60.05,'expected_interval_s':10})
    for i in range(60):
        d={'id':f'demo-temp-{i}','site_id':'DEMO-RIVER','source_type':'sensor','source_ref':'Synthetic replay; not a physical sensor','mode':'DEMO','timestamp':(base-timedelta(seconds=(59-i)*10)).isoformat(),'latitude':-3.1,'longitude':-60.0,'metric':'temperature_c','value':round(27+np.sin(i*1.3)*1.2+(16 if i>=57 else 0),3),'quality':'valid','metadata':{'fixture':True}}
        # Stable fixtures are generated once, preserving event IDs on repeated clicks.
        if any(x['id']==d['id'] for x in store.rows('DEMO')):continue
        inserted+=store.add(d)
    for i,(typ,metric,value,age) in enumerate([('satellite','satellite_alert',1,0),('drone','vegetation_change_pct',18,0),('sensor','humidity_pct',0,72)]):
        oid='demo-event-'+str(i)
        if any(x['id']==oid for x in store.rows('DEMO')):continue
        inserted+=store.add({'id':oid,'site_id':'DEMO-RIVER' if i<2 else 'DEMO-OFFLINE','source_type':typ,'source_ref':'Synthetic scenario, not a real detection','mode':'DEMO','timestamp':(base-timedelta(hours=age)).isoformat(),'latitude':-3.1-i*.01,'longitude':-60.0-i*.01,'metric':metric,'value':value,'quality':'valid','metadata':{'fixture':True}})
    return {'inserted':inserted,'mode':'DEMO','note':'Synthetic sensor replay and candidate changes; no real detection or physical validation.'}

def write_examples(root):
    root=Path(root);root.mkdir(exist_ok=True,parents=True)
    h=w=240;b=np.zeros((h,w,3),dtype='uint8');b[:]=[35,130,50];a=b.copy();a[60:160,80:180]=[160,95,50]
    for name,array in [('rgb_before.png',b),('rgb_after.png',a),('rgb_common_mask.png',np.full((h,w),255,dtype='uint8'))]:Image.fromarray(array).save(root/name)
    import rasterio
    from rasterio.transform import from_origin
    transform=from_origin(500000,9657500,10,10)
    red=np.full((h,w),.08,dtype='float32');nir=np.full((h,w),.45,dtype='float32');nir_after=nir.copy();nir_after[60:160,80:180]=.12
    for name,n in [('ndvi_before.tif',nir),('ndvi_after.tif',nir_after)]:
        with rasterio.open(root/name,'w',driver='GTiff',width=w,height=h,count=2,dtype='float32',crs='EPSG:32721',transform=transform,nodata=-9999,compress='deflate') as ds:ds.write(red,1);ds.write(n,2)
    with rasterio.open(root/'ndvi_common_mask.tif','w',driver='GTiff',width=w,height=h,count=1,dtype='uint8',crs='EPSG:32721',transform=transform,compress='deflate') as ds:ds.write(np.ones((h,w),dtype='uint8'),1)
    meta={'mode':'DEMO','source_type':'drone','site_id':'DEMO-RIVER','source_ref':'Synthetic co-registered fixture','latitude':-3.1,'longitude':-60.0,'before_time':'2026-11-10T12:00:00Z','after_time':'2026-11-11T12:00:00Z','aligned':True,'scale':1,'offset':0,'red_band':1,'nir_band':2,'threshold':.2,'baseline':.4}
    (root/'image_metadata.json').write_text(json.dumps(meta,indent=2))
    sensor={'id':'demo-replay-single','site_id':'DEMO-RIVER','source_type':'sensor','source_ref':'Synthetic replay','mode':'DEMO','timestamp':base_time(),'latitude':-3.1,'longitude':-60.0,'metric':'temperature_c','value':27.2,'quality':'valid','metadata':{'device_id':'demo-device','calibration':'synthetic; not calibrated hardware'}}
    (root/'sensor_observations.json').write_text(json.dumps([sensor],indent=2))
    flight={'flight_id':'DEMO-FLIGHT-001','mode':'DEMO','platform':'Synthetic drone manifest','observations':[dict(sensor,id='demo-drone-manifest',source_type='drone',metric='vegetation_change_pct',value=12,source_ref='Synthetic externally supplied change estimate')],'note':'A manifest is metadata only, not a flight controller.'}
    (root/'drone_manifest.json').write_text(json.dumps(flight,indent=2))

def base_time():return now().replace(microsecond=0).isoformat()
