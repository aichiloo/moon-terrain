"""Download and verify the complete v0.2.0 Unity-image + Three.js offline demo."""
from pathlib import Path, PurePosixPath
import argparse, hashlib, os, shutil, stat, urllib.request, zipfile

REPO = Path(__file__).resolve().parents[1]
URL = 'https://github.com/moonspace123/moon-terrain/releases/download/v0.2.0/Lunar_Unity_Demo.zip'
SHA256 = 'd9eec289ecfab631705d7aa97bb3e71b922658055631cd2bf2cd1eef998fa107'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, help='Verify/use an existing ZIP')
    parser.add_argument('--destination', type=Path, default=REPO/'demo'/'Lunar_Unity_Demo')
    parser.add_argument('--verify-only', action='store_true', help='Check SHA-256 and all ZIP CRCs without extraction')
    args = parser.parse_args()
    archive = args.archive
    if archive is None:
        archive = REPO/'build'/'Lunar_Unity_Demo.zip'
        archive.parent.mkdir(parents=True, exist_ok=True)
        part = archive.with_suffix('.zip.part')
        request = urllib.request.Request(URL, headers={'User-Agent':'moon-terrain'})
        with urllib.request.urlopen(request, timeout=120) as response, part.open('wb') as output:
            shutil.copyfileobj(response, output, length=1024*1024)
        part.replace(archive)
    digest = hashlib.sha256()
    with archive.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024), b''): digest.update(chunk)
    if digest.hexdigest() != SHA256: raise SystemExit('SHA-256 mismatch; no extraction performed.')
    destination = args.destination.resolve()
    with zipfile.ZipFile(archive) as bundle:
        members = []
        for member in bundle.infolist():
            parts = PurePosixPath(member.filename).parts
            mode = member.external_attr >> 16
            if not parts or parts[0] != 'Lunar_Unity_Demo' or '..' in parts or '\\' in member.filename or ':' in member.filename or stat.S_ISLNK(mode):
                raise ValueError('Unsafe archive path')
            target = destination.joinpath(*parts[1:]).resolve()
            if os.path.commonpath([str(target), str(destination)]) != str(destination): raise ValueError('Unsafe archive destination')
            members.append((member,target))
        bad = bundle.testzip()
        if bad: raise ValueError('ZIP CRC failed: '+bad)
        if args.verify_only:
            print('PASS: SHA-256, safe paths and all ZIP CRCs;',len(members),'entries')
            return
        if destination.exists() and any(destination.iterdir()):
            raise SystemExit('Destination is not empty; choose a new --destination folder.')
        destination.mkdir(parents=True,exist_ok=True)
        for member,target in members:
            if member.is_dir(): target.mkdir(parents=True,exist_ok=True)
            else:
                target.parent.mkdir(parents=True,exist_ok=True)
                with bundle.open(member) as src,target.open('wb') as dst: shutil.copyfileobj(src,dst)
    print('Verified demo extracted to:',destination)
    print('Open:',destination/'index.html')

if __name__ == '__main__': main()
