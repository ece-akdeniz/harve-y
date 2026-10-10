"""Immutable, credential-free source checkpoints using a private temporary Git index."""

import hashlib
import json
import math
import os
import re
import subprocess
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

from .models import SECRET_KEYS, check_json

DEFAULTS = dict(anchor=0.12, rounds=5, close_gap=0.005, final_hold_s=40.0, p_walk=0.25)
FIELDS = {
    'schema_version', 'checkpoint_id', 'commit', 'project_path', 'author', 'description',
    'parent_id', 'created_at', 'agent', 'config', 'runner', 'lock_sha256', 'submodules',
    'data', 'harness_version', 'remote', 'ref', 'published',
}


def _git(repo, *args, env=None, raw=False):
    process_env = os.environ.copy()
    for key in ('GIT_INDEX_FILE', 'GIT_DIR', 'GIT_WORK_TREE', 'GIT_CONFIG_COUNT', 'GIT_CONFIG_PARAMETERS'):
        process_env.pop(key, None)
    process_env.update(env or {})
    result = subprocess.run(
        ['git', '-c', 'core.hooksPath=/dev/null', '-C', str(repo), *args],
        env=process_env, capture_output=True,
    )
    if result.returncode:
        # Git stderr can contain remote credentials: never include it in public exceptions.
        raise ValueError(f'Git operation failed: {args[0]}')
    return result.stdout if raw else result.stdout.decode().strip()


def _id(value):
    return isinstance(value, str) and bool(re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', value))


def _relative(value):
    return isinstance(value, str) and bool(value) and not Path(value).is_absolute() and '..' not in Path(value).parts


def _hash(value, size=64):
    return isinstance(value, str) and bool(re.fullmatch(rf'[0-9a-f]{{{size}}}', value))


def _remote(value):
    if value is None:
        return
    if not isinstance(value, str) or not value or len(value) > 2048 or any(c in value for c in '\n\r\0'):
        raise ValueError('invalid remote')
    if '://' in value:
        parsed = urlsplit(value)
        if (parsed.scheme not in {'https', 'ssh', 'file'} or parsed.password
                or (parsed.username and parsed.scheme != 'ssh')
                or parsed.query or parsed.fragment):
            raise ValueError('remote must be credential-free')
    elif '@' in value and re.fullmatch(r'[A-Za-z0-9_-]+@[A-Za-z0-9.-]+:[A-Za-z0-9_./-]+', value):
        return
    elif '@' in value or '?' in value or '#' in value:
        raise ValueError('remote must be credential-free')


def _secrets(value):
    encoded = json.dumps(value, allow_nan=False)
    if any(v in encoded for k, v in os.environ.items() if SECRET_KEYS.search(k) and len(v) >= 8):
        raise ValueError('secret value in public checkpoint')


def resolve_config(config):
    if not isinstance(config, dict) or set(config) - (set(DEFAULTS) | {'meso', 'claims', 'estimates'}):
        raise ValueError('unknown checkpoint config option')
    out = {**DEFAULTS, 'meso': os.environ.get('NEGOTIATOR_MESO') == '1',
           'claims': os.environ.get('NEGOTIATOR_CLAIMS') == '1',
           'estimates': None if os.environ.get('NEGOTIATOR_ESTIMATES') == '1' else {}, **config}
    for key in DEFAULTS:
        value = out[key]
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError('invalid numerical config')
    if type(out['rounds']) is not int or not 1 <= out['rounds'] <= 100:
        raise ValueError('invalid rounds')
    if any(out[key] > 1 for key in ('anchor', 'close_gap', 'p_walk')):
        raise ValueError('invalid fraction')
    if any(type(out[key]) is not bool for key in ('meso', 'claims')):
        raise ValueError('unresolved feature switch')
    if out['estimates'] is not None and not isinstance(out['estimates'], dict):
        raise ValueError('invalid estimates')
    check_json(out)
    _secrets(out)
    return out


def validate_checkpoint(body):
    """Validate untrusted public metadata without Git, disk access or network calls."""
    if not isinstance(body, dict) or set(body) != FIELDS:
        raise ValueError('invalid checkpoint fields')
    try:
        encoded = json.dumps(body, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError('checkpoint must contain finite JSON') from exc
    if len(encoded.encode()) > 65536:
        raise ValueError('checkpoint too large')
    if type(body['schema_version']) is not int or body['schema_version'] != 1 or not _id(body['checkpoint_id']):
        raise ValueError('invalid checkpoint identity')
    if not _hash(body['commit'], 40) or not _hash(body['lock_sha256']):
        raise ValueError('invalid commit or lock hash')
    if not _relative(body['project_path']) or type(body['published']) is not bool:
        raise ValueError('invalid checkpoint path or publication')
    if body['parent_id'] is not None and not _id(body['parent_id']):
        raise ValueError('invalid parent')
    for key, limit in [('author', 200), ('description', 4000), ('harness_version', 100)]:
        if not isinstance(body[key], str) or not 1 <= len(body[key]) <= limit:
            raise ValueError(f'invalid {key}')
    if not isinstance(body['created_at'], str) or len(body['created_at']) > 50:
        raise ValueError('invalid timestamp')
    try:
        if datetime.fromisoformat(body['created_at']).tzinfo is None:
            raise ValueError('timestamp requires timezone')
    except (ValueError, TypeError) as exc:
        raise ValueError('invalid timestamp') from exc
    if body['agent'] != 'package' or body['runner'] not in {'serial', 'async'}:
        raise ValueError('unsupported agent or runner')
    if not isinstance(body['config'], dict) or set(body['config']) != set(DEFAULTS) | {'meso', 'claims', 'estimates'}:
        raise ValueError('config must be resolved')
    resolve_config(body['config'])
    if not isinstance(body['data'], dict) or len(body['data']) > 100:
        raise ValueError('invalid data manifest')
    if (body['config']['estimates'] is None or body['config']['claims']) and not body['data']:
        raise ValueError('dossier-dependent features require data manifest')
    for name, entry in body['data'].items():
        if not _id(name) or not isinstance(entry, dict) or set(entry) != {'sha256', 'source'}:
            raise ValueError('invalid data manifest')
        if not _hash(entry['sha256']) or not isinstance(entry['source'], str) or not entry['source']:
            raise ValueError('invalid data hash or source')
        _remote(entry['source'])
    if not isinstance(body['submodules'], dict) or len(body['submodules']) > 100:
        raise ValueError('invalid submodules')
    if any(not _relative(k) or not _hash(v, 40) for k, v in body['submodules'].items()):
        raise ValueError('invalid submodule identity')
    _remote(body['remote'])
    if body['ref'] != f"refs/heads/lab/checkpoints/{body['checkpoint_id']}":
        raise ValueError('invalid checkpoint ref')
    if body['published'] and body['remote'] is None:
        raise ValueError('published checkpoint requires remote')
    _secrets(body)
    return json.loads(encoded)


def _root(repo, root=None):
    common = Path(_git(repo, 'rev-parse', '--git-common-dir'))
    return Path(root) if root else (common if common.is_absolute() else repo / common) / 'lab/checkpoints'


def _save(checkpoint, root):
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', dir=root, delete=False) as stream:
        json.dump(checkpoint, stream, indent=2, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
        path = Path(stream.name)
    path.replace(root / f"{checkpoint['checkpoint_id']}.json")


def load_checkpoint(checkpoint_id, root):
    if not _id(checkpoint_id):
        raise ValueError('invalid checkpoint identity')
    body = validate_checkpoint(json.loads((Path(root) / f'{checkpoint_id}.json').read_text()))
    if body['checkpoint_id'] != checkpoint_id:
        raise ValueError('checkpoint identity mismatch')
    return body


def _private(path):
    return any(p.startswith('.env') or p in {'.aws', '.codex', '.agents', '.venv', '.lab-checkpoint.json'}
               or re.search(r'(^|[._-])(api[_-]?key|password|tokens?|secrets?|authorization|credentials?)([._-]|$)',
                            p, re.I) for p in Path(path).parts)


def create_checkpoint(project, *, config, agent='package', runner='serial', author, description,
                      parent_id=None, data=None, root=None):
    project = Path(project).resolve()
    repo = Path(_git(project, 'rev-parse', '--show-toplevel'))
    config = resolve_config(config)
    lock = project / 'uv.lock'
    if not lock.is_file():
        raise ValueError('checkpoint requires project uv.lock')
    remotes = _git(repo, 'remote').splitlines()
    remote = _git(repo, 'remote', 'get-url', 'origin') if 'origin' in remotes else None
    _remote(remote)
    submodules = {}
    for line in _git(repo, 'submodule', 'status', '--recursive', raw=True).decode().splitlines():
        if line[0] != ' ':
            raise ValueError('submodule must be initialized at recorded commit')
        sha, path, *_ = line[1:].split()
        if _git(repo / path, 'status', '--porcelain'):
            raise ValueError('dirty submodule')
        submodules[path] = sha
    names = set(_git(repo, 'ls-files', '-z', raw=True).decode().split('\0'))
    names.update(_git(repo, 'ls-files', '--others', '--exclude-standard', '-z', raw=True).decode().split('\0'))
    names.difference_update(_git(repo, 'ls-files', '-ci', '--exclude-standard', '-z', raw=True).decode().split('\0'))
    names.discard('')
    selected = []
    for name in sorted(names):
        if _private(name) or any(name.startswith(p + '/') for p in submodules):
            continue
        path = repo / name
        if path.is_symlink():
            raise ValueError('checkpoint cannot contain symbolic links')
        if path.is_file():
            content = path.read_bytes()
            if any(v.encode() in content for k, v in os.environ.items() if SECRET_KEYS.search(k) and len(v) >= 8):
                raise ValueError('secret value in source')
            selected.append(name)
    checkpoint_id = uuid.uuid4().hex
    with tempfile.TemporaryDirectory() as temp:
        env = {'GIT_INDEX_FILE': str(Path(temp) / 'index')}
        _git(repo, 'read-tree', '--empty', env=env)
        # hash-object avoids clean filters changing the exact runnable source snapshot.
        for name in selected:
            path = repo / name
            sha = _git(repo, 'hash-object', '-w', '--no-filters', '--', name)
            mode = '100755' if path.stat().st_mode & 0o111 else '100644'
            _git(repo, 'update-index', '--add', '--cacheinfo', mode, sha, name, env=env)
        for path, sha in submodules.items():
            if any(path.startswith(other + '/') for other in submodules if other != path):
                continue
            _git(repo, 'update-index', '--add', '--cacheinfo', '160000', sha, path, env=env)
        tree = _git(repo, 'write-tree', env=env)
        # No parent: excluded secrets must not remain reachable in checkpoint ancestry.
        commit = _git(repo, 'commit-tree', tree, '-m', f'Lab checkpoint {checkpoint_id}', env={
            **env, 'GIT_AUTHOR_NAME': 'Lab', 'GIT_AUTHOR_EMAIL': 'lab@localhost',
            'GIT_COMMITTER_NAME': 'Lab', 'GIT_COMMITTER_EMAIL': 'lab@localhost'})
    body = validate_checkpoint(dict(
        schema_version=1, checkpoint_id=checkpoint_id, commit=commit,
        project_path=project.relative_to(repo).as_posix(), author=author, description=description,
        parent_id=parent_id, created_at=datetime.now(UTC).isoformat(), agent=agent, config=config,
        runner=runner, lock_sha256=hashlib.sha256(lock.read_bytes()).hexdigest(), submodules=submodules,
        data=data or {}, harness_version='lab-v1', remote=remote,
        ref=f'refs/heads/lab/checkpoints/{checkpoint_id}', published=False,
    ))
    _git(repo, 'update-ref', body['ref'], commit, '0' * 40)
    _save(body, _root(repo, root))
    return body


def _verify_tree(project, body):
    tree_submodules = {}
    for record in _git(project, 'ls-tree', '-r', '-z', body['commit'], raw=True).decode().split('\0'):
        if not record:
            continue
        metadata, path = record.split('\t', 1)
        mode, kind, sha = metadata.split()
        if mode == '120000':
            raise ValueError('checkpoint contains a symbolic link')
        if _private(path):
            raise ValueError('checkpoint contains private paths')
        if kind == 'commit':
            tree_submodules[path] = sha
    top_submodules = {p: sha for p, sha in body['submodules'].items()
                      if not any(p.startswith(other + '/') for other in body['submodules'] if other != p)}
    if tree_submodules != top_submodules:
        raise ValueError('submodule manifest mismatch')
    if len(_git(project, 'rev-list', '--parents', '-n', '1', body['commit']).split()) != 1:
        raise ValueError('checkpoint must have no parent history')
    lock_path = str(Path(body['project_path']) / 'uv.lock')
    lock_bytes = _git(project, 'show', f"{body['commit']}:{lock_path}", raw=True)
    if hashlib.sha256(lock_bytes).hexdigest() != body['lock_sha256']:
        raise ValueError('checkpoint lock hash mismatch')


def publish_checkpoint(project, checkpoint, *, remote='origin'):
    body = validate_checkpoint(checkpoint)
    _verify_tree(project, body)
    url = _git(project, 'remote', 'get-url', remote)
    _remote(url)
    if _git(project, 'rev-parse', body['ref']) != body['commit']:
        raise ValueError('immutable local checkpoint ref mismatch')
    existing = _git(project, 'ls-remote', remote, body['ref'])
    if existing and existing.split()[0] != body['commit']:
        raise ValueError('immutable remote checkpoint ref mismatch')
    if not existing:
        # Empty expected ref gives atomic create-only publication, including concurrent writers.
        _git(project, 'push', f"--force-with-lease={body['ref']}:", remote, f"{body['commit']}:{body['ref']}")
    return validate_checkpoint({**body, 'remote': url, 'published': True})


def _data_hash(path):
    if path.is_symlink():
        raise ValueError('data cannot contain links')
    if path.is_file():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    from .runner import fingerprint_data
    return fingerprint_data(path)


def _verify_checkout_bytes(repo, commit):
    for record in _git(repo, 'ls-tree', '-r', '-z', commit, raw=True).decode().split('\0'):
        if not record:
            continue
        metadata, path = record.split('\t', 1)
        mode, kind, sha = metadata.split()
        target = Path(repo) / path
        if kind == 'commit':
            continue
        if mode == '120000' or target.is_symlink():
            raise ValueError('checkpoint source contains symbolic link')
        if not target.is_file() or target.read_bytes() != _git(repo, 'cat-file', 'blob', sha, raw=True):
            raise ValueError('restored source bytes differ from checkpoint')
        if bool(target.stat().st_mode & 0o111) != (mode == '100755'):
            raise ValueError('restored source executable mode differs from checkpoint')


def restore_checkpoint(project, checkpoint, destination, *, branch=None, data_paths=None):
    body = validate_checkpoint(checkpoint)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise ValueError('restore destination already exists')
    if not isinstance(body['data'], dict) or len(body['data']) > 100:
        raise ValueError('invalid data manifest')
    if (body['config']['estimates'] is None or body['config']['claims']) and not body['data']:
        raise ValueError('dossier-dependent features require data manifest')
    for name, entry in body['data'].items():
        if name not in (data_paths or {}) or _data_hash(Path(data_paths[name])) != entry['sha256']:
            raise ValueError('required data missing or hash mismatch')
    try:
        _git(project, 'cat-file', '-e', body['commit'] + '^{commit}')
    except ValueError:
        if not body['published']:
            raise ValueError('checkpoint is not locally available') from None
        _git(project, 'fetch', '--no-tags', body['remote'], body['ref'])
        if _git(project, 'rev-parse', 'FETCH_HEAD') != body['commit']:
            raise ValueError('remote checkpoint SHA mismatch') from None
    _verify_tree(project, body)
    args = ['worktree', 'add']
    args += ['-b', branch] if branch else ['--detach']
    _git(project, *args, str(destination), body['commit'])
    restored = destination / body['project_path']
    try:
        lock = restored / 'uv.lock'
        if not lock.is_file() or hashlib.sha256(lock.read_bytes()).hexdigest() != body['lock_sha256']:
            raise ValueError('checkpoint lock hash mismatch')
        if body['submodules']:
            _git(destination, 'submodule', 'update', '--init', '--recursive')
            for path, sha in body['submodules'].items():
                if _git(destination / path, 'rev-parse', 'HEAD') != sha:
                    raise ValueError('submodule SHA mismatch')
        _verify_checkout_bytes(destination, body['commit'])
        for path, sha in body['submodules'].items():
            _verify_checkout_bytes(destination / path, sha)
        (restored / '.lab-checkpoint.json').write_text(json.dumps(body, indent=2))
    except Exception:
        _git(project, 'worktree', 'remove', '--force', str(destination))
        raise
    return restored
