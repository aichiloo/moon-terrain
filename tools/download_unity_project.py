"""Download, verify and safely unpack the complete Unity v0.3.0 project.

Python 3.9+; standard library only. Existing projects are never overwritten.
"""
from pathlib import Path
import argparse
import hashlib
import http.client
import json
import os
import re
import shutil
import stat
import tempfile
import time
import unicodedata
import urllib.error
import urllib.request
import zipfile

REPO = Path(__file__).resolve().parents[1]
VERSION = "v0.3.0"
ARCHIVE_NAME = "Lunar_Unity_Project_v0.3.0.zip"
ROOT_NAME = "Lunar_Unity_Project"
BASE_URL = "https://github.com/moonspace123/moon-terrain/releases/download/" + VERSION
RECEIPT = ".moon-terrain-release.json"
SCENES = ("plain", "slope", "rim", "depression", "ridge", "ejecta", "rille")
RESERVED = {"CON", "PRN", "AUX", "NUL"} | {
    prefix + str(n) for prefix in ("COM", "LPT") for n in range(1, 10)
}


def sha256_file(file):
    digest = hashlib.sha256()
    with file.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_file(url, destination):
    """Reuse a completed download; retry/resume only our own .part file."""
    if destination.exists():
        if not destination.is_file() or destination.is_symlink():
            raise ValueError("Download path is not a regular file: " + str(destination))
        print("Using cached:", destination)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".part")
    if partial.is_symlink() or (partial.exists() and not partial.is_file()):
        raise ValueError("Partial-download path is not a regular file: " + str(partial))
    for attempt in range(4):
        offset = partial.stat().st_size if partial.exists() else 0
        headers = {"User-Agent": "moon-terrain-unity-project/0.3.0"}
        if offset:
            headers["Range"] = "bytes=" + str(offset) + "-"
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=120) as response:
                resumed = response.status == 206
                if resumed:
                    content_range = response.headers.get("Content-Range", "")
                    match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+|\*)", content_range)
                    if not match or int(match[1]) != offset:
                        raise ValueError("Server returned an unexpected download range.")
                expected = response.headers.get("Content-Length")
                transferred = 0
                with partial.open("ab" if resumed else "wb") as target:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        target.write(chunk)
                        transferred += len(chunk)
                if expected is not None and transferred != int(expected):
                    raise OSError("Download ended before the announced content length.")
            partial.replace(destination)
            print("Downloaded:", destination)
            return
        except urllib.error.HTTPError as error:
            if error.code == 416:
                match = re.fullmatch(r"bytes \*/(\d+)", error.headers.get("Content-Range", ""))
                if match and int(match[1]) == offset and offset:
                    partial.replace(destination)
                    return  # The complete file is checked against SHA-256 below.
            if error.code not in (408, 429, 500, 502, 503, 504) or attempt == 3:
                raise
        except (OSError, urllib.error.URLError, http.client.HTTPException):
            if attempt == 3:
                raise
        print("Connection interrupted; retrying partial download.")
        time.sleep(2 ** attempt)


def read_checksum(file):
    text = file.read_text(encoding="utf-8-sig").strip()
    match = re.fullmatch(r"([0-9a-fA-F]{64})(?:[ \t]+\*?([^\r\n]+))?", text)
    if not match or (match[2] is not None and match[2] != ARCHIVE_NAME):
        raise ValueError("Invalid SHA-256 sidecar; expected one checksum for " + ARCHIVE_NAME)
    return match[1].lower()


def checked_members(bundle):
    """Reject traversal, symlinks, Windows aliases and file/directory collisions."""
    members = []
    seen = {}
    total_bytes = 0
    for member in bundle.infolist():
        # ZipInfo normalizes backslashes on Windows and truncates names at NUL.
        # Validate the original ZIP spelling before that normalization.
        name = member.orig_filename
        parts = name.rstrip("/").split("/")
        mode = member.external_attr >> 16
        if (
            not parts or parts[0] != ROOT_NAME or "\\" in name or ":" in name
            or any(p in ("", ".", "..") for p in parts)
            or any(ord(c) < 32 for c in name)
            or stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR)
        ):
            raise ValueError("Unsafe ZIP entry: " + repr(name))
        relative = parts[1:]
        for part in relative:
            if part.endswith((".", " ")) or part.split(".", 1)[0].upper() in RESERVED:
                raise ValueError("Unsafe Windows ZIP name: " + repr(name))
        if not relative:
            if not member.is_dir():
                raise ValueError("ZIP root is not a directory.")
            continue
        key = "/".join(unicodedata.normalize("NFC", p).casefold() for p in relative)
        if key in seen:
            raise ValueError("Duplicate or aliased ZIP entry: " + repr(name))
        seen[key] = member.is_dir()
        total_bytes += member.file_size
        members.append((member, relative))
    for key in seen:
        parts = key.split("/")
        for length in range(1, len(parts)):
            parent = "/".join(parts[:length])
            if parent in seen and not seen[parent]:
                raise ValueError("ZIP entry uses a file as its parent: " + key)
    required = {
        "UnityProject/ProjectSettings/ProjectVersion.txt",
        "UnityProject/Packages/manifest.json",
        *("UnityProject/Assets/Scenes/" + scene + ".unity" for scene in SCENES),
    }
    available = {"/".join(relative) for member, relative in members if not member.is_dir()}
    if not required.issubset(available):
        raise ValueError("ZIP is missing required Unity project files: " + ", ".join(sorted(required - available)))
    return members, total_bytes


def existing_project(destination, digest):
    if destination.is_symlink():
        raise ValueError("Refusing to replace a linked destination: " + str(destination))
    if not destination.exists():
        return False
    if not destination.is_dir():
        raise ValueError("Destination is not a directory: " + str(destination))
    if not any(destination.iterdir()):
        return False
    receipt = destination / RECEIPT
    try:
        data = json.loads(receipt.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    if data.get("archive_sha256") == digest and data.get("release") == VERSION:
        print("Existing downloaded project kept; no local files were replaced:", destination)
        return True
    raise ValueError("Destination is not empty; your existing files were kept. Choose a new --destination folder: " + str(destination))


def extract_project(bundle, members, total_bytes, destination, digest):
    if existing_project(destination, digest):
        return
    parent = destination.parent.resolve()
    parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(parent).free < total_bytes + 64 * 1024 * 1024:
        raise OSError("Not enough free space to extract the complete project.")
    prefix = "." + destination.name + "-extract-"
    staging = Path(tempfile.mkdtemp(prefix=prefix, dir=parent)).resolve()
    try:
        for member, relative in members:
            target = staging.joinpath(*relative)
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(member) as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output, length=1024 * 1024)
        (staging / RECEIPT).write_text(json.dumps({
            "release": VERSION, "archive": ARCHIVE_NAME, "archive_sha256": digest,
        }, indent=2) + "\n", encoding="utf-8")
        # Never merge into an existing project, even if it appeared during extraction.
        if destination.exists():
            if destination.is_symlink() or not destination.is_dir() or any(destination.iterdir()):
                raise ValueError("Destination changed while extracting; existing files were kept.")
            destination.rmdir()  # Only an empty directory is removed.
        staging.rename(destination)
    finally:
        # Cleanup is limited to the unique staging directory created above.
        if staging.exists():
            if staging.parent.resolve() != parent or not staging.name.startswith(prefix) or staging.is_symlink():
                raise ValueError("Unexpected staging path; automatic cleanup was skipped.")
            shutil.rmtree(staging)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, help="Use an existing ZIP instead of downloading it")
    parser.add_argument("--sha256-file", type=Path, help="Use an existing release .zip.sha256 sidecar")
    parser.add_argument("--destination", type=Path, default=REPO / "projects" / ROOT_NAME)
    parser.add_argument("--verify-only", action="store_true", help="Verify SHA-256, ZIP paths and CRCs without extracting")
    args = parser.parse_args()
    archive = args.archive or REPO / "build" / ARCHIVE_NAME
    checksum = args.sha256_file or archive.with_name(archive.name + ".sha256")
    if not checksum.exists():
        if args.sha256_file:
            raise FileNotFoundError("Checksum file does not exist: " + str(checksum))
        download_file(BASE_URL + "/" + ARCHIVE_NAME + ".sha256", checksum)
    expected = read_checksum(checksum)
    if args.archive:
        if not archive.is_file():
            raise FileNotFoundError("Archive does not exist: " + str(archive))
    else:
        download_file(BASE_URL + "/" + ARCHIVE_NAME, archive)
    digest = sha256_file(archive)
    if digest != expected:
        raise ValueError("SHA-256 mismatch; no extraction performed. The downloaded file was kept: " + str(archive))
    print("SHA-256 verified:", digest)
    destination = Path(os.path.abspath(os.path.expanduser(str(args.destination))))
    with zipfile.ZipFile(archive) as bundle:
        members, total_bytes = checked_members(bundle)
        bad = bundle.testzip()
        if bad:
            raise ValueError("ZIP CRC check failed: " + bad)
        print("ZIP paths and CRCs verified:", len(members), "entries")
        if args.verify_only:
            return
        extract_project(bundle, members, total_bytes, destination, digest)
    print("Unity Hub: add/open", destination / "UnityProject")
    print("Required Editor: Unity 2022.3.62f3c1; first import rebuilds the local cache.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError) as error:
        raise SystemExit("Unity project download failed: " + str(error))
