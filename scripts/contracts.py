#!/usr/bin/env python3
"""Generate public API types and scenario schema, or verify reproducible drift."""
import argparse
from pathlib import Path
import subprocess
import tempfile
import os
import shutil
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
with tempfile.TemporaryDirectory(prefix='workquest-contracts-') as folder:
    target=Path(folder)
    env={**os.environ,'CONTRACT_OUTPUT':str(target)}
    subprocess.run(['uv','run','python','-m','app.cli.export_contracts'],cwd=root/'apps/api',env=env,check=True)
    types=target/'api-types.ts'
    subprocess.run(['pnpm','exec','openapi-typescript',str(target/'openapi.json'),'-o',str(types)],cwd=root/'apps/web',check=True)
    subprocess.run(['pnpm','exec','prettier','--write',str(types)],cwd=root/'apps/web',check=True,stdout=subprocess.DEVNULL)
    for source,destination in [(target/'openapi.json',root/'packages/contracts/openapi.json'),(target/'scenario.schema.json',root/'packages/contracts/scenario.schema.json'),(types,root/'apps/web/src/generated/api-types.ts')]:
        if args.check:
            if not destination.exists() or source.read_bytes()!=destination.read_bytes():
                raise SystemExit(f'Contract drift: {destination.relative_to(root)}. Run make contracts and review the diff.')
        else:
            destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination)
print('Contract check passed.' if args.check else 'Contracts regenerated.')
