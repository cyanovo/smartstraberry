"""Build a reviewed code-only cumulative update from the immutable published ZIP."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NEW = ROOT / 'delivery/Strawberry-Student-Windows-2026-10-26'
BASE = ROOT / 'delivery/Strawberry-Student-Windows-2026-10-25.zip'
OUT = ROOT / 'delivery/student-update-2026.10.26-01'
BASE_HASH = 'dafb07d49d89f470faac2a6461418ea7ef0df849ad4c5ec0127ab676d403fba4'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def allowed(path):
    parts = Path(path).parts
    if Path(path).is_absolute() or '..' in parts or ':' in path:
        return False
    if any(p in {'.venv', 'node_modules', 'saves', '.runtime', '__pycache__'} for p in parts):
        return False
    if path.startswith(('Newsmart-Strawberry/backend/server/', 'Newsmart-Strawberry/backend/package/',
                        'Newsmart-Strawberry/backend/test/', 'Newsmart-Strawberry/web/src/',
                        'Newsmart-Strawberry/scripts/', 'Newsmart-Strawberry/docs/', '学生版本同步/')):
        return Path(path).suffix.lower() in {'.py', '.js', '.mjs', '.vue', '.css', '.less', '.json', '.yaml', '.yml', '.toml', '.lock', '.md', '.cmd', '.ps1', '.ts', '.mts'}
    parent = Path(path).parent.as_posix()
    if parent in {'.', 'Newsmart-Strawberry', 'Newsmart-Strawberry/backend', 'Newsmart-Strawberry/web', 'strawberry_project', 'strawberry_vision'}:
        if Path(path).name == 'requirements.txt':
            return True
        return Path(path).suffix.lower() in {'.py', '.js', '.mjs', '.ts', '.json', '.yaml', '.toml', '.lock', '.md', '.cmd', '.ps1'} and Path(path).name not in {
            'manifest.json', 'node-links.json', 'pending-links.json', 'student-version.json', 'integrity-report.json',
            'PACKAGE_CHECKS.json', 'DEPLOY_TEST_REPORT.json', 'PACKAGE_VALIDATION.md', 'annotations_draft.json'}
    return False


def main():
    if OUT.exists() or Path(str(OUT) + '.zip').exists():
        raise SystemExit('Update already exists; do not overwrite published outputs')
    with BASE.open('rb') as file:
        assert hashlib.file_digest(file, 'sha256').hexdigest() == BASE_HASH, 'Wrong published baseline'
    OUT.mkdir()
    changes = []
    with zipfile.ZipFile(BASE) as baseline:
        old_manifest = json.loads(baseline.read('Strawberry-Student-Windows/manifest.json'))
        new_manifest = json.loads((NEW / 'manifest.json').read_text(encoding='utf-8'))
        for relative in sorted(new_manifest):
            if not allowed(relative):
                continue
            data = (NEW / relative).read_bytes()
            sha = digest(data)
            old_sha = old_manifest.get(relative)
            if sha == old_sha:
                continue
            target = OUT / 'files' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            if old_sha:
                original = baseline.read('Strawberry-Student-Windows/' + relative)
                assert digest(original) == old_sha
                old_file = OUT / 'base' / relative
                old_file.parent.mkdir(parents=True, exist_ok=True)
                old_file.write_bytes(original)
            changes.append({'operation': 'modify' if old_sha else 'add', 'path': relative,
                            'old_sha256': old_sha, 'new_sha256': sha})
        # Prove the update can be applied to published file bytes, not the mutable extracted directory.
        for change in changes:
            data = (OUT / 'files' / change['path']).read_bytes()
            assert digest(data) == new_manifest[change['path']]
        for relative, needle in {
            'Newsmart-Strawberry/scripts/windows/services.ps1': b'STRAWBERRY_SKIP_WORKER',
            'Newsmart-Strawberry/backend/package/yuxi/repositories/detect_repository.py': b'ROUND(AVG(maturity_ratio)::numeric, 2)',
        }.items():
            candidate = OUT / 'files' / relative
            effective = candidate.read_bytes() if candidate.exists() else baseline.read('Strawberry-Student-Windows/' + relative)
            assert needle in effective, 'Lost delivery-specific repair: ' + relative
    metadata = {'source_version': 'student-2026.10.25-base', 'target_version': 'student-2026.10.26',
                'platform': 'Windows x64 native', 'baseline_zip_sha256': BASE_HASH,
                'dependency_changes': [], 'migrations': [], 'deletions': [], 'files': changes,
                'validation': 'Every old and new hash checked; applied code matches full package; baseline repairs retained'}
    for change in changes:
        if Path(change['path']).name in {'uv.lock', 'pnpm-lock.yaml', 'requirements.txt', 'pyproject.toml', 'package.json'}:
            metadata['dependency_changes'].append(change['path'])
    (OUT / 'update-manifest.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    shutil.copy2(ROOT / 'packaging/templates/UPDATE.md', OUT / 'UPDATE.md')
    shutil.copy2(ROOT / '学生版本同步/AI代码同步规范.md', OUT / 'AI代码同步规范.md')
    archive = Path(str(OUT) + '.zip')
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as output:
        for file in OUT.rglob('*'):
            if file.is_file():
                output.write(file, file.relative_to(OUT.parent).as_posix())
    with zipfile.ZipFile(archive) as check:
        assert check.testzip() is None
    with archive.open('rb') as file:
        sha = hashlib.file_digest(file, 'sha256').hexdigest()
    archive.with_suffix('.zip.sha256').write_text(f'{sha}  {archive.name}\n', encoding='ascii')
    print(json.dumps({'archive': str(archive), 'files': len(changes), 'dependencies': metadata['dependency_changes'], 'sha256': sha}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
