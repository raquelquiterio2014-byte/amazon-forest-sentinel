"""Local evidence storage, audit chain and explicit verification priorities."""
import hashlib
import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

RELEASE='Final educational release'
UNITS={'temperature_c':('C',-20,70),'humidity_pct':('%',0,100),'acoustic_activity_index':('index',0,1),'vegetation_change_pct':('%',0,100),'satellite_alert':('flag',0,1)}

def now():return datetime.now(timezone.utc)
def stamp():return now().isoformat()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def digest(b):return hashlib.sha256(b).hexdigest()
def number(v,lo,hi,name):
    if isinstance(v,bool):raise ValueError(name+' must be numeric')
    try:n=float(v)
    except (ValueError,TypeError):raise ValueError(name+' must be numeric')
    if not math.isfinite(n) or not lo<=n<=hi:raise ValueError(name+' out of range')
    return n

def text(v,name,limit=500):
    if not isinstance(v,str) or not v.strip() or len(v)>limit:raise ValueError('Invalid '+name)
    return v.strip()
def time_value(v):
    try:d=datetime.fromisoformat(v.replace('Z','+00:00'))
    except (ValueError,TypeError,AttributeError):raise ValueError('Invalid ISO 8601 timestamp')
    if not d.tzinfo:raise ValueError('Timestamp must include timezone')
    if (d-now()).total_seconds()>300:raise ValueError('Future timestamp')
    return d.astimezone(timezone.utc).isoformat()

def validate(raw):
    if not isinstance(raw,dict):raise ValueError('Observation must be an object')
    keys=['id','site_id','source_type','source_ref','mode','timestamp','latitude','longitude','metric','value','quality']
    if any(k not in raw for k in keys):raise ValueError('Missing fields: '+', '.join(k for k in keys if k not in raw))
    d={k:raw[k] for k in keys}
    for k in ['id','site_id','source_ref']:d[k]=text(d[k],k)
    if d['mode'] not in ('DEMO','FIELD'):raise ValueError('mode must be DEMO or FIELD')
    if d['source_type'] not in ('satellite','drone','sensor','manual','image_analysis'):raise ValueError('Invalid source_type')
    if d['quality'] not in ('valid','invalid'):raise ValueError('Invalid quality')
    if d['metric'] not in UNITS:raise ValueError('Unsupported metric')
    d['timestamp']=time_value(d['timestamp'])
    d['latitude']=number(d['latitude'],-90,90,'latitude'); d['longitude']=number(d['longitude'],-180,180,'longitude')
    _,lo,hi=UNITS[d['metric']];d['value']=number(d['value'],lo,hi,'value')
    if d['metric']=='satellite_alert' and d['value'] not in (0,1):raise ValueError('satellite_alert must be 0 or 1')
    d['metadata']=raw.get('metadata',{})
    if not isinstance(d['metadata'],dict) or len(canonical(d['metadata']))>30000:raise ValueError('Invalid metadata')
    geometry=raw.get('geometry')
    if geometry is not None:
        from shapely.geometry import shape, mapping
        g=shape(geometry)
        if g.is_empty or not g.is_valid or g.geom_type not in ('Point','Polygon','MultiPolygon'):raise ValueError('Invalid geometry')
        a,b,c,e=g.bounds
        if not(-180<=a<=c<=180 and -90<=b<=e<=90):raise ValueError('Geometry coordinates outside WGS84 range')
        d['geometry']=mapping(g)
    return d

def priority(d,current=None):
    age=((current or now())-datetime.fromisoformat(d['timestamp'])).total_seconds()/3600
    p,r='LOW','No configured trigger; absence of a trigger does not establish safety.'
    if d['quality']!='valid':p,r='BLOCKED','Invalid upstream measurement.'
    elif age>48:p,r='HISTORICAL','Older than 48 h; inspect as historical evidence, not a current emergency.'
    elif d['metric']=='satellite_alert' and d['value']==1:p,r='HIGH','Published vegetation-change alert; requires contextual review, not proof of illegality.'
    elif d['metric']=='vegetation_change_pct' and d['value']>=10:p,r='HIGH','Vegetation-change screening threshold (10%) exceeded; inspect masks and imagery.'
    elif d['metric']=='acoustic_activity_index' and d['value']>=0.8:p,r='MEDIUM','Supplied activity index >=0.8; sound source is unidentified.'
    elif d['metric']=='temperature_c' and d['value']>=40:p,r='MEDIUM','Temperature >=40 C; nonspecific environmental signal.'
    return {'level':p,'reason':r,'age_hours':round(age,2),'rule':'educational-fixed-thresholds','probability':None}

class Store:
    def __init__(self,root):
        self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True);(self.root/'files').mkdir(exist_ok=True)
        self.db=self.root/'forest.sqlite3'
        with self.connection() as c:
            c.executescript('''PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS evidence(id TEXT PRIMARY KEY,payload TEXT NOT NULL,hash TEXT NOT NULL,received TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY,kind TEXT NOT NULL,payload TEXT NOT NULL,timestamp TEXT NOT NULL,previous_hash TEXT NOT NULL,hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sites(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS files(hash TEXT PRIMARY KEY,name TEXT NOT NULL,mime TEXT NOT NULL,bytes INTEGER NOT NULL);
''')
    def connection(self):return sqlite3.connect(self.db,timeout=20)
    def event(self,c,kind,payload):
        prev=c.execute('SELECT hash FROM events ORDER BY seq DESC LIMIT 1').fetchone();prev=prev[0] if prev else '0'*64
        p=canonical(payload);t=stamp();h=digest(canonical([kind,p,t,prev]).encode())
        c.execute('INSERT INTO events(kind,payload,timestamp,previous_hash,hash) VALUES(?,?,?,?,?)',(kind,p,t,prev,h))
    def add(self,raw):
        d=validate(raw);p=canonical(d);h=digest(p.encode())
        with self.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            old=c.execute('SELECT hash FROM evidence WHERE id=?',(d['id'],)).fetchone()
            if old:
                if old[0]!=h:raise ValueError('ID conflict: same ID with different content')
                return False
            c.execute('INSERT INTO evidence VALUES(?,?,?,?)',(d['id'],p,h,stamp()));self.event(c,'evidence_added',{'id':d['id'],'hash':h})
        return True
    def rows(self,mode=None):
        with self.connection() as c:rs=c.execute('SELECT payload,hash,received FROM evidence ORDER BY received DESC').fetchall()
        return [dict(json.loads(p),sha256=h,received=t,priority=priority(json.loads(p))) for p,h,t in rs if mode is None or json.loads(p)['mode']==mode]
    def get(self,oid):
        with self.connection() as c:r=c.execute('SELECT payload FROM evidence WHERE id=?',(oid,)).fetchone()
        if not r:raise ValueError('Unknown observation')
        return json.loads(r[0])
    def audit(self):
        with self.connection() as c:
            c.row_factory=sqlite3.Row;rs=[dict(r) for r in c.execute('SELECT * FROM events ORDER BY seq')]
        for r in rs:r['payload']=json.loads(r['payload'])
        return rs
    def verify(self):
        prev='0'*64;count=0
        for e in self.audit():
            h=digest(canonical([e['kind'],canonical(e['payload']),e['timestamp'],prev]).encode())
            if h!=e['hash'] or e['previous_hash']!=prev:return {'ok':False,'event':e['seq']}
            prev=e['hash'];count+=1
        expected={e['payload']['id']:e['payload']['hash'] for e in self.audit() if e['kind']=='evidence_added'}
        with self.connection() as c:
            actual={oid:h for oid,h in c.execute('SELECT id,hash FROM evidence')}
            if actual!=expected:return {'ok':False,'reason':'Evidence inventory differs from audit history'}
            for oid,p,h in c.execute('SELECT id,payload,hash FROM evidence'):
                if digest(p.encode())!=h:return {'ok':False,'evidence_id':oid}
            for h,name,mime,size in c.execute('SELECT * FROM files'):
                path=self.root/'files'/h
                if not path.exists() or digest(path.read_bytes())!=h:return {'ok':False,'file':h}
        return {'ok':True,'events_checked':count,'chain_head':prev,'limitation':'Local hash chain detects accidental edits; it is not externally anchored and cannot prove authenticity.'}
    def record(self,kind,payload):
        with self.connection() as c:c.execute('BEGIN IMMEDIATE');self.event(c,kind,payload)
    def review(self,oid,reviewer,decision,note):
        self.get(oid)
        if decision not in ('needs_verification','supported','dismissed'):raise ValueError('Invalid review decision')
        self.record('human_review',{'id':oid,'reviewer':text(reviewer,'reviewer',100),'decision':decision,'note':text(note,'rationale',4000)})
    def save_file(self,name,data,mime='application/octet-stream'):
        if not data or len(data)>32*1024*1024:raise ValueError('File must be 1 byte to 32 MiB')
        h=digest(data);safe=Path(name).name[:160];path=self.root/'files'/h
        if not path.exists():path.write_bytes(data)
        with self.connection() as c:c.execute('INSERT OR IGNORE INTO files VALUES(?,?,?,?)',(h,safe,mime,len(data)))
        return {'sha256':h,'filename':safe,'size':len(data),'url':'/files/'+h}
    def attach(self,oid,name,data):
        self.get(oid);f=self.save_file(name,data);self.record('attachment',{'id':oid,**f});return f
    def set_site(self,d):
        site={'id':text(d.get('id'),'site ID',100),'mode':d.get('mode'),'latitude':number(d.get('latitude'),-90,90,'latitude'),'longitude':number(d.get('longitude'),-180,180,'longitude'),'expected_interval_s':number(d.get('expected_interval_s'),10,604800,'interval')}
        if site['mode'] not in ('DEMO','FIELD'):raise ValueError('Invalid mode')
        with self.connection() as c:c.execute('INSERT OR REPLACE INTO sites VALUES(?,?)',(site['mode']+':'+site['id'],canonical(site)));self.event(c,'site_configured',site)
    def sites(self):
        with self.connection() as c:sites=[json.loads(x[0]) for x in c.execute('SELECT payload FROM sites')]
        rows=self.rows()
        for site in sites:
            matches=[d for d in rows if d['source_type']=='sensor' and d['site_id']==site['id'] and d['mode']==site['mode']]
            valid=[d for d in matches if d['quality']=='valid']
            latest=max(matches,key=lambda d:d['timestamp']) if matches else None
            last_valid=max(valid,key=lambda d:d['timestamp']) if valid else None
            age=(now()-datetime.fromisoformat(latest['timestamp'])).total_seconds() if latest else None
            if age is None:status='NO_DATA'
            elif age>max(60,3*site['expected_interval_s']):status='STALE'
            elif latest['quality']=='invalid':status='INVALID'
            else:status='ACTIVE'
            site.update(status=status,age_s=round(age,1) if age is not None else None,last_valid=last_valid['timestamp'] if last_valid else None)
        return sites
    def export(self,mode=None):
        rows=self.rows(mode);ids={d['id'] for d in rows}
        events=self.audit()
        if mode:events=[e for e in events if e['payload'].get('id') in ids or e['payload'].get('mode')==mode]
        return {'release':RELEASE,'exported_at':stamp(),'mode':mode,'observations':rows,'events':events,'sites':[s for s in self.sites() if mode is None or s['mode']==mode],'audit_check':self.verify(),'limitations':'Verification support only. No proof of illegality or avoided deforestation. Site IDs and FIELD labels are uploader declarations.'}
