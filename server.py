"""Loopback-only web application with authenticated ingestion and no telemetry."""
import argparse
import base64
import hmac
import json
import mimetypes
import os
import re
import secrets
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path

from engine import Store,RELEASE,canonical,stamp,digest
from adapters import import_geojson,fetch_inpe
from demonstration import create_demo
from imagery import rgb_pair,ndvi_pair
from intelligence import local_anomalies,gemini
from reporting import report_html,csv_bytes

ROOT=Path(__file__).resolve().parent

def load_env(path):
    if not path.exists():return
    for line in path.read_text(encoding='utf-8').splitlines():
        line=line.strip()
        if line and not line.startswith('#') and '=' in line:
            key,value=line.split('=',1)
            if key in ('GEMINI_API_KEY','GEMINI_MODEL','SENSOR_TOKEN'):os.environ.setdefault(key,value.strip().strip('"').strip("'"))

def decode(item):
    if not isinstance(item,dict):raise ValueError('Expected file object')
    name=item.get('name','upload.bin')
    try:b=base64.b64decode(item.get('data',''),validate=True)
    except Exception:raise ValueError('Invalid base64 file')
    if not b or len(b)>32*1024*1024:raise ValueError('File size must be 1 byte..32 MiB')
    return name,b

class Handler(BaseHTTPRequestHandler):
    server_version='AmazonForestSentinel'
    def log_message(self,*args):pass
    @property
    def store(self):return self.server.store
    def reply(self,value,status=200,ctype='application/json',filename=None):
        body=value if isinstance(value,bytes) else canonical(value).encode()
        self.send_response(status);self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','DENY')
        self.send_header('Referrer-Policy','strict-origin-when-cross-origin')
        if filename:self.send_header('Content-Disposition','attachment; filename="'+filename+'"')
        self.end_headers();self.wfile.write(body)
    def host_ok(self):
        host=self.headers.get('Host','')
        return host in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}')
    def auth(self,sensor=False):
        token=self.headers.get('Authorization','').removeprefix('Bearer ') if sensor else self.headers.get('X-Session-Token','')
        return hmac.compare_digest(token,self.server.sensor_token if sensor else self.server.session_token)
    def do_GET(self):
        if not self.host_ok():return self.reply({'error':'Invalid host'},403)
        path=urllib.parse.urlsplit(self.path).path;q=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        try:
            if path=='/':
                html=(ROOT/'web/index.html').read_text(encoding='utf-8').replace('__SESSION_TOKEN__',self.server.session_token)
                return self.reply(html.encode(),ctype='text/html; charset=utf-8')
            if path.startswith('/web/'):
                p=(ROOT/path.lstrip('/')).resolve()
                if (ROOT/'web').resolve() not in p.parents or not p.is_file():return self.reply({'error':'Not found'},404)
                return self.reply(p.read_bytes(),ctype=mimetypes.guess_type(p.name)[0] or 'application/octet-stream')
            if not self.auth():return self.reply({'error':'Session token required'},401)
            if path=='/api/state':
                mode=q.get('mode',['DEMO'])[0]
                if mode not in ('DEMO','FIELD'):raise ValueError('Invalid mode')
                rows=self.store.rows(mode);ids={r['id'] for r in rows}
                return self.reply({'release':RELEASE,'mode':mode,'observations':rows,'sites':[s for s in self.store.sites() if s['mode']==mode],'events':[e for e in self.store.audit() if e['payload'].get('id') in ids or e['payload'].get('mode')==mode][-100:],'cloud_configured':bool(os.environ.get('GEMINI_API_KEY') and os.environ.get('GEMINI_MODEL')),'sensor_receiver':'Loopback HTTP; use USB/serial bridge or an authenticated SSH tunnel for remote hardware','integrity':self.store.verify()})
            if path=='/api/export':
                mode=q.get('mode',['DEMO'])[0];fmt=q.get('format',['json'])[0]
                if mode not in ('DEMO','FIELD'):raise ValueError('Invalid mode')
                if fmt=='html':return self.reply(report_html(self.store,mode),ctype='text/html; charset=utf-8',filename='forest_report_'+mode+'.html')
                if fmt=='csv':return self.reply(csv_bytes(self.store,mode),ctype='text/csv; charset=utf-8',filename='forest_observations_'+mode+'.csv')
                return self.reply(self.store.export(mode),filename='forest_evidence_'+mode+'.json')
            if path.startswith('/files/'):
                h=path.split('/')[-1]
                if not re.fullmatch('[0-9a-f]{64}',h):raise ValueError('Invalid file ID')
                p=self.store.root/'files'/h
                if not p.exists():return self.reply({'error':'Not found'},404)
                with self.store.connection() as c:r=c.execute('SELECT name,mime FROM files WHERE hash=?',(h,)).fetchone()
                return self.reply(p.read_bytes(),ctype=r[1] if r else 'application/octet-stream')
            if path=='/api/example':
                allowed={'sensor_observations.json','drone_manifest.json','image_metadata.json','rgb_before.png','rgb_after.png','rgb_common_mask.png','ndvi_before.tif','ndvi_after.tif','ndvi_common_mask.tif','inpe_public_sample.geojson'}
                name=q.get('name',[''])[0]
                if name not in allowed or not (ROOT/'examples'/name).is_file():return self.reply({'error':'Example unavailable'},404)
                return self.reply((ROOT/'examples'/name).read_bytes(),ctype=mimetypes.guess_type(name)[0] or 'application/octet-stream',filename=name)
            return self.reply({'error':'Not found'},404)
        except Exception as e:self.reply({'error':str(e)[:600]},400)
    def do_POST(self):
        if not self.host_ok():return self.reply({'error':'Invalid host'},403)
        sensor=self.path=='/api/ingest'
        if not self.auth(sensor):return self.reply({'error':'Invalid receiver token' if sensor else 'Invalid session token'},401)
        origin=self.headers.get('Origin')
        if origin and origin not in (f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'):return self.reply({'error':'Invalid origin'},403)
        try:
            n=int(self.headers.get('Content-Length','0'))
            if n<=0 or n>100*1024*1024:raise ValueError('Request size limit is 100 MiB')
            d=json.loads(self.rfile.read(n))
            result=self.action(self.path,d)
            self.reply(result)
        except Exception as e:self.reply({'error':str(e)[:600]},400)
    def action(self,path,d):
        if path=='/api/demo':return create_demo(self.store)
        if path=='/api/site':self.store.set_site(d);return {'saved':True}
        if path in ('/api/import','/api/ingest'):
            rows=d if isinstance(d,list) else [d]
            if len(rows)>10000:raise ValueError('Import limit: 10000 records')
            out={'inserted':0,'duplicates':0,'errors':[]}
            for i,r in enumerate(rows):
                try:
                    if self.store.add(r):out['inserted']+=1
                    else:out['duplicates']+=1
                except Exception as e:out['errors'].append({'row':i,'reason':str(e)[:250]})
            out['ack']=len(out['errors'])==0;return out
        if path=='/api/drone':
            manifest=d.get('manifest',{})
            if not manifest.get('flight_id') or manifest.get('mode') not in ('DEMO','FIELD'):raise ValueError('Drone manifest requires flight_id and mode')
            rows=manifest.get('observations',[])
            if not rows or any(r.get('source_type')!='drone' or r.get('mode')!=manifest['mode'] for r in rows):raise ValueError('Manifest observations must be drone records with matching mode')
            result=self.action('/api/import',rows)
            self.store.record('drone_manifest',{'mode':manifest['mode'],'flight_id':str(manifest['flight_id'])[:120],'result':result});return result
        if path=='/api/geojson':
            collection=d.get('collection');options=d.get('options',{})
            result=import_geojson(self.store,collection,options)
            source_file=self.store.save_file('imported_collection.geojson',canonical(collection).encode(),'application/geo+json')
            self.store.record('geojson_import',{'mode':options.get('mode','FIELD'),'options':options,'result':result,'source_file':source_file})
            return result
        if path=='/api/inpe':
            data,provenance=fetch_inpe(d['start'],d['end'],d['aoi'],int(d.get('count',200)))
            raw=self.store.save_file('inpe_wfs_response.geojson',canonical(data).encode(),'application/geo+json')
            options=dict(d.get('options',{}),mode='FIELD',aoi=d['aoi'],source_ref=provenance['source_url'],date_field=provenance['date_property'])
            imported=import_geojson(self.store,data,options);self.store.record('inpe_query',{'mode':'FIELD',**provenance,**raw,'result':imported})
            return {'provenance':provenance,'import':imported}
        if path=='/api/attach':
            name,data=decode(d['file']);return self.store.attach(d['id'],name,data)
        if path=='/api/review':
            self.store.review(d['id'],d['reviewer'],d['decision'],d['note']);return {'saved':True}
        if path=='/api/local-ai':return local_anomalies(self.store,d['mode'],d['site_id'],d['metric'])
        if path=='/api/cloud-ai':
            if d.get('consent') is not True:raise ValueError('Explicit cloud-data consent required')
            return gemini(self.store,d['id'])
        if path=='/api/analyze':
            bn,bb=decode(d['before']);an,ab=decode(d['after']);mn,mb=decode(d['mask']);meta=d['metadata']
            if meta.get('mode') not in ('DEMO','FIELD') or meta.get('source_type') not in ('drone','satellite'):raise ValueError('Select DEMO/FIELD and drone/satellite source')
            method=d.get('method')
            if method not in ('rgb','ndvi'):raise ValueError('Method must be rgb or ndvi')
            result,overlay=(rgb_pair if method=='rgb' else ndvi_pair)(bb,ab,mb,meta)
            inputs=[self.store.save_file(n,b) for n,b in ((bn,bb),(an,ab),(mn,mb))]
            overlay_file=self.store.save_file('change_overlay.png',overlay,'image/png')
            oid='image-'+digest(canonical([meta,method,[x['sha256'] for x in inputs]]).encode())[:24]
            obs={'id':oid,'site_id':meta['site_id'],'source_type':'image_analysis','source_ref':meta['source_ref'],'mode':meta['mode'],'timestamp':meta['after_time'],'latitude':result.get('center_wgs84',{}).get('latitude',meta['latitude']),'longitude':result.get('center_wgs84',{}).get('longitude',meta['longitude']),'metric':'vegetation_change_pct','value':result['change_pct'],'quality':'valid','metadata':{'original_source_type':meta['source_type'],'analysis':result,'inputs':inputs,'overlay':overlay_file,'input_metadata':meta}}
            self.store.add(obs);self.store.record('image_analysis',{'id':oid,'mode':meta['mode'],'method':method,'result':result,'overlay':overlay_file});return {'id':oid,'result':result,'overlay':overlay_file}
        raise ValueError('Unknown operation')

def make_server(root,port=8765):
    store=Store(root);token_file=Path(root)/'sensor_token.txt'
    if os.environ.get('SENSOR_TOKEN'):sensor_token=os.environ['SENSOR_TOKEN']
    elif token_file.exists():sensor_token=token_file.read_text().strip()
    else:
        sensor_token=secrets.token_urlsafe(32);token_file.write_text(sensor_token);token_file.chmod(0o600)
    if len(sensor_token)<24:raise ValueError('SENSOR_TOKEN must contain at least 24 characters')
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler);server.store=store;server.session_token=secrets.token_urlsafe(32);server.sensor_token=sensor_token;return server

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765);parser.add_argument('--no-browser',action='store_true');args=parser.parse_args()
    load_env(ROOT/'.env');server=make_server(ROOT/'data',args.port);url=f'http://127.0.0.1:{server.server_port}'
    print('Amazon Forest Sentinel — '+RELEASE+'\nOpen '+url+'\nKeep this terminal open. Ctrl+C stops the local server.\nReceiver token: data/sensor_token.txt (keep private).')
    if not args.no_browser:threading.Timer(1.0,lambda:webbrowser.open(url)).start()
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
