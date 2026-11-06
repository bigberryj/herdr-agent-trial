#!/usr/bin/env python3
"""Install the reviewed publisher release without executing install scripts."""
import hashlib
from pathlib import Path
import urllib.request

VERSION = 'v0.9.5'
DIGEST = '14d9e8bc8b4a9e0118d77c32266f76d461f09b40342eb23752960bd89f59929d'
URL = f'https://github.com/herdrdev/herdr/releases/download/{VERSION}/herdr-linux-x86_64'


def main():
    import platform
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise SystemExit('This trial installer is pinned to Linux x86_64.')
    root = Path(__file__).resolve().parent
    binary = Path.home()/'.local/lib/herdr'/VERSION/'herdr'
    if binary.exists():
        if hashlib.sha256(binary.read_bytes()).hexdigest() != DIGEST:
            raise SystemExit('Existing binary differs: refusing replacement.')
    else:
        data = urllib.request.urlopen(URL, timeout=60).read()
        if hashlib.sha256(data).hexdigest() != DIGEST:
            raise SystemExit('Publisher asset digest mismatch: not installed.')
        binary.parent.mkdir(parents=True, exist_ok=True)
        with binary.open('xb') as f:
            f.write(data)
    binary.chmod(0o755)
    (root/'workspace').mkdir(exist_ok=True)
    wrapper = root/'herdr-trial'
    wrapper.chmod(0o755)
    bindir = Path.home()/'.local/bin'
    bindir.mkdir(parents=True, exist_ok=True)
    for name,target in [('herdr',binary),('herdr-trial',wrapper),('herdr-workers',root/'herdr-workers')]:
        target.chmod(0o755)
        link=bindir/name
        if link.exists() or link.is_symlink():
            if not link.is_symlink() or link.resolve() != target.resolve():
                raise SystemExit(f'Refusing to replace existing {link}')
        else:
            link.symlink_to(target)
    print(f'Verified {VERSION} {DIGEST}; installed user-local command links.')


if __name__ == '__main__':
    main()
