import os

def read_file(path):
    try:
        with open(path,'r') as f:
            return f.read().strip()
    except Exception as e:
        print(f"MISSING: {path} ({e})")
        return None

token = read_file('token.txt')
channel = read_file('channel_id.txt')

ok = True
if not token:
    ok = False
else:
    if len(token) < 10:
        print('WARN: token looks short')

if not channel:
    ok = False
else:
    try:
        cid = int(channel)
    except Exception:
        print('ERROR: channel_id is not an integer')
        ok = False

if ok:
    masked = token[:6] + '...' + token[-6:]
    print('TOKEN:', masked)
    print('CHANNEL_ID:', channel)
    print('Config OK')
else:
    print('Config invalid')
