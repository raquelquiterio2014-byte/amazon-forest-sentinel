"""Durable local device bridge: replay JSON or forward serial JSON lines."""
import argparse
import json
import sqlite3
import time
import urllib.request
from datetime import datetime,timezone
from pathlib import Path
from engine import validate

class Outbox:
    def __init__(self,path):
        self.path=str(path)
        with sqlite3.connect(self.path) as c:c.execute('CREATE TABLE IF NOT EXISTS queue(id TEXT PRIMARY KEY,payload TEXT NOT NULL,attempts INTEGER DEFAULT 0,error TEXT DEFAULT "")')
    def put(self,record):
        d=validate(record);p=json.dumps(d,sort_keys=True)
        with sqlite3.connect(self.path) as c:
            old=c.execute('SELECT payload FROM queue WHERE id=?',(d['id'],)).fetchone()
            if old and old[0]!=p:raise ValueError('Queued event ID conflict')
            c.execute('INSERT OR IGNORE INTO queue(id,payload) VALUES(?,?)',(d['id'],p))
    def flush(self,url,token):
        with sqlite3.connect(self.path) as c:rows=c.execute('SELECT id,payload FROM queue ORDER BY rowid LIMIT 100').fetchall()
        delivered=0
        for oid,payload in rows:
            try:
                req=urllib.request.Request(url+'/api/ingest',data=payload.encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+token},method='POST')
                with urllib.request.urlopen(req,timeout=15) as r:ack=json.load(r)
                if not ack.get('ack'):raise ValueError('Receiver rejected event: '+str(ack.get('errors')))
                with sqlite3.connect(self.path) as c:c.execute('DELETE FROM queue WHERE id=?',(oid,))
                delivered+=1
            except Exception as e:
                with sqlite3.connect(self.path) as c:c.execute('UPDATE queue SET attempts=attempts+1,error=? WHERE id=?',(type(e).__name__+': '+str(e)[:150],oid))
        return delivered

def main():
    p=argparse.ArgumentParser();p.add_argument('--replay',type=Path);p.add_argument('--serial');p.add_argument('--baud',type=int,default=115200);p.add_argument('--url',default='http://127.0.0.1:8765');p.add_argument('--token-file',type=Path,default=Path(__file__).resolve().parent/'data/sensor_token.txt');p.add_argument('--queue',type=Path,default=Path(__file__).resolve().parent/'data/device_outbox.sqlite3');p.add_argument('--refresh-demo-time',action='store_true');p.add_argument('--retry',action='store_true');args=p.parse_args()
    args.queue.parent.mkdir(parents=True,exist_ok=True);q=Outbox(args.queue);token=args.token_file.read_text().strip()
    if args.replay:
        records=json.loads(args.replay.read_text())
        if not isinstance(records,list):raise ValueError('Replay needs JSON array')
        for r in records:
            if args.refresh_demo_time:
                if r.get('mode')!='DEMO':raise ValueError('Time refresh only permitted for DEMO records')
                r['timestamp']=datetime.now(timezone.utc).isoformat();r['id']=r['id']+'-'+str(time.time_ns())
            q.put(r)
    if args.serial:
        import serial
        with serial.Serial(args.serial,args.baud,timeout=2) as port:
            print('Forwarding JSON lines. Ctrl+C to stop; queued records survive restarts.')
            while True:
                line=port.readline(65536)
                if line:
                    try:q.put(json.loads(line))
                    except Exception as e:print('Rejected serial record:',str(e)[:180])
                print('ACK count:',q.flush(args.url,token));time.sleep(.1)
    else:
        print('ACK count:',q.flush(args.url,token))
        if args.retry:
            while True:time.sleep(5);print('ACK count:',q.flush(args.url,token))

if __name__=='__main__':main()
