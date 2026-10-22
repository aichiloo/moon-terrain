"""Verify the complete release against its bundled SHA-256 manifest."""
from pathlib import Path
import argparse
import hashlib
import json

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]/'demo')
    args=parser.parse_args()
    root=args.root.resolve()
    manifest=root/'SHA256SUMS.txt'
    if not manifest.exists():raise SystemExit('Download the demo first.')
    count=0
    for line in manifest.read_text(encoding='utf-8').splitlines():
        expected,name=line.split('  ',1)
        target=(root/name).resolve()
        if not target.is_relative_to(root):raise ValueError('Unsafe manifest path')
        if hashlib.sha256(target.read_bytes()).hexdigest()!=expected:raise SystemExit('Hash mismatch: '+name)
        count+=1
    print(json.dumps({'passed':True,'files_verified':count,'scope':'File integrity only; not a physics or navigation test.'}))

if __name__=='__main__':main()
