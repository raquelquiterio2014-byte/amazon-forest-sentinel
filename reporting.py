import csv
import html
import io
import json
from collections import Counter
from engine import stamp

def csv_bytes(store,mode):
    fields=['id','site_id','mode','source_type','timestamp','latitude','longitude','metric','value','quality','priority','sha256','source_ref']
    out=io.StringIO(newline='');w=csv.DictWriter(out,fieldnames=fields);w.writeheader()
    for d in store.rows(mode):w.writerow({k:(d['priority']['level'] if k=='priority' else d.get(k,'')) for k in fields})
    # Protect spreadsheet applications from formula evaluation in string cells.
    rows=list(csv.reader(io.StringIO(out.getvalue())))
    cleaned=io.StringIO(newline='');writer=csv.writer(cleaned)
    for row in rows:writer.writerow(["'"+c if c[:1] in ('=','+','@') or (c.startswith('-') and not _numeric(c)) else c for c in row])
    return ('\ufeff'+cleaned.getvalue()).encode('utf-8')
def _numeric(v):
    try:float(v);return True
    except ValueError:return False

def report_html(store,mode):
    ex=store.export(mode);rows=ex['observations'];counts=Counter(d['priority']['level'] for d in rows);esc=lambda s:html.escape(str(s))
    table=''.join('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in (d['id'],d['source_type'],d['timestamp'],d['metric'],d['value'],d['priority']['level'],d['source_ref']))+'</tr>' for d in rows)
    reviews=[e for e in ex['events'] if e['kind']=='human_review']
    notes=''.join('<li>'+esc(e['timestamp'])+' — '+esc(e['payload'])+'</li>' for e in reviews)
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>Amazon Forest Sentinel — Evidence Report</title><style>body{{font:14px Arial;margin:32px;color:#14372b}}table{{border-collapse:collapse;width:100%;font-size:11px}}td,th{{border:1px solid #bed2c6;padding:6px;text-align:left;overflow-wrap:anywhere}}h1{{color:#125c3a}}@media print{{body{{margin:12mm}}}}</style><h1>Amazon Forest Sentinel</h1><h2>Evidence and verification report — {esc(mode)}</h2><p>Generated: {esc(stamp())}</p><p>Observations: {len(rows)} | Priorities: {esc(dict(counts))}</p><p><b>Educational decision support. Thresholds and image screening are not validated deforestation detection. No proof of illegal activity or avoided deforestation. DEMO records are synthetic; FIELD is uploader-declared.</b></p><table><tr><th>ID</th><th>Source</th><th>Observed</th><th>Metric</th><th>Value</th><th>Priority</th><th>Provenance</th></tr>{table}</table><h2>Human reviews</h2><ul>{notes or '<li>No reviews recorded.</li>'}</ul><h2>Integrity</h2><p>{esc(ex['audit_check'])}</p><p>Print this standalone report to PDF from your browser. Preserve the JSON export and original source files for reproducibility. Local hashes do not prove authenticity.</p></html>'''.encode()
