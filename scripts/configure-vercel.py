"""Set the public Render origin in Vercel's same-origin API rewrite. No secrets."""
import argparse,json
from pathlib import Path
from urllib.parse import urlsplit
parser=argparse.ArgumentParser();parser.add_argument('--api-origin',required=True);args=parser.parse_args()
origin=urlsplit(args.api_origin)
if origin.scheme!='https' or not origin.hostname or origin.username or origin.password or origin.path not in ('','/') or origin.query or origin.fragment:
    parser.error('Use an HTTPS origin with no credentials, path, query or fragment')
root=Path(__file__).resolve().parent.parent
p=root/'vercel.json';data=json.loads(p.read_text());data['rewrites'][0]['destination']=args.api_origin.rstrip('/')+'/api/:path*';p.write_text(json.dumps(data,indent=2)+'\n')
print('Updated vercel.json. Set the exact final Vercel origin as APP_ORIGIN in Render before use.')
