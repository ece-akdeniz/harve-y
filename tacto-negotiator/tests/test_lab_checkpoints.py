import hashlib
import subprocess

import pytest

from negotiator.lab.checkpoints import (
    create_checkpoint,
    load_checkpoint,
    publish_checkpoint,
    restore_checkpoint,
    validate_checkpoint,
)


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True).stdout.decode().strip()


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / 'repo'
    path.mkdir()
    git(path, 'init')
    git(path, 'config', 'user.email', 'test@example.com')
    git(path, 'config', 'user.name', 'Test')
    (path / 'uv.lock').write_text('lock')
    (path / 'a.py').write_text('base')
    (path / 'deleted.py').write_text('delete')
    (path / '.env').write_text('PRIVATE=hidden')
    git(path, 'add', '.')
    git(path, 'commit', '-m', 'base')
    return path


def make(repo, **kwargs):
    return create_checkpoint(repo, config={}, author='Test', description='candidate', **kwargs)


def test_roundtrip_preserves_checkout_and_excludes_tracked_secret(repo, tmp_path):
    (repo / 'a.py').write_text('staged')
    git(repo, 'add', 'a.py')
    (repo / 'a.py').write_text('working')
    (repo / 'binary.bin').write_bytes(b'\x00\xff')
    (repo / 'deleted.py').unlink()
    before = git(repo, 'status', '--porcelain=v1')
    branch = git(repo, 'symbolic-ref', 'HEAD')
    index = git(repo, 'diff', '--cached')
    cp = make(repo)
    manifest_root = (repo / git(repo, 'rev-parse', '--git-common-dir')).resolve() / 'lab/checkpoints'
    assert load_checkpoint(cp['checkpoint_id'], manifest_root) == cp
    restored = restore_checkpoint(repo, cp, tmp_path / 'restored')
    assert (restored / 'binary.bin').read_bytes() == b'\x00\xff'
    assert (restored / 'a.py').read_text() == 'working'
    assert not (restored / 'deleted.py').exists()
    assert not (restored / '.env').exists()
    assert git(repo, 'status', '--porcelain=v1') == before
    assert git(repo, 'symbolic-ref', 'HEAD') == branch
    assert git(repo, 'diff', '--cached') == index


def test_publish_second_clone_duplicate_and_immutable(repo, tmp_path):
    remote = tmp_path / 'remote.git'
    subprocess.run(['git', 'init', '--bare', str(remote)], check=True, capture_output=True)
    git(repo, 'remote', 'add', 'origin', str(remote))
    git(repo, 'push', 'origin', 'HEAD:refs/heads/main')
    second = tmp_path / 'second'
    subprocess.run(['git', 'clone', '-b', 'main', str(remote), str(second)], check=True, capture_output=True)
    cp = make(repo)
    published = publish_checkpoint(repo, cp)
    assert published['published']
    assert git(repo, 'rev-list', '--count', cp['commit']) == '1'
    assert '.env' not in git(remote, 'ls-tree', '-r', '--name-only', cp['commit'])
    assert publish_checkpoint(repo, published) == published
    restored = restore_checkpoint(second, published, tmp_path / 'restored')
    assert (restored / 'a.py').read_text() == 'base'
    git(remote, 'update-ref', cp['ref'], git(repo, 'rev-parse', 'HEAD'))
    with pytest.raises(ValueError, match='immutable'):
        publish_checkpoint(repo, published)


def test_hash_mismatch_and_existing_destination(repo, tmp_path):
    cp = make(repo)
    with pytest.raises(ValueError, match='lock'):
        restore_checkpoint(repo, {**cp, 'lock_sha256': '0' * 64}, tmp_path / 'bad')
    with pytest.raises(ValueError):
        restore_checkpoint(repo, cp, repo)


@pytest.mark.parametrize('config', [{'api_key': 'private'}, {'rounds': None}, {'anchor': float('nan')}, {'meso': '1'}])
def test_invalid_config(repo, config):
    with pytest.raises(ValueError):
        create_checkpoint(repo, config=config, author='Test', description='candidate')


def test_bad_remote_and_public_schema(repo):
    git(repo, 'remote', 'add', 'origin', 'https://user:password@example.com/repo.git')
    with pytest.raises(ValueError):
        make(repo)
    git(repo, 'remote', 'remove', 'origin')
    cp = make(repo)
    for change in [{'surprise': 1}, {'published': 'yes'}, {'commit': 'bad'}, {'project_path': '../escape'}]:
        with pytest.raises(ValueError):
            validate_checkpoint({**cp, **change})


def test_source_secret_and_unsafe_link_rejected(repo, monkeypatch):
    monkeypatch.setenv('ARENA_API_KEY', 'a-real-private-key')
    (repo / 'a.py').write_text('key = "a-real-private-key"')
    with pytest.raises(ValueError, match='secret'):
        make(repo)
    (repo / 'a.py').write_text('safe')
    (repo / 'escape.py').symlink_to('/etc/passwd')
    with pytest.raises(ValueError, match='link'):
        make(repo)


def test_required_data_verified(repo, tmp_path):
    data = tmp_path / 'data.bin'
    data.write_bytes(b'dataset')
    cp = make(repo, data={'base': {'sha256': hashlib.sha256(b'dataset').hexdigest(), 'source': 'release/base'}})
    with pytest.raises(ValueError, match='data'):
        restore_checkpoint(repo, cp, tmp_path / 'missing')
    restored = restore_checkpoint(repo, cp, tmp_path / 'good', data_paths={'base': data})
    assert restored.is_dir()


def test_dirty_submodule_rejected(repo, tmp_path):
    child = tmp_path / 'child'
    child.mkdir()
    git(child, 'init')
    git(child, 'config', 'user.email', 'test@example.com')
    git(child, 'config', 'user.name', 'Test')
    (child / 'source.py').write_text('base')
    git(child, 'add', '.')
    git(child, 'commit', '-m', 'base')
    git(repo, '-c', 'protocol.file.allow=always', 'submodule', 'add', str(child), 'child')
    git(repo, 'commit', '-am', 'submodule')
    (repo / 'child/source.py').write_text('dirty')
    with pytest.raises(ValueError, match='submodule'):
        make(repo)


@pytest.mark.parametrize('change', [{'config': []}, {'data': []}, {'submodules': []}])
def test_malformed_nested_schema(repo, change):
    with pytest.raises(ValueError):
        validate_checkpoint({**make(repo), **change})


def test_restore_rejects_unrecorded_source_link(repo, tmp_path):
    cp = make(repo)
    (repo / '.env').unlink()
    git(repo, 'add', '-u')
    (repo / 'link').symlink_to('/etc/passwd')
    git(repo, 'add', 'link')
    git(repo, 'commit', '-m', 'unsafe')
    with pytest.raises(ValueError, match='link'):
        restore_checkpoint(repo, {**cp, 'commit': git(repo, 'rev-parse', 'HEAD')}, tmp_path / 'unsafe')


def test_publish_rejects_checkpoint_with_private_history(repo, tmp_path):
    remote = tmp_path / 'remote.git'
    subprocess.run(['git', 'init', '--bare', str(remote)], check=True, capture_output=True)
    git(repo, 'remote', 'add', 'origin', str(remote))
    cp = make(repo)
    commit = git(repo, 'rev-parse', 'HEAD')
    git(repo, 'update-ref', cp['ref'], commit)
    with pytest.raises(ValueError, match='private|parent'):
        publish_checkpoint(repo, {**cp, 'commit': commit})
    assert not git(repo, 'ls-remote', 'origin', cp['ref'])


def test_clean_submodule_and_ssh_transport(repo, tmp_path):
    child = tmp_path / 'child'
    child.mkdir()
    git(child, 'init')
    git(child, 'config', 'user.email', 'test@example.com')
    git(child, 'config', 'user.name', 'Test')
    (child / 'source.py').write_text('base')
    git(child, 'add', '.')
    git(child, 'commit', '-m', 'base')
    git(repo, '-c', 'protocol.file.allow=always', 'submodule', 'add', str(child), 'child')
    git(repo, 'commit', '-am', 'submodule')
    git(repo, 'remote', 'add', 'origin', 'git@example.com:team/repo.git')
    cp = make(repo)
    assert cp['submodules'] == {'child': git(child, 'rev-parse', 'HEAD')}
    assert cp['remote'] == 'git@example.com:team/repo.git'


@pytest.mark.parametrize('name', ['.lab-secrets.env', 'credentials.json', 'secrets.json', 'access-token.txt'])
def test_private_filename_excluded_without_environment_value(repo, name):
    (repo / name).write_text('unregistered-secret-value')
    git(repo, 'add', name)
    cp = make(repo)
    assert name not in git(repo, 'ls-tree', '-r', '--name-only', cp['commit']).splitlines()


def test_restore_rejects_transformed_source_bytes_and_cleans_worktree(repo, tmp_path):
    (repo / '.gitattributes').write_text('*.py text eol=crlf\n')
    (repo / 'a.py').write_bytes(b'line\n')
    cp = make(repo)
    destination = tmp_path / 'transformed'
    with pytest.raises(ValueError, match='source bytes'):
        restore_checkpoint(repo, cp, destination)
    assert not destination.exists()
    assert str(destination) not in git(repo, 'worktree', 'list', '--porcelain')


@pytest.mark.parametrize('config', [{'estimates': None}, {'claims': True}])
def test_dossier_features_require_data_manifest(repo, config):
    with pytest.raises(ValueError, match='data'):
        create_checkpoint(repo, config=config, author='Test', description='dossier')


def test_nested_clean_submodule_roundtrip(repo, tmp_path):
    nested = tmp_path / 'nested'
    nested.mkdir()
    git(nested, 'init')
    git(nested, 'config', 'user.email', 'test@example.com')
    git(nested, 'config', 'user.name', 'Test')
    (nested / 'n.py').write_bytes(b'nested\n')
    git(nested, 'add', '.')
    git(nested, 'commit', '-m', 'nested')
    child = tmp_path / 'child'
    child.mkdir()
    git(child, 'init')
    git(child, 'config', 'user.email', 'test@example.com')
    git(child, 'config', 'user.name', 'Test')
    git(child, '-c', 'protocol.file.allow=always', 'submodule', 'add', str(nested), 'nested')
    git(child, 'commit', '-am', 'child')
    git(repo, '-c', 'protocol.file.allow=always', 'submodule', 'add', str(child), 'child')
    git(repo, '-c', 'protocol.file.allow=always', 'submodule', 'update', '--init', '--recursive')
    git(repo, 'commit', '-am', 'submodule')
    cp = make(repo)
    assert cp['submodules']['child/nested'] == git(nested, 'rev-parse', 'HEAD')
    # Local fixtures are trusted temporary remotes; production retains Git default protocol policy.
    import os
    old = os.environ.get('GIT_ALLOW_PROTOCOL')
    os.environ['GIT_ALLOW_PROTOCOL'] = 'file'
    try:
        restored = restore_checkpoint(repo, cp, tmp_path / 'nested-restored')
    finally:
        if old is None:
            os.environ.pop('GIT_ALLOW_PROTOCOL', None)
        else:
            os.environ['GIT_ALLOW_PROTOCOL'] = old
    assert (restored / 'child/nested/n.py').read_bytes() == b'nested\n'


def test_injected_estimates_cannot_carry_unknown_credentials(repo):
    with pytest.raises(ValueError):
        create_checkpoint(repo, config={'estimates': {'credentials': 'not-in-environment'}},
                          author='Test', description='private config')
