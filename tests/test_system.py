import base64
import io
import json
import os
import sqlite3
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch,MagicMock
import numpy as np
from PIL import Image
from engine import Store,validate,priority,now,digest,canonical
from adapters import import_geojson,url_for,fetch_inpe
from imagery import rgb_pair,ndvi_pair
from demonstration import create_demo
from intelligence import local_anomalies,gemini
from server import make_server,ROOT
from device_client import Outbox
from reporting import report_html,csv_bytes

def record(**kw):
    d={'id':'test-event','site_id':'TEST-SITE','mode':'DEMO','source_type':'sensor','source_ref':'Synthetic test','timestamp':now().isoformat(),'latitude':-3,'longitude':-60,'metric':'temperature_c','value':27,'quality':'valid'};d.update(kw);return d

class Base(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=Store(Path(self.tmp.name)/'store')
class EvidenceTests(Base):
    def test_dedup_and_conflict(self):
        d=record();self.assertTrue(self.store.add(d));self.assertFalse(self.store.add(d))
        with self.assertRaises(ValueError):self.store.add(dict(d,value=29))
    def test_nan_inf_bool_bounds(self):
        for v in (float('nan'),float('inf'),True,71,-21):
            with self.assertRaises(ValueError):validate(record(value=v))
    def test_timestamps(self):
        for t in ('2026-01-01T00:00:00',None,42,(now()+timedelta(hours=2)).isoformat()):
            with self.assertRaises(ValueError):validate(record(timestamp=t))
    def test_coords(self):
        for kw in ({'latitude':91},{'longitude':-181},{'latitude':True}):
            with self.assertRaises(ValueError):validate(record(**kw))
    def test_quality_and_stale(self):
        self.assertEqual(priority(validate(record(quality='invalid')))['level'],'BLOCKED')
        self.assertEqual(priority(validate(record(timestamp=(now()-timedelta(days=3)).isoformat())))['level'],'HISTORICAL')
    def test_valid_zero_not_absence(self):self.assertEqual(priority(validate(record(metric='humidity_pct',value=0)))['level'],'LOW')
    def test_mode_separation(self):
        self.store.add(record());self.store.add(record(id='field',mode='FIELD'));self.assertEqual(len(self.store.rows('DEMO')),1);self.assertEqual(len(self.store.export('FIELD')['observations']),1)
    def test_audit_and_review_history(self):
        self.store.add(record());self.store.review('test-event','reviewer','supported','Checked source');self.store.review('test-event','reviewer','dismissed','Later correction');self.assertTrue(self.store.verify()['ok']);self.assertEqual(len([e for e in self.store.audit() if e['kind']=='human_review']),2)
    def test_edit_detected(self):
        self.store.add(record())
        with self.store.connection() as c:c.execute('UPDATE evidence SET payload=?',('{}',))
        self.assertFalse(self.store.verify()['ok'])
    def test_evidence_deletion_detected(self):
        self.store.add(record())
        with self.store.connection() as c:c.execute('DELETE FROM evidence')
        self.assertFalse(self.store.verify()['ok'])
    def test_chain_edit_detected(self):
        self.store.add(record())
        with self.store.connection() as c:c.execute('UPDATE events SET payload=?',('{}',))
        self.assertFalse(self.store.verify()['ok'])
    def test_file_copy_and_tamper(self):
        self.store.add(record());r=self.store.attach('test-event','../../log.txt',b'original');self.assertEqual(r['filename'],'log.txt');self.assertTrue(self.store.verify()['ok']);(self.store.root/'files'/r['sha256']).write_bytes(b'changed');self.assertFalse(self.store.verify()['ok'])
    def test_sensor_states(self):
        self.store.set_site({'id':'TEST-SITE','mode':'DEMO','latitude':-3,'longitude':-60,'expected_interval_s':10});self.assertEqual(self.store.sites()[0]['status'],'NO_DATA')
        self.store.add(record());self.assertEqual(self.store.sites()[0]['status'],'ACTIVE')
        self.store.add(record(id='invalid',quality='invalid'));self.assertEqual(self.store.sites()[0]['status'],'INVALID')
    def test_site_modes_remain_separate(self):
        for mode in ('DEMO','FIELD'):self.store.set_site({'id':'SAME','mode':mode,'latitude':-3,'longitude':-60,'expected_interval_s':10})
        self.assertEqual(len(self.store.sites()),2)
        self.assertEqual({s['mode'] for s in self.store.sites()},{'DEMO','FIELD'})
    def test_old_sensor_stale(self):
        self.store.set_site({'id':'TEST-SITE','mode':'DEMO','latitude':-3,'longitude':-60,'expected_interval_s':10});self.store.add(record(timestamp=(now()-timedelta(minutes=5)).isoformat()));self.assertEqual(self.store.sites()[0]['status'],'STALE')
    def test_unknown_review(self):
        with self.assertRaises(ValueError):self.store.review('missing','r','supported','checked')
    def test_exports_escape(self):
        self.store.add(record(source_ref='<script>alert(1)</script>',site_id='=1+2'));self.assertNotIn(b'<script>alert(1)</script>',report_html(self.store,'DEMO'));self.assertIn(b"'=1+2",csv_bytes(self.store,'DEMO'))

class GeoTests(Base):
    def collection(self):return {'type':'FeatureCollection','features':[{'type':'Feature','geometry':{'type':'Polygon','coordinates':[[[-60,-3],[-59,-3],[-59,-2],[-60,-2],[-60,-3]]]},'properties':{'gid':'1','view_date':'2026-01-01','classname':'test'}}]}
    def test_intersection_and_duplicate(self):
        opts={'mode':'FIELD','source_ref':'test','aoi':[-60,-3,-59,-2]};r=import_geojson(self.store,self.collection(),opts);self.assertEqual(r['inserted'],1);self.assertEqual(import_geojson(self.store,self.collection(),opts)['duplicates'],1)
    def test_official_overlap_deduplicates(self):
        a={'mode':'FIELD','source_ref':'https://terrabrasilis.dpi.inpe.br/query?count=8'}
        b={'mode':'FIELD','source_ref':'INPE official bundled sample'}
        self.assertEqual(import_geojson(self.store,self.collection(),a)['inserted'],1)
        self.assertEqual(import_geojson(self.store,self.collection(),b)['duplicates'],1)
    def test_outside(self):self.assertEqual(import_geojson(self.store,self.collection(),{'aoi':[-50,-3,-49,-2]})['outside_aoi'],1)
    def test_crs_rejected(self):
        d=self.collection();d['crs']={'properties':{'name':'EPSG:3857'}}
        with self.assertRaises(ValueError):import_geojson(self.store,d,{})
    def test_missing_date_reported(self):
        r=import_geojson(self.store,self.collection(),{'date_field':'not_a_date'});self.assertEqual(len(r['errors']),1);self.assertEqual(r['inserted'],0)
    def test_bbox_and_date_safety(self):
        with self.assertRaises(ValueError):url_for('2026-02-01','2026-01-01',[-60,-3,-59,-2])
        with self.assertRaises(ValueError):url_for('2026-01-01','2026-02-01',[-59,-3,-60,-2])
    def test_bundled_official_sample(self):
        d=json.loads((ROOT/'examples/inpe_public_sample.geojson').read_text());r=import_geojson(self.store,d,{'aoi':[-75,-20,-40,10],'mode':'FIELD','source_ref':'INPE official public sample'});self.assertEqual(r['inserted'],8);self.assertEqual(r['errors'],[])

class ImageTests(Base):
    def setUp(self):
        super().setUp();self.meta=json.loads((ROOT/'examples/image_metadata.json').read_text())
    def data(self,name):return (ROOT/'examples'/name).read_bytes()
    def test_rgb_known_change(self):
        m=dict(self.meta,threshold=.15,baseline=.1);r,out=rgb_pair(self.data('rgb_before.png'),self.data('rgb_after.png'),self.data('rgb_common_mask.png'),m);self.assertEqual(r['changed_pixels'],10000);self.assertEqual(r['baseline_pixels'],57600);self.assertIsNone(r['area_ha']);self.assertTrue(out.startswith(b'\x89PNG'))
    def test_ndvi_known_change_and_area(self):
        r,out=ndvi_pair(self.data('ndvi_before.tif'),self.data('ndvi_after.tif'),self.data('ndvi_common_mask.tif'),self.meta);self.assertEqual(r['changed_pixels'],10000);self.assertEqual(r['area_ha'],100)
    def test_missing_mask(self):
        with self.assertRaises(ValueError):rgb_pair(self.data('rgb_before.png'),self.data('rgb_after.png'),None,self.meta)
    def test_alignment_gate(self):
        with self.assertRaises(ValueError):rgb_pair(self.data('rgb_before.png'),self.data('rgb_after.png'),self.data('rgb_common_mask.png'),dict(self.meta,aligned=False))
    def test_mask_excludes_change(self):
        m=np.ones((240,240),dtype='uint8')*255;m[60:160,80:180]=0;b=io.BytesIO();Image.fromarray(m).save(b,format='PNG');r,_=rgb_pair(self.data('rgb_before.png'),self.data('rgb_after.png'),b.getvalue(),dict(self.meta,threshold=.15,baseline=.1));self.assertEqual(r['changed_pixels'],0);self.assertEqual(r['valid_pixels'],47600)
    def test_dates_gate(self):
        with self.assertRaises(ValueError):rgb_pair(self.data('rgb_before.png'),self.data('rgb_after.png'),self.data('rgb_common_mask.png'),dict(self.meta,after_time=self.meta['before_time']))
    def test_grid_mismatch(self):
        from rasterio.io import MemoryFile
        from rasterio.transform import from_origin
        with MemoryFile() as mem:
            with mem.open(driver='GTiff',width=240,height=240,count=2,dtype='float32',crs='EPSG:32721',transform=from_origin(500010,9657500,10,10)) as ds:ds.write(np.ones((2,240,240),dtype='float32')*.2)
            data=mem.read()
        with self.assertRaises(ValueError):ndvi_pair(self.data('ndvi_before.tif'),data,self.data('ndvi_common_mask.tif'),self.meta)

class IntelligenceTests(Base):
    def test_local_chronological_holdout(self):
        create_demo(self.store);r=local_anomalies(self.store,'DEMO','DEMO-RIVER','temperature_c');self.assertEqual(r['training_count'],50);self.assertEqual(r['evaluation_count'],10);self.assertTrue(any(v['anomaly'] for v in r['findings']));self.assertTrue(self.store.verify()['ok'])
    def history(self,baseline,evaluation,root=None):
        store=self.store if root is None else Store(Path(self.tmp.name)/root)
        base=now()-timedelta(hours=1)
        for i,value in enumerate(list(baseline)+list(evaluation)):
            store.add(record(id='synthetic-'+str(i),value=float(value),
                             timestamp=(base+timedelta(seconds=i)).isoformat()))
        return store
    def test_demo_discriminates_expected_pulses(self):
        create_demo(self.store)
        r=local_anomalies(self.store,'DEMO','DEMO-RIVER','temperature_c')
        self.assertEqual([f['anomaly'] for f in r['findings']],[False]*7+[True]*3)
        self.assertEqual(r['summary'],{'anomalies':3,'not_flagged':7})
        self.assertTrue(all(f['decision_score']>0 for f in r['findings'][:7]))
        self.assertTrue(all(f['decision_score']<0 for f in r['findings'][7:]))
    def test_independent_normal_holdout(self):
        rng=np.random.default_rng(218)
        baseline=25+rng.normal(0,1.4,100)
        evaluation=[24.8,25.2,24.1,25.8,26.1,23.9,25.6,24.5,26.2,25.0]
        self.history(baseline,evaluation)
        r=local_anomalies(self.store,'DEMO','TEST-SITE','temperature_c')
        self.assertEqual(r['summary']['anomalies'],0)
    def test_high_and_low_excursions_independent_fixture(self):
        baseline=25+1.5*np.sin(np.arange(70)*.63)
        self.history(baseline,[24,26,25,24.5,25.5,25.3,24.2,45,-10,50])
        r=local_anomalies(self.store,'DEMO','TEST-SITE','temperature_c')
        self.assertEqual([f['anomaly'] for f in r['findings']],[False]*7+[True]*3)
    def test_shifted_scaled_baseline(self):
        baseline=37+3*np.sin(np.arange(80)*.71)
        self.history(baseline,[36,38,37,35.5,38.5,36.2,37.8,65,10,66])
        r=local_anomalies(self.store,'DEMO','TEST-SITE','temperature_c')
        self.assertEqual([f['anomaly'] for f in r['findings']],[False]*7+[True]*3)
    def test_evaluation_does_not_fit_baseline(self):
        baseline=27+np.sin(np.arange(60)*.71)
        a=self.history(baseline,[27]*10)
        b=self.history(baseline,[60]*10,root='independent')
        ra=local_anomalies(a,'DEMO','TEST-SITE','temperature_c')
        rb=local_anomalies(b,'DEMO','TEST-SITE','temperature_c')
        self.assertEqual(ra['baseline'],rb['baseline'])
        self.assertEqual(ra['training_ids_sha256'],rb['training_ids_sha256'])
    def test_zero_mad_is_not_a_fabricated_scale(self):
        self.history([27]*48+[26,28],[27]*10)
        with self.assertRaisesRegex(ValueError,'robust variation'):
            local_anomalies(self.store,'DEMO','TEST-SITE','temperature_c')
    def test_tied_partition_times_rejected(self):
        for i in range(40):self.store.add(record(id='tie-'+str(i),value=26+i%4,timestamp='2026-11-01T10:00:00Z'))
        with self.assertRaisesRegex(ValueError,'separated observation times'):
            local_anomalies(self.store,'DEMO','TEST-SITE','temperature_c')
    def test_insufficient_history(self):
        with self.assertRaises(ValueError):local_anomalies(self.store,'FIELD','missing','temperature_c')
    def test_cloud_minimizes_data_and_keeps_priority(self):
        self.store.add(record());response=MagicMock();response.__enter__.return_value=response;response.read.return_value=b'{"candidates":[{"content":{"parts":[{"text":"Check the evidence."}]}}]}'
        with patch('urllib.request.urlopen',return_value=response) as call:
            r=gemini(self.store,'test-event',key='fake-key',model='test-model');prompt=json.loads(call.call_args.args[0].data)['contents'][0]['parts'][0]['text'];self.assertNotIn('latitude',prompt);self.assertNotIn('site_id',prompt);self.assertNotIn('test-event',prompt);self.assertEqual(r['text'],'Check the evidence.')
        self.assertEqual(self.store.rows()[0]['priority']['level'],'LOW')
    def test_cloud_no_credentials(self):
        self.store.add(record())
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(ValueError):gemini(self.store,'test-event')

class HTTPTests(Base):
    def setUp(self):
        super().setUp();self.server=make_server(Path(self.tmp.name)/'http',0);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.url='http://127.0.0.1:'+str(self.server.server_port)
        self.addCleanup(self.close)
    def close(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=3)
    def request(self,path,data=None,token=True,sensor=False):
        headers={'Content-Type':'application/json'}
        if token:headers['Authorization' if sensor else 'X-Session-Token']=('Bearer '+self.server.sensor_token) if sensor else self.server.session_token
        req=urllib.request.Request(self.url+path,data=json.dumps(data).encode() if data is not None else None,headers=headers)
        with urllib.request.urlopen(req,timeout=5) as r:return r.status,r.read()
    def test_ui_loads(self):self.assertIn(b'Forest overview',self.request('/')[1])
    def test_auth_gate(self):
        with self.assertRaises(urllib.error.HTTPError) as cm:self.request('/api/state',token=False)
        self.assertEqual(cm.exception.code,401)
    def test_ingest_ack_duplicate(self):
        d=record();_,b=self.request('/api/ingest',d,sensor=True);self.assertTrue(json.loads(b)['ack']);_,b=self.request('/api/ingest',d,sensor=True);self.assertEqual(json.loads(b)['duplicates'],1)
    def test_ingest_rejects_invalid_without_ack(self):
        _,b=self.request('/api/ingest',record(value=999),sensor=True);r=json.loads(b);self.assertFalse(r['ack']);self.assertEqual(r['inserted'],0)
    def test_outbox_delivery_and_retries(self):
        q=Outbox(Path(self.tmp.name)/'outbox.sqlite3');q.put(record());self.assertEqual(q.flush(self.url,'wrong'),0);self.assertEqual(q.flush(self.url,self.server.sensor_token),1);self.assertEqual(q.flush(self.url,self.server.sensor_token),0)
    def test_site_receiver_and_export(self):
        self.request('/api/site',{'id':'TEST-SITE','mode':'DEMO','latitude':-3,'longitude':-60,'expected_interval_s':10});self.request('/api/ingest',record(),sensor=True);_,b=self.request('/api/state?mode=DEMO');self.assertEqual(json.loads(b)['sites'][0]['status'],'ACTIVE');_,b=self.request('/api/export?mode=DEMO');self.assertEqual(len(json.loads(b)['observations']),1)
    def test_local_ai_endpoint_reports_seven_regular_three_excursions(self):
        create_demo(self.server.store)
        _,body=self.request('/api/local-ai',{'mode':'DEMO','site_id':'DEMO-RIVER','metric':'temperature_c'})
        result=json.loads(body)
        self.assertEqual(result['summary'],{'anomalies':3,'not_flagged':7})
        self.assertEqual(result['baseline']['fitted_on'],'training observations only')
        self.assertEqual(result['algorithm_revision'],'iforest-mad-guard-1')
    def test_full_image_workflow(self):
        enc=lambda name:{'name':name,'data':base64.b64encode((ROOT/'examples'/name).read_bytes()).decode()}
        m=json.loads((ROOT/'examples/image_metadata.json').read_text());m.update(threshold=.15,baseline=.1)
        _,b=self.request('/api/analyze',{'method':'rgb','before':enc('rgb_before.png'),'after':enc('rgb_after.png'),'mask':enc('rgb_common_mask.png'),'metadata':m});r=json.loads(b);self.assertEqual(r['result']['changed_pixels'],10000);self.assertEqual(self.request(r['overlay']['url'])[0],200)
    def test_origin_gate(self):
        req=urllib.request.Request(self.url+'/api/demo',data=b'{}',headers={'X-Session-Token':self.server.session_token,'Origin':'https://example.org','Content-Type':'application/json'})
        with self.assertRaises(urllib.error.HTTPError) as cm:urllib.request.urlopen(req)
        self.assertEqual(cm.exception.code,403)

if __name__=='__main__':unittest.main(verbosity=2)
