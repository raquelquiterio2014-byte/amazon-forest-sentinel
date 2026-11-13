"""Public INPE WFS adapter and GeoJSON import with explicit schema mapping."""
import json
import urllib.parse
import urllib.request
from datetime import date
from shapely.geometry import shape,box,mapping
from engine import digest,time_value

WFS='https://terrabrasilis.dpi.inpe.br/geoserver/deter-amz/wfs'
def bounds(value):
    if not isinstance(value,list) or len(value)!=4:raise ValueError('AOI must be [west,south,east,north]')
    from engine import number
    a,b,c,d=[number(v,-180 if i%2==0 else -90,180 if i%2==0 else 90,'AOI') for i,v in enumerate(value)]
    if a>=c or b>=d:raise ValueError('AOI west<east and south<north required')
    return [a,b,c,d]
def url_for(start,end,aoi,count=200,layer="deter_amz",geometry="geom",date_property="view_date"):
    aoi=bounds(aoi);s=date.fromisoformat(start);e=date.fromisoformat(end)
    if s>e:raise ValueError('Start date must precede end date')
    if not 1<=int(count)<=1000:raise ValueError('count must be 1..1000')
    # WFS 1.0.0 and explicit EPSG:4326 use longitude/latitude coordinate order.
    params={'service':'WFS','version':'1.0.0','request':'GetFeature','typeName':layer,'srsName':'EPSG:4326','outputFormat':'application/json','maxFeatures':int(count),'sortBy':'gid','CQL_FILTER':f"{date_property} BETWEEN '{s}' AND '{e}' AND BBOX({geometry},{','.join(map(str,aoi))},'EPSG:4326')"}
    # Geometry name is discovered before issuing GetFeature in fetch_inpe.
    return WFS+'?'+urllib.parse.urlencode(params)

def get_bytes(url,limit=20*1024*1024):
    request=urllib.request.Request(url,headers={'User-Agent':'AmazonForestSentinel/educational','Accept':'application/json, application/xml'})
    with urllib.request.urlopen(request,timeout=35) as r:data=r.read(limit+1)
    if len(data)>limit:raise ValueError('Download exceeds 20 MiB; reduce AOI / date range')
    return data

def fetch_inpe(start,end,aoi,count=200):
    import xml.etree.ElementTree as ET
    caps=ET.fromstring(get_bytes(WFS+'?service=WFS&version=2.0.0&request=GetCapabilities'))
    layers=[e.text for e in caps.iter() if e.tag.endswith('Name') and e.text and ':' in e.text]
    layer=next((v for v in layers if v.split(':')[-1]=='deter_amz'),None) or next((v for v in layers if v.split(':')[-1]=='deter_public'),None)
    if not layer:raise ValueError('No supported public DETER layer found; import downloaded GeoJSON instead')
    describe=WFS+'?'+urllib.parse.urlencode({'service':'WFS','version':'1.0.0','request':'DescribeFeatureType','typeName':layer})
    schema=ET.fromstring(get_bytes(describe))
    geom=None;fields=[]
    for el in schema.iter():
        typ=el.attrib.get('type','');name=el.attrib.get('name')
        if name:fields.append(name)
        if any(k in typ for k in ('Polygon','Geometry','Surface')):geom=name
    if not geom or not geom.replace('_','').isalnum():raise ValueError('Could not determine WFS geometry property; import downloaded GeoJSON instead')
    date_property='view_date' if 'view_date' in fields else 'date'
    url=url_for(start,end,aoi,count,layer,geom,date_property)
    raw=get_bytes(url)
    try:d=json.loads(raw)
    except Exception:raise ValueError('INPE did not return GeoJSON; check service availability or schema')
    if d.get('type')!='FeatureCollection':raise ValueError('Expected WFS FeatureCollection')
    return d,{'source_url':url,'layer':layer,'date_property':date_property,'retrieved_at':__import__('engine').stamp(),'sha256':digest(raw),'retrieval_note':'Bounded single-page sample; not a complete regional time series. At limit, narrow the query.','at_limit':len(d.get('features',[]))>=int(count)}

def import_geojson(store,collection,options):
    if not isinstance(collection,dict) or collection.get('type')!='FeatureCollection':raise ValueError('Expected GeoJSON FeatureCollection')
    crs=collection.get('crs',{}).get('properties',{}).get('name','EPSG:4326')
    if not any(x in crs.upper() for x in ('4326','CRS84')):raise ValueError('Reproject to WGS84 / EPSG:4326 before importing')
    mode=options.get('mode','FIELD');source=options.get('source_ref','User imported GeoJSON');aoi=box(*bounds(options.get('aoi',[-75,-20,-40,10])))
    date_field=options.get('date_field','view_date');id_field=options.get('id_field','gid');class_field=options.get('class_field','classname')
    result={'inserted':0,'duplicates':0,'outside_aoi':0,'errors':[],'selection':'Exact geometry intersection with AOI; original polygons retained, not clipped.'}
    features=collection.get('features',[])
    if not isinstance(features,list) or len(features)>10000:raise ValueError('Import limit: 10000 features')
    for i,f in enumerate(features):
        try:
            g=shape(f.get('geometry'))
            if not g.is_valid or g.is_empty or g.geom_type not in ('Polygon','MultiPolygon','Point'):raise ValueError('Invalid geometry')
            if not aoi.intersects(g):result['outside_aoi']+=1;continue
            props=f.get('properties') or {};t=props.get(date_field)
            if not isinstance(t,str):raise ValueError('Missing date field: '+date_field)
            if len(t)==10:t+='T00:00:00+00:00'
            elif not ('+' in t[10:] or t.endswith('Z')):raise ValueError('Datetime needs timezone; convert explicitly')
            t=time_value(t);ident=str(props.get(id_field) or f.get('id') or digest(json.dumps(f,sort_keys=True).encode())[:24])
            point=g.representative_point();official=('inpe' in source.lower() or 'terrabrasilis' in source.lower());key='inpe-deter' if official else digest(source.encode())[:10]
            stable_source='https://terrabrasilis.dpi.inpe.br/ | public DETER alert' if official else source
            d={'id':f'geo-{key}-{ident}','site_id':'INPE-AOI' if 'inpe' in source.lower() or 'terrabrasilis' in source.lower() else 'IMPORTED-AOI','source_type':'satellite','source_ref':stable_source,'mode':mode,'timestamp':t,'latitude':point.y,'longitude':point.x,'metric':'satellite_alert','value':1,'quality':'valid','geometry':mapping(g),'metadata':{'provider_id':ident,'class':str(props.get(class_field,'unspecified')),'properties':props,'geometry_crs':'EPSG:4326','meaning':'Imported vegetation-change alert, not a deforestation rate or legal finding'}}
            if store.add(d):result['inserted']+=1
            else:result['duplicates']+=1
        except Exception as e:result['errors'].append({'feature':i,'reason':str(e)[:250]})
    return result
