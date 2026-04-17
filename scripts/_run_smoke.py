import json, time
from urllib import request, error
base = 'http://127.0.0.1:6666'
out = []
def call(method, path, body=None, headers=None):
    url = base + path
    data = None
    req_headers = {'Content-Type': 'application/json'}
    if headers:
        req_headers.update(headers)
    if body is not None:
        data = json.dumps(body).encode('utf-8')
    req = request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode('utf-8')
            try:
                payload = json.loads(raw)
            except Exception:
                payload = raw
            return resp.status, payload
    except error.HTTPError as e:
        raw = e.read().decode('utf-8')
        try:
            payload = json.loads(raw)
        except Exception:
            payload = raw
        return e.code, payload
    except Exception as e:
        return None, str(e)
# wait health
for _ in range(60):
    st, pl = call('GET', '/health', body=None, headers={})
    if st == 200:
        out.append({'health': {'status': st, 'body': pl}})
        break
    time.sleep(2)
else:
    out.append({'health': {'status': st, 'body': pl}})
# chat
st, pl = call('POST', '/chat', {'message':'smoke test feedback','session_id':'','history':[]})
out.append({'chat': {'status': st, 'body': pl}})
sid = None
if isinstance(pl, dict):
    sid = pl.get('session_id')
# feedback turn
if sid:
    st2, pl2 = call('POST', '/feedback', {'session_id': sid, 'rating':'like', 'comment':'smoke'})
    out.append({'feedback': {'status': st2, 'body': pl2}})
    st3, pl3 = call('POST', '/feedback/end', {'session_id': sid, 'rating':5, 'comment':'smoke end', 'tags':['helpful']})
    out.append({'feedback_end': {'status': st3, 'body': pl3}})
# trainer endpoints
trainer = ''
with open(r'E:\Working\VinUni-FinalProj\VinMec-v2-kafka\.env', 'r', encoding='utf-8') as f:
    for line in f:
        if line.startswith('TRAINER_API_KEY='):
            trainer = line.split('=',1)[1].strip().strip('"')
            break
if trainer:
    h = {'X-Trainer-Key': trainer}
    for path in ['/feedback?limit=5', '/feedback/stats', '/feedback/search?q=smoke&limit=3', '/feedback/end?limit=5', '/feedback/end/stats']:
        stx, plx = call('GET', path, headers=h)
        out.append({path: {'status': stx, 'body': plx}})
else:
    out.append({'trainer_tests': 'skipped_no_key'})
with open(r'E:\Working\VinUni-FinalProj\VinMec-v2-kafka\scripts\_api_smoke_result.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=True, indent=2)
