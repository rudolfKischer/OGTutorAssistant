import argparse
import glob
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tarfile
import urllib.error
import urllib.request
import zipfile
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data" / "manifest.json"
CACHE = ROOT / "data" / ".bucket"
CHUNK = 1 << 20


def load():
    return json.loads(MANIFEST.read_text())


def save(manifest):
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")


def digest(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(CHUNK), b""):
            hasher.update(block)
    return hasher.hexdigest()


def tag(name, bundle):
    return f"{name}-v{bundle['version']}"


def asset(name, bundle):
    return bundle.get("asset") or f"{tag(name, bundle)}.tar.gz"


def source_url(manifest, name, bundle):
    if bundle.get("url"):
        return bundle["url"]
    return f"https://github.com/{manifest['repo']}/releases/download/{tag(name, bundle)}/{asset(name, bundle)}"


def download(manifest, name, bundle, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        urllib.request.urlretrieve(source_url(manifest, name, bundle), target)
    except urllib.error.HTTPError:
        subprocess.run(["gh", "release", "download", tag(name, bundle), "-R", manifest["repo"], "-p", asset(name, bundle), "-D", str(target.parent), "--clobber"], check=True)


def stamp(name):
    return CACHE / f"{name}.stamp"


def current(name, bundle):
    present = all((ROOT / path).exists() for path in bundle["files"])
    return present and stamp(name).exists() and stamp(name).read_text() == f"{bundle['version']}:{bundle['sha256']}"


def extract(bundle, archive):
    dest = ROOT / bundle.get("dest", ".")
    if bundle.get("archive") == "raw":
        (ROOT / bundle["files"][0]).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(archive, ROOT / bundle["files"][0])
        return
    if bundle.get("archive") == "zip":
        zipfile.ZipFile(archive).extractall(dest)
        return
    wanted = set(bundle["files"])
    with tarfile.open(archive) as tar:
        members = [member for member in tar.getmembers() if member.name in wanted]
        tar.extractall(dest, members=members, filter="data")


def fetch_bundle(manifest, name, force=False):
    bundle = manifest["bundles"][name]
    if current(name, bundle) and not force:
        return False
    archive = CACHE / asset(name, bundle)
    if not archive.exists() or digest(archive) != bundle["sha256"]:
        download(manifest, name, bundle, archive)
    if digest(archive) != bundle["sha256"]:
        raise SystemExit(f"{name}: checksum mismatch for {archive.name}")
    extract(bundle, archive)
    stamp(name).write_text(f"{bundle['version']}:{bundle['sha256']}")
    return True


def ensure(names=None, force=False):
    manifest = load()
    chosen = names or [name for name, bundle in manifest["bundles"].items() if bundle.get("required", True)]
    return {name: fetch_bundle(manifest, name, force) for name in chosen}


def packed(bundle, path):
    data = (ROOT / path).read_bytes()
    if not bundle.get("filter"):
        return data
    sys.path.insert(0, str(ROOT))
    module, function = bundle["filter"].split(":")
    return getattr(import_module(module), function)(path, data)


def pack(name, bundle, archive):
    archive.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "w:gz", format=tarfile.PAX_FORMAT) as tar:
        for path in sorted(bundle["files"]):
            data = packed(bundle, path)
            info = tarfile.TarInfo(path)
            info.size, info.mtime, info.mode = len(data), 0, 0o644
            tar.addfile(info, io.BytesIO(data))


def release(manifest, name, bundle, archive):
    repo, label = manifest["repo"], tag(name, bundle)
    exists = subprocess.run(["gh", "release", "view", label, "-R", repo], capture_output=True).returncode == 0
    if not exists:
        subprocess.run(["gh", "release", "create", label, "-R", repo, "--title", label, "--notes", f"Data bundle {name}, version {bundle['version']}."], check=True)
    subprocess.run(["gh", "release", "upload", label, str(archive), "-R", repo, "--clobber"], check=True)


def expand(bundle):
    if bundle.get("globs"):
        bundle["files"] = sorted({Path(path).relative_to(ROOT).as_posix() for pattern in bundle["globs"] for path in glob.glob(str(ROOT / pattern))})


def publish(name, bump=False):
    manifest = load()
    bundle = manifest["bundles"][name]
    expand(bundle)
    bundle["version"] = bundle["version"] + 1 if bump else bundle["version"]
    bundle["asset"] = asset(name, {**bundle, "asset": None})
    archive = CACHE / bundle["asset"]
    pack(name, bundle, archive)
    bundle["sha256"], bundle["size"] = digest(archive), archive.stat().st_size
    release(manifest, name, bundle, archive)
    save(manifest)
    stamp(name).write_text(f"{bundle['version']}:{bundle['sha256']}")
    return bundle


def status():
    manifest = load()
    for name, bundle in manifest["bundles"].items():
        state = "current" if current(name, bundle) else "missing"
        print(f"{name:12} v{bundle['version']:<3} {bundle.get('size', 0) / 1e6:7.2f} MB  {state}  {len(bundle['files'])} files")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["fetch", "publish", "status", "clean"])
    parser.add_argument("names", nargs="*")
    parser.add_argument("--bump", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.command == "status":
        status()
    elif args.command == "clean":
        shutil.rmtree(CACHE, ignore_errors=True)
    elif args.command == "publish":
        for name in args.names:
            print(name, publish(name, args.bump)["sha256"])
    else:
        report(args)


def report(args):
    done = ensure(args.names or None, args.force)
    print(", ".join(f"{name}: {'downloaded' if fetched else 'up to date'}" for name, fetched in done.items()))


if __name__ == "__main__":
    main()
