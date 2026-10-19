import argparse
import gzip
import hashlib
import io
import json
import shutil
import subprocess
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data" / "manifest.json"
CACHE = ROOT / "data" / ".bucket"
HOOKS = ".githooks"
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
    return f"{tag(name, bundle)}.tar.gz"


def download(manifest, name, bundle, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(f"https://github.com/{manifest['repo']}/releases/download/{tag(name, bundle)}/{asset(name, bundle)}", target)


def stamp(name):
    return CACHE / f"{name}.json"


def recorded(name):
    return json.loads(stamp(name).read_text()) if stamp(name).exists() else None


def record(name, bundle):
    files = {path: digest(ROOT / path) for path in bundle["files"] if (ROOT / path).exists()}
    stamp(name).write_text(json.dumps({"version": bundle["version"], "sha256": bundle["sha256"], "files": files}))


def current(name, bundle):
    state = recorded(name)
    present = all((ROOT / path).exists() for path in bundle["files"])
    return present and state is not None and (state["version"], state["sha256"]) == (bundle["version"], bundle["sha256"])


def modified(name):
    state = recorded(name)
    return state is not None and any((ROOT / path).exists() and digest(ROOT / path) != sha for path, sha in state["files"].items())


def extract(bundle, archive):
    wanted = set(bundle["files"])
    with tarfile.open(archive) as tar:
        members = [member for member in tar.getmembers() if member.name in wanted]
        options = {"filter": "data"} if hasattr(tarfile, "data_filter") else {}
        tar.extractall(ROOT, members=members, **options)


def fetch_bundle(manifest, name, force=False):
    bundle = manifest["bundles"][name]
    if current(name, bundle) and not force:
        return "up to date"
    if modified(name) and not force:
        return "kept local edits (run sync, or fetch --force)"
    archive = CACHE / asset(name, bundle)
    if not archive.exists() or digest(archive) != bundle["sha256"]:
        download(manifest, name, bundle, archive)
    if digest(archive) != bundle["sha256"]:
        raise SystemExit(f"{name}: checksum mismatch for {archive.name}")
    extract(bundle, archive)
    record(name, bundle)
    return "downloaded"


def ensure(names=None, force=False):
    manifest = load()
    chosen = names or [name for name, bundle in manifest["bundles"].items() if bundle.get("required", True)]
    return {name: fetch_bundle(manifest, name, force) for name in chosen}


def pack(bundle, archive):
    archive.parent.mkdir(parents=True, exist_ok=True)
    with open(archive, "wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as zipped, tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for path in sorted(bundle["files"]):
            data = (ROOT / path).read_bytes()
            info = tarfile.TarInfo(path)
            info.size, info.mtime, info.mode = len(data), 0, 0o644
            tar.addfile(info, io.BytesIO(data))


def release(manifest, name, bundle, archive):
    repo, label = manifest["repo"], tag(name, bundle)
    exists = subprocess.run(["gh", "release", "view", label, "-R", repo], capture_output=True).returncode == 0
    if not exists:
        subprocess.run(["gh", "release", "create", label, "-R", repo, "--title", label, "--notes", f"Data bundle {name}, version {bundle['version']}."], check=True)
    subprocess.run(["gh", "release", "upload", label, str(archive), "-R", repo, "--clobber"], check=True)


def publish(name, bump=False):
    manifest = load()
    bundle = manifest["bundles"][name]
    bundle["version"] += 1 if bump else 0
    bundle["asset"] = asset(name, bundle)
    archive = CACHE / bundle["asset"]
    pack(bundle, archive)
    bundle["sha256"], bundle["size"] = digest(archive), archive.stat().st_size
    release(manifest, name, bundle, archive)
    save(manifest)
    record(name, bundle)
    return bundle


def sync():
    changed = [name for name in load()["bundles"] if modified(name)]
    for name in changed:
        print(f"{name}: local edits, uploading v{load()['bundles'][name]['version'] + 1}")
        publish(name, bump=True)
    return changed


def install():
    if (ROOT / ".git").exists() and (ROOT / HOOKS).is_dir():
        subprocess.run(["git", "config", "core.hooksPath", HOOKS], cwd=ROOT, check=True)


def status():
    for name, bundle in load()["bundles"].items():
        state = "modified" if modified(name) else "current" if current(name, bundle) else "missing"
        print(f"{name:12} v{bundle['version']:<3} {bundle.get('size', 0) / 1e6:7.2f} MB  {state}  {len(bundle['files'])} files")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["fetch", "publish", "sync", "status", "install", "clean"])
    parser.add_argument("names", nargs="*")
    parser.add_argument("--bump", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.command == "publish":
        for name in args.names:
            print(name, publish(name, args.bump)["sha256"])
    elif args.command == "clean":
        shutil.rmtree(CACHE, ignore_errors=True)
    elif args.command == "fetch":
        install()
        print(", ".join(f"{name}: {state}" for name, state in ensure(args.names or None, args.force).items()))
    else:
        {"sync": sync, "status": status, "install": install}[args.command]()


if __name__ == "__main__":
    main()
