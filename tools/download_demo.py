"""Download the checked offline demo without placing large assets in Git history."""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import shutil
import urllib.request
import zipfile

REPO = Path(__file__).resolve().parents[1]
URL = 'https://github.com/moonspace123/moon-terrain/releases/download/v0.1.0/Lunar_Detail_Regions_03.zip'
SHA256 = 'ced7ff4d8f11e35f970ca5328d5c69ab9f2bced6a2a6e4abe4d00067dc20e5ce'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,help='Use a previously downloaded release ZIP')
    args=parser.parse_args()
    archive=args.archive
    if archive is None:
        archive=REPO/'build'/'Lunar_Detail_Regions_03.zip'
        archive.parent.mkdir(parents=True,exist_ok=True)
        part=archive.with_suffix('.zip.part')
        request=urllib.request.Request(URL,headers={'User-Agent':'moon-terrain'})
        with urllib.request.urlopen(request,timeout=120) as response,part.open('wb') as output:
            shutil.copyfileobj(response,output)
        part.replace(archive)
    digest=hashlib.sha256()
    with archive.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
    if digest.hexdigest()!=SHA256:raise SystemExit('SHA-256 mismatch; archive was not extracted.')
    destination=(REPO/'demo').resolve()
    destination.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            parts=PurePosixPath(member.filename).parts
            if not parts or parts[0]!='Lunar_Detail_Regions' or '..' in parts or '\\' in member.filename:
                raise ValueError('Unexpected archive path')
            target=destination.joinpath(*parts[1:]).resolve()
            if not target.is_relative_to(destination):raise ValueError('Unsafe archive path')
            if member.is_dir():target.mkdir(parents=True,exist_ok=True)
            else:
                target.parent.mkdir(parents=True,exist_ok=True)
                with bundle.open(member) as source,target.open('wb') as output:shutil.copyfileobj(source,output)
    print('Demo extracted to',destination)
    print('Run: python tools/serve.py')

if __name__=='__main__':main()
