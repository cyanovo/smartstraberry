"""Build a cumulative, code-only update from two immutable student releases."""
import hashlib
import json
from pathlib import Path
import zipfile

from build_update import allowed, digest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'delivery/student-update-2026.10.27-01'
BASES = {
    'student-2026.10.25-base': ('Strawberry-Student-Windows-2026-10-25.zip', 'dafb07d49d89f470faac2a6461418ea7ef0df849ad4c5ec0127ab676d403fba4'),
    'student-2026.10.26': ('Strawberry-Student-Windows-2026-10-26.zip', '49540ab94722b08e103bc6d4fa8674d2acf75307997868cd2800058d46688153'),
}
SKIP = {'.venv', '.venv_new', 'node_modules', '__pycache__', '.runtime', 'saves', '.git', 'dist', 'output', 'images', 'dataset', 'datasets', 'weights', 'runs', '.pytest_cache', '.ruff_cache', '.idea', '.vscode'}


def walk(folder):
    for p in folder.iterdir():
        if p.name in SKIP or p.is_symlink() or p.is_junction():
            continue
        if p.is_dir():
            yield from walk(p)
        elif p.is_file():
            yield p


def main():
    import sys
    publish = '--publish' in sys.argv
    snapshots = {}
    for version, (name, expected) in BASES.items():
        path = ROOT / 'delivery' / name
        with path.open('rb') as f:
            assert hashlib.file_digest(f, 'sha256').hexdigest() == expected
        with zipfile.ZipFile(path) as z:
            manifest_name = next(n for n in z.namelist() if n.count('/') == 1 and n.endswith('/manifest.json'))
            prefix = manifest_name.rsplit('/', 1)[0] + '/'
            manifest = json.loads(z.read(manifest_name))
            snapshots[version] = {p: z.read(prefix + p) for p in manifest if allowed(p) or p.startswith('strawberry_vision/tests/') and p.endswith('.py')}
            for p, data in snapshots[version].items():
                assert digest(data) == manifest[p], p
    target = dict(snapshots['student-2026.10.26'])
    # Only application source is overlaid. Delivery root launchers keep their published relocation logic.
    for directory in ('Newsmart-Strawberry/backend', 'Newsmart-Strawberry/web', 'Newsmart-Strawberry/scripts', 'Newsmart-Strawberry/docs', 'strawberry_project', 'strawberry_vision'):
        for path in walk(ROOT / directory):
            relative = path.relative_to(ROOT).as_posix()
            if relative in {'Newsmart-Strawberry/backend/package/yuxi/services/iot_service.py', 'Newsmart-Strawberry/backend/package/yuxi/services/field_analysis_service.py', 'strawberry_project/strawberry_classifier.py', 'strawberry_vision/train.py'}:
                continue
            if not (allowed(relative) or relative.startswith('strawberry_vision/tests/') and path.suffix == '.py'):
                continue
            if directory in ('strawberry_project', 'strawberry_vision') and path.suffix in {'.yaml', '.yml', '.json'}:
                continue
            if path.name.startswith('.env') or path.name in {'test_student_packaging.py'}:
                continue
            data = path.read_bytes()
            # Keep published formatting/line endings when source has no semantic text change.
            prior = target.get(relative)
            if prior is not None and prior.decode('utf-8-sig').replace('\r\n', '\n') == data.decode('utf-8-sig').replace('\r\n', '\n'):
                continue
            target[relative] = data
    service = 'Newsmart-Strawberry/scripts/windows/services.ps1'
    text = target[service].decode('utf-8-sig')
    if 'STRAWBERRY_SKIP_WORKER' not in text:
        old = "    Start-Owned 'worker' $python @((Join-Path $root 'backend/run_local.py'), '--worker') (Join-Path $root 'backend')"
        assert old in text, 'Review changed worker startup before packaging'
        text = text.replace(old, "    if ($env:STRAWBERRY_SKIP_WORKER -ne '1') { " + old.strip() + ' }')
    target[service] = text.encode('utf-8-sig')
    repo = 'Newsmart-Strawberry/backend/package/yuxi/repositories/detect_repository.py'
    target[repo] = target[repo].replace(b'ROUND(AVG(maturity_ratio), 2)', b'ROUND(AVG(maturity_ratio)::numeric, 2)')
    assert b'STRAWBERRY_SKIP_WORKER' in target[service]
    assert b'ROUND(AVG(maturity_ratio)::numeric, 2)' in target[repo]
    # Restore published bytes after applying delivery-only patches if content is unchanged.
    for p in (service, repo):
        prior = snapshots['student-2026.10.26'][p]
        if prior.decode('utf-8-sig').splitlines() == target[p].decode('utf-8-sig').splitlines():
            target[p] = prior
    if '--stage' in sys.argv:
        stage = ROOT / 'packaging/.qa-20261027'
        for p, data in target.items():
            if p.endswith('.py'):
                compile(data, p, 'exec')
            dest = stage / p
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        print('STAGED', stage)
    changes = []
    for p, data in sorted(target.items()):
        assert not Path(p).is_absolute() and '..' not in Path(p).parts and ':' not in p
        assert not any(part in SKIP for part in Path(p).parts)
        previous = {v: digest(s[p]) if p in s else None for v, s in snapshots.items()}
        if all(sha == digest(data) for sha in previous.values()):
            continue
        changes.append({'path': p, 'operation_by_source': {v: 'modify' if h else 'add' for v, h in previous.items()}, 'old_sha256': previous, 'new_sha256': digest(data)})
    metadata = {'target_version': 'student-2026.10.27-01', 'sources': {v: {'zip': n, 'sha256': h} for v, (n, h) in BASES.items()}, 'platform': 'Windows x64 native', 'deletions': [], 'migrations': [], 'dependency_changes': [c['path'] for c in changes if Path(c['path']).name in {'requirements.txt', 'pyproject.toml', 'uv.lock', 'package.json', 'pnpm-lock.yaml'}], 'files': changes}
    print('CHANGES', len(changes), 'DEPENDENCIES', metadata['dependency_changes'])
    for change in changes:
        print('LATEST' if change['old_sha256']['student-2026.10.26'] != change['new_sha256'] else 'CUMULATIVE', change['path'])
    if not publish:
        return
    assert not OUT.exists() and not Path(str(OUT) + '.zip').exists()
    OUT.mkdir()
    for c in changes:
        p = c['path']
        for location, data in [('files', target[p])] + [('base/' + v, s[p]) for v, s in snapshots.items() if p in s]:
            dest = OUT / location / p
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        if p.endswith('.py'):
            compile(target[p], p, 'exec')
    for version, snapshot in snapshots.items():
        applied = dict(snapshot)
        applied.update({c['path']: (OUT / 'files' / c['path']).read_bytes() for c in changes})
        assert all(applied[p] == data for p, data in target.items()), version
    (OUT / 'update-manifest.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    for src, name in [('packaging/UPDATE-20261027.md', 'UPDATE.md'), ('学生版本同步/AI代码同步规范.md', 'AI代码同步规范.md'), ('packaging/VALIDATION-20261027.md', 'VALIDATION.md')]:
        (OUT / name).write_bytes((ROOT / src).read_bytes())
    (OUT / '版本更新记录-截至本次制包.md').write_bytes((ROOT / '学生版本同步/版本更新记录.md').read_bytes())
    inventory = {p.relative_to(OUT).as_posix(): digest(p.read_bytes()) for p in OUT.rglob('*') if p.is_file()}
    (OUT / 'package-files.sha256.json').write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding='utf-8')
    archive = Path(str(OUT) + '.zip')
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for p in OUT.rglob('*'):
            if p.is_file():
                z.write(p, p.relative_to(OUT.parent).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name, sha in inventory.items():
            assert digest(z.read(OUT.name + '/' + name)) == sha
    sha = digest(archive.read_bytes())
    archive.with_suffix('.zip.sha256').write_text(f'{sha}  {archive.name}\n', encoding='ascii')
    print('READY', archive, archive.stat().st_size, len(changes), sha)


if __name__ == '__main__':
    main()
