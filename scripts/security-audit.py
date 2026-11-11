"""Bounded package audits and a redacted scan of tracked + unignored source files."""
from pathlib import Path
import json,re,subprocess,sys
root=Path(__file__).resolve().parent.parent
artifacts=root/'artifacts';artifacts.mkdir(exist_ok=True)
results={}
for label,command,cwd in [('frontend',['pnpm','audit','--prod','--json'],root),('python',['uv','run','pip-audit','--format','json'],root/'apps/api')]:
    result=subprocess.run(command,cwd=cwd,capture_output=True,text=True)
    (artifacts/f'audit-{label}.json').write_text(result.stdout)
    (artifacts/f'audit-{label}-stderr.txt').write_text(result.stderr)
    results[label]={'exit_code':result.returncode,'report':f'artifacts/audit-{label}.json'}
files=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=root).decode().split('\0')
patterns=[r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',r'AIza[0-9A-Za-z_-]{35}',r'gh[pousr]_[A-Za-z0-9]{30,}',r'sk-[A-Za-z0-9_-]{35,}']
findings=[]
for name in files:
    p=root/name
    if not name or not p.is_file():continue
    try:lines=p.read_text().splitlines()
    except UnicodeError:continue
    for number,line in enumerate(lines,1):
        if any(re.search(pattern,line) for pattern in patterns):findings.append({'file':name,'line':number,'kind':'credential-shaped literal; value redacted'})
results['secret_scan']={'findings':findings,'scope':'tracked + unignored source; known private-key/API-token patterns, not an exhaustive entropy scan'}
(artifacts/'audit-summary.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
if findings or any(results[k]['exit_code'] for k in ['frontend','python']):raise SystemExit(1)
