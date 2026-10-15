#!/usr/bin/env python3
"""Prepare a source-only ytax package release tree from pinned Git objects.

Python 3.10+ standard library and Git. One package profile (packages/<name>/profile.json)
selects exact Git objects from named local repositories. No network, build, license
adoption, GitHub mutation, or execution of repository content is performed.
"""
from __future__ import annotations

import argparse
import datetime
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass

VERSION = '2.0.0'
MAX_FILE = 32 * 1024 * 1024
MAX_TOTAL = 512 * 1024 * 1024
KIT = Path(__file__).resolve().parent.parent
# The owner's decision to publish this exact plan. Content and legal checks are the QC gates.
APPROVAL_FLAGS = ('release_approved',)
# Status words that must not remain in prepared documents or the README. Split literals: this file
# ships in every package, and must not itself contain the markers.
DRAFT_MARKERS = re.compile(br'\bDRA' br'FT\b|NOT YET ' br'ADOPTED|\bPEND' br'ING\b|\bTO CON' br'FIRM\b|\bTB' br'D\b|'
                           br'COPYRIGHT_' br'YEARS|LICENSING_CONTACT_' br'TO_CONFIRM', re.I)
APPROVAL_KEYS = {'package', 'release_id', 'plan_sha256', 'approved_by', 'date', *APPROVAL_FLAGS}


class ReleaseError(Exception):
    pass


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def jbytes(value) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + '\n').encode()


def path_ok(value: str, empty: bool = False) -> str:
    if empty and value == '':
        return value
    p = PurePosixPath(value)
    if (not isinstance(value, str) or not value or p.is_absolute() or str(p) != value or
        any(x in ('', '.', '..', '.git') for x in value.split('/')) or
        any(ord(c) < 32 for c in value) or '\\' in value or ':' in value or
        any(x.endswith((' ', '.')) for x in value.split('/'))):
        raise ReleaseError(f'Unsafe/noncanonical relative path: {value!r}')
    return value


def join(prefix: str, rel: str) -> str:
    return path_ok(f'{prefix}/{rel}' if prefix and rel else prefix or rel)


def inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


CANDIDATE_PUBLIC_NAME = 'ytax release-candidate repository (private)'
# Every commit and tag the release tools make carries this identity, not the Git configuration of
# whoever runs them: it is public metadata of the released repository (2026-10-12).
RELEASE_IDENTITY = ('ytax release', 'release@ytax.ai')


def release_identity_env() -> dict:
    name, email = RELEASE_IDENTITY
    return {**os.environ, 'GIT_AUTHOR_NAME': name, 'GIT_AUTHOR_EMAIL': email,
            'GIT_COMMITTER_NAME': name, 'GIT_COMMITTER_EMAIL': email}


def public_profile(profile: dict) -> dict:
    """The profile as it ships: each repository under its public_name, if it has one, and the
    private candidate repository under a neutral name."""
    shipped = json.loads(json.dumps(profile))
    for spec in shipped.get('repositories', {}).values():
        if 'public_name' in spec:
            spec['name'] = spec.pop('public_name')
    if 'candidate_repository' in shipped:
        shipped['candidate_repository'] = CANDIDATE_PUBLIC_NAME
    return shipped


def load_profile(path: Path):
    raw = path.read_bytes()

    def unique_pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ReleaseError(f'Duplicate JSON key: {key}')
            result[key] = value
        return result
    profile = json.loads(raw.decode('utf-8'), object_pairs_hook=unique_pairs)
    if profile.get('schema_version') != 3:
        raise ReleaseError('Unsupported profile schema_version')
    if not re.fullmatch(r'ytax-[a-z0-9-]+', profile.get('package', '')):
        raise ReleaseError('Invalid package name')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', profile.get('release_id', '')):
        raise ReleaseError('Invalid release_id')
    if not profile['release_id'].startswith(profile['package'] + '-'):
        raise ReleaseError('release_id must start with the package name')
    repos = profile.get('repositories', {})
    if not repos:
        raise ReleaseError('Profile names no repositories')
    for name, spec in repos.items():
        if not re.fullmatch(r'[a-z_]+', name):
            raise ReleaseError(f'Invalid repository key: {name}')
        if not re.fullmatch(r'[0-9a-f]{40}', spec.get('commit', '')):
            raise ReleaseError(f'{name} commit must be an exact 40-character commit, not a branch')
        if not re.fullmatch(r'[A-Za-z0-9._-]+/[A-Za-z0-9._-]+', spec.get('name', '')):
            raise ReleaseError(f'{name} must name its owner/repository')
        if 'public_name' in spec and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 ()._-]{2,79}', spec['public_name']):
            raise ReleaseError(f'{name} public_name must be a short plain name')
    return profile, raw


@dataclass(frozen=True)
class Entry:
    path: str
    mode: str
    oid: str
    kind: str


class Repo:
    def __init__(self, key: str, name: str, path: Path, commit: str):
        self.key = key
        self.name = name
        self.path = path.resolve()
        self.commit = commit
        resolved = self.git('rev-parse', '--verify', commit + '^{commit}').decode().strip()
        if resolved != commit:
            raise ReleaseError('Commit did not resolve exactly')
        self.cache: dict[str, bytes] = {}

    def git(self, *args: str) -> bytes:
        env = {**os.environ, 'GIT_OPTIONAL_LOCKS': '0', 'GIT_TERMINAL_PROMPT': '0',
               'GIT_NO_LAZY_FETCH': '1', 'GIT_LITERAL_PATHSPECS': '1'}
        try:
            run = subprocess.run(['git', '-C', str(self.path), *args],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 env=env, check=True, timeout=120)
            return run.stdout
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            # Do not echo possible credential-bearing remote URLs from stderr.
            raise ReleaseError(f'Git read failed in {self.path}; ensure pinned objects are local') from exc

    def tree(self, prefix: str = '') -> dict[str, Entry]:
        path_ok(prefix, empty=True)
        args = ['ls-tree', '-r', '-z', '--full-tree', self.commit]
        if prefix:
            args += ['--', prefix]
        out = {}
        for item in self.git(*args).split(b'\0'):
            if not item:
                continue
            meta, name = item.split(b'\t', 1)
            mode, kind, oid = meta.decode().split()
            name = name.decode('utf-8')
            if prefix and name != prefix and not name.startswith(prefix + '/'):
                continue
            rel = name[len(prefix) + 1:] if prefix and name != prefix else ('' if prefix else name)
            if rel:
                path_ok(rel)
            out[rel] = Entry(name, mode, oid, kind)
        return out

    def blob(self, e: Entry) -> bytes:
        if e.kind != 'blob' or e.mode not in ('100644', '100755'):
            raise ReleaseError(f'Refuse symlink, submodule, or special entry: {e.path}')
        if e.oid not in self.cache:
            size = int(self.git('cat-file', '-s', e.oid))
            if size > MAX_FILE:
                raise ReleaseError(f'File exceeds configured safety limit: {e.path}')
            data = self.git('cat-file', 'blob', e.oid)
            if len(data) != size:
                raise ReleaseError('Git blob length mismatch')
            check = hashlib.sha1(b'blob ' + str(size).encode() + b'\0' + data).hexdigest()
            if check != e.oid:
                raise ReleaseError('Git blob ID mismatch')
            if data.startswith(b'version https://git-lfs.github.com/spec/v1'):
                raise ReleaseError(f'LFS pointer is not source content: {e.path}')
            self.cache[e.oid] = data
        return self.cache[e.oid]

    def file(self, name: str) -> Entry:
        entries = self.tree(name)
        if set(entries) != {''}:
            raise ReleaseError(f'Required file missing or not a regular file: {name}')
        return entries['']


def compare(left: dict[str, Entry], right: dict[str, Entry]):
    return {
        'unchanged': sorted(k for k in left.keys() & right.keys()
                            if (left[k].mode, left[k].oid) == (right[k].mode, right[k].oid)),
        'changed': sorted(k for k in left.keys() & right.keys()
                          if (left[k].mode, left[k].oid) != (right[k].mode, right[k].oid)),
        'added': sorted(right.keys() - left.keys()),
        'removed': sorted(left.keys() - right.keys()),
    }


def require_same(upstream, local, label):
    result = compare(upstream, local)
    if any(result[k] for k in ('changed', 'added', 'removed')):
        counts = {k: len(v) for k, v in result.items()}
        raise ReleaseError(f'Frozen {label} differs from its pin: {counts}')
    if not local:
        raise ReleaseError(f'Empty frozen component: {label}')
    return {k: len(v) for k, v in result.items()}


def xml_facts(data: bytes, name: str):
    if re.search(br'<!\s*(?:DOCTYPE|ENTITY)\b', data, re.I):
        raise ReleaseError(f'DTD/entity declaration refused: {name}')
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ReleaseError(f'XML parse error in {name}: {exc}') from exc
    if root.tag != 'FactDictionaryModule':
        raise ReleaseError(f'Unexpected dictionary root in {name}: {root.tag}')
    paths = {}
    for fact in root.findall('./Facts/Fact'):
        key = fact.get('path')
        if not key or key in paths:
            raise ReleaseError(f'Missing/duplicate Fact path in {name}: {key}')
        # Conservative syntax fingerprint: no scalar/whitespace normalization.
        paths[key] = sha(ET.tostring(fact, encoding='utf-8'))
    return paths


def secret_check(data: bytes, name: str):
    patterns = [br'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----',
                br'gh[pousr]_[A-Za-z0-9]{30,}', br'AKIA[A-Z0-9]{16}',
                br'https://[^\s"<>]+[?&]token=[A-Za-z0-9_-]{20,}']
    if any(re.search(p, data) for p in patterns):
        raise ReleaseError(f'Possible secret in {name}; review privately, do not publish')


def dictionary_content_hash(files: dict[str, bytes]) -> str:
    """The service's `adapter.dictionary_sha256()` over in-memory files.

    That function walks the tree with sorted(os.walk(...)): directories ordered by their full
    path string, files by name within a directory, hashing each forward-slash relative path
    followed by its bytes. Sorting on '' / '/<dir>' reproduces the directory order exactly."""
    h = hashlib.sha256()
    for rel in sorted(files, key=lambda r: (('/' + r.rsplit('/', 1)[0]) if '/' in r else '',
                                            r.rsplit('/', 1)[-1])):
        h.update(rel.encode())
        h.update(files[rel])
    return 'sha256:' + h.hexdigest()


def engine_pin(text: str) -> dict:
    """Read the pinned commit and dictionary content hash from the service's ENGINE-PIN.md."""
    commit = re.search(r'^\|\s*Pinned commit\s*\|\s*`([0-9a-f]{40})`', text, re.M)
    digest = re.search(r'^\|\s*\*\*Dictionary content hash\*\*\s*\|\s*`(sha256:[0-9a-f]{64})`', text, re.M)
    if not commit or not digest:
        raise ReleaseError('ENGINE-PIN.md does not state a pinned commit and dictionary content hash')
    return {'commit': commit.group(1), 'dictionary_sha256': digest.group(1)}


class Payload:
    def __init__(self):
        self.files: dict[str, bytes] = {}
        self.records: dict[str, dict] = {}
        self.folded: set[str] = set()
        self.total = 0

    def put(self, dest, data, record, mode='100644'):
        path_ok(dest)
        if dest.casefold() in self.folded:
            raise ReleaseError(f'Duplicate/case-colliding output path: {dest}')
        self.total += len(data)
        if len(data) > MAX_FILE or self.total > MAX_TOTAL:
            raise ReleaseError('Payload exceeds safety limits')
        secret_check(data, dest)
        self.folded.add(dest.casefold())
        self.files[dest] = data
        self.records[dest] = {**record, 'sha256': sha(data), 'bytes': len(data), 'mode': mode}

    def add(self, repo: Repo, entry: Entry, dest, component, origin='not_determined_by_diff'):
        self.put(dest, repo.blob(entry), {
            'component': component, 'source_repository': repo.name, 'source_commit': repo.commit,
            'source_path': entry.path, 'git_blob': entry.oid, 'origin_comparison': origin,
            'rights': 'See legal/COMPONENT-SCOPE.md; no ownership inference from diff'}, entry.mode)


def prepare(args):
    profile, profile_bytes = load_profile(args.profile)
    paths = dict(args.repo or [])
    repos: dict[str, Repo] = {}
    for key, spec in profile['repositories'].items():
        if key not in paths:
            raise ReleaseError(f'No local path given for repository {key} (--repo {key}=PATH)')
        # Shipped files name a repository by its public_name; the private name is only for fetching.
        repos[key] = Repo(key, spec.get('public_name', spec['name']), Path(paths[key]), spec['commit'])

    def repo(key) -> Repo:
        if key not in repos:
            raise ReleaseError(f'Profile refers to undeclared repository: {key}')
        return repos[key]

    payload = Payload()
    checks: dict[str, object] = {}
    frozen: dict[str, dict[str, Entry]] = {}

    # Frozen imports: the local copy must equal its upstream pin by path, blob, and mode. An import
    # that names a `changed_component` carries ytax changes instead: every file is still compared
    # with the pin, identical files keep the upstream origin, and changed or added files go to that
    # ytax component, so the header and license gates see them as ytax material.
    for spec in profile.get('frozen', []):
        local_repo, upstream_repo = repo(spec['repo']), repo(spec['upstream_repo'])
        excluded = [path_ok(x) for x in spec.get('upstream_exclude', [])]
        upstream = {k: v for k, v in upstream_repo.tree(path_ok(spec['upstream_path'], empty=True)).items()
                    if not any(k == x or k.startswith(x + '/') for x in excluded)}
        local = local_repo.tree(path_ok(spec['path']))
        changed_component = spec.get('changed_component')
        if changed_component is None:
            checks['frozen_' + spec['label']] = require_same(upstream, local, spec['label'])
            origins = dict.fromkeys(local, ('identical_to_pinned_upstream', spec['component']))
        else:
            if not local:
                raise ReleaseError(f'Empty frozen component: {spec["label"]}')
            if changed_component == spec['component']:
                raise ReleaseError(f'{spec["label"]}: changed_component must differ from component')
            diff = compare(upstream, local)
            checks['frozen_' + spec['label']] = {**{k: len(v) for k, v in diff.items()},
                                                 'changed_paths': diff['changed'], 'added_paths': diff['added'],
                                                 'removed_paths': diff['removed']}
            origins = {**dict.fromkeys(diff['unchanged'], ('identical_to_pinned_upstream', spec['component'])),
                       **dict.fromkeys(diff['changed'], ('changed_from_pinned_upstream', changed_component)),
                       **dict.fromkeys(diff['added'], ('not_in_pinned_upstream', changed_component))}
        frozen[spec['label']] = local
        for rel, e in sorted(local.items()):
            origin, component = origins[rel]
            payload.add(local_repo, e, join(spec['dest'], rel), component, origin)
    for spec in profile.get('identical_files', []):
        local_repo, upstream_repo = repo(spec['repo']), repo(spec['upstream_repo'])
        local, upstream = local_repo.file(path_ok(spec['path'])), upstream_repo.file(path_ok(spec['upstream_path']))
        if local_repo.blob(local) != upstream_repo.blob(upstream):
            raise ReleaseError(f'{spec["path"]} does not match pinned {upstream_repo.name} {spec["upstream_path"]}')
        payload.add(upstream_repo, upstream, path_ok(spec['dest']), spec['component'], 'pinned_upstream')

    # The development repository's own UPSTREAM.md must agree with the configured pins.
    if 'upstream_md' in profile:
        spec = profile['upstream_md']
        text = repo(spec['repo']).blob(repo(spec['repo']).file(path_ok(spec['path'])))
        needed = [repo(k).commit for k in spec.get('commits_of', [])] + spec.get('mentions', [])
        missing = [v for v in needed if v.encode() not in text]
        if missing:
            raise ReleaseError(f'{spec["path"]} and profile disagree; not mentioned: {missing}')
        checks['upstream_md'] = {'repository': repo(spec['repo']).name, 'path': spec['path'],
                                 'sha256': sha(text), 'mentions_verified': len(needed)}

    # Complete living dictionary tree, compared against a frozen baseline when one is named.
    dictionary_files: dict[str, bytes] = {}
    facts_report, file_comparison = {}, {}
    if 'dictionary' in profile:
        spec = profile['dictionary']
        dev = repo(spec['repo'])
        living = dev.tree(path_ok(spec['path']))
        if not living:
            raise ReleaseError('No living dictionary selected')
        if 'FactDictionaryModule.rng' not in living:
            raise ReleaseError('Required FactDictionaryModule.rng missing from selected dictionary')
        baseline = frozen.get(spec.get('baseline', ''), {})
        file_comparison = compare(baseline, {k: e for k, e in living.items()
                                             if '/' not in k and k.endswith(('.xml', '.rng'))})
        global_paths = {}
        for rel, e in sorted(living.items()):
            origin = ('identical_to_pinned_upstream' if rel in baseline and
                      (e.oid, e.mode) == (baseline[rel].oid, baseline[rel].mode)
                      else 'changed_from_same_path_baseline' if rel in baseline
                      else 'absent_from_this_baseline_not_proof_of_originality')
            payload.add(dev, e, join(spec['dest'], rel), spec['component'], origin)
            dictionary_files[rel] = dev.blob(e)
            if '/' not in rel and rel.endswith('.xml'):
                current = xml_facts(dev.blob(e), rel)
                for key in current:
                    if key in global_paths:
                        raise ReleaseError(f'Duplicate Fact path across loaded modules: {key}')
                    global_paths[key] = rel
                old = xml_facts(dev.blob(baseline[rel]), rel) if rel in baseline else {}
                facts_report[rel] = {
                    'baseline_facts': len(old), 'current_facts': len(current),
                    'added_paths': sorted(current.keys() - old.keys()),
                    'removed_paths': sorted(old.keys() - current.keys()),
                    'changed_syntax_paths': sorted(k for k in old.keys() & current.keys()
                                                   if old[k] != current[k]),
                    'note': 'Conservative parsed-syntax comparison, not behavior/ownership analysis',
                }
        checks['dictionary_content_hash'] = dictionary_content_hash(dictionary_files)

    # The service's engine pin: the development commit and dictionary bytes must be exactly it.
    if 'service_pin' in profile:
        spec = profile['service_pin']
        service = repo(spec['repo'])
        pin = engine_pin(service.blob(service.file(path_ok(spec['path']))).decode('utf-8'))
        result = {'repository': service.name, 'service_commit': service.commit, 'path': spec['path'],
                  'pinned_commit': pin['commit'], 'pinned_dictionary_sha256': pin['dictionary_sha256']}
        if 'development' in spec:
            if repo(spec['development']).commit != pin['commit']:
                raise ReleaseError(f'{spec["development"]} commit is not the service engine pin {pin["commit"]}')
            result['development_commit_matches'] = True
        if dictionary_files:
            if checks['dictionary_content_hash'] != pin['dictionary_sha256']:
                raise ReleaseError('Dictionary content hash differs from the service engine pin')
            result['dictionary_content_hash_matches'] = True
        if 'facts_profile' in spec:
            facts, _ = load_profile(kit_file(args.kit, spec['facts_profile']))
            facts_commit = facts['repositories']['development']['commit']
            if facts_commit != pin['commit']:
                raise ReleaseError(f'Service engine pin {pin["commit"]} is not the ytax-facts development '
                                   f'commit {facts_commit} in {spec["facts_profile"]}')
            # A package built on ytax-facts input ships under the same license text, so a release under
            # one license cannot become a route to the same material under another without a
            # separate owner decision (docs/LEGAL-RECORD.md, decision 13).
            own, theirs = profile.get('prepared', {}).get('LICENSE'), facts.get('prepared', {}).get('LICENSE')
            if own != theirs:
                raise ReleaseError(f'License text {own} differs from {theirs} of the ytax-facts release '
                                   f'{facts["release_id"]}; using it as input needs a separate owner decision')
            result['facts_release_id'] = facts['release_id']
            result['facts_profile_commit_matches'] = True
        if not any(k in result for k in ('development_commit_matches', 'dictionary_content_hash_matches',
                                         'facts_profile_commit_matches')):
            raise ReleaseError('service_pin checks nothing: name a development repository or a facts_profile')
        checks['service_pin'] = result

    adapters = {}
    if 'generator' in profile:
        spec = profile['generator']
        dev, df = repo(spec['repo']), repo(spec['upstream_repo'])
        for rel in spec['files']:
            path_ok(rel)
            current = dev.file(join(spec['path'], rel))
            old = df.file(join(spec['upstream_path'], rel))
            same = (current.oid, current.mode) == (old.oid, old.mode)
            adapters[rel] = {'upstream_blob': old.oid, 'ytax_blob': current.oid,
                             'status': 'unchanged' if same else 'changed'}
            payload.add(dev, current, join(spec['dest'], rel), spec['component'],
                        'identical_to_pinned_upstream' if same else 'changed_from_pinned_upstream')
            payload.add(df, old, join(spec['upstream_dest'], rel), spec['upstream_component'],
                        'pinned_upstream')

    # Explicit file and tree selections, with exact exclusions that must all be exercised.
    # `exclude_globs` (fnmatch, where `*` also crosses `/`) drop whole kinds of file from a selection's
    # trees, such as the blank IRS PDFs beside their field maps; each must drop at least one file,
    # and none may match a file that `files` names explicitly.
    for spec in profile.get('selections', []):
        source = repo(spec['repo'])
        dest = path_ok(spec.get('dest', ''), empty=True)
        selected, excluded, seen_excluded = set(), {path_ok(x) for x in spec.get('exclude', [])}, set()
        globs = spec.get('exclude_globs', [])
        if not isinstance(globs, list) or not all(isinstance(g, str) and g for g in globs):
            raise ReleaseError(f'Selection {spec["component"]}: exclude_globs must be a list of patterns')
        seen_globs = set()
        for rel in spec.get('files', []):
            path_ok(rel)
            if rel in excluded or rel in selected or any(fnmatch.fnmatchcase(rel, g) for g in globs):
                raise ReleaseError(f'File both selected and excluded, or duplicated: {rel}')
            selected.add(rel)
            payload.add(source, source.file(rel), join(dest, rel), spec['component'])
        for prefix in spec.get('trees', []):
            entries = source.tree(path_ok(prefix))
            if not entries:
                raise ReleaseError(f'Empty tree selection: {source.name} {prefix}')
            for rel, entry in sorted(entries.items()):
                source_path = join(prefix, rel)
                if source_path in excluded:
                    seen_excluded.add(source_path)
                    continue
                matched = {g for g in globs if fnmatch.fnmatchcase(source_path, g)}
                if matched:
                    seen_globs |= matched
                    continue
                if source_path in selected:
                    raise ReleaseError(f'Overlapping selection: {source_path}')
                selected.add(source_path)
                payload.add(source, entry, join(dest, source_path), spec['component'])
        if not selected:
            raise ReleaseError(f'Selection {spec["component"]} selected nothing')
        if seen_excluded != excluded:
            raise ReleaseError(f'Exclusions did not match selected tree files: {sorted(excluded - seen_excluded)}')
        if seen_globs != set(globs):
            raise ReleaseError(f'Exclusion patterns matched no selected tree file: {sorted(set(globs) - seen_globs)}')

    if not payload.files:
        raise ReleaseError('Profile selects no source files')
    kit = args.kit.resolve()
    for dest, rel in sorted(profile.get('prepared', {}).items()):
        path_ok(dest), path_ok(rel)
        p = kit / rel
        if not p.is_file() or any(x.is_symlink() for x in [p, *p.parents]) or not inside(p.resolve(), kit):
            raise ReleaseError(f'Missing/unsafe prepared file: {rel}')
        payload.put(dest, p.read_bytes(), {'component': 'prepared-documents', 'kit_path': rel})
    shipped_profile = public_profile(profile)
    payload.put('docs/release/profile.json', jbytes(shipped_profile), {'component': 'release-profile'})
    payload.put('tools/build_release.py', Path(__file__).read_bytes(), {'component': 'release-builder'})

    draft_files = sorted(name for name, data in payload.files.items()
                         if payload.records[name].get('component') == 'prepared-documents'
                         and name != 'LICENSE' and DRAFT_MARKERS.search(data))
    if DRAFT_MARKERS.search(kit_file(kit, profile['readme']).read_bytes()):
        draft_files.append(profile['readme'])
    plan = {
        'schema_version': 3, 'package': profile['package'], 'release_id': profile['release_id'],
        'product': 'ytax', 'entity': 'TRIPLE J AI LLC', 'profile': shipped_profile,
        'profile_sha256': sha(profile_bytes), 'builder_version': VERSION,
        'builder_sha256': sha(Path(__file__).read_bytes()),
        'readme_template_sha256': sha(kit_file(kit, profile['readme']).read_bytes()),
        'repositories': {k: {'name': r.name, 'commit': r.commit} for k, r in repos.items()},
        'checks': checks, 'payload': payload.records,
        'dictionary_file_comparison': file_comparison, 'dictionary_fact_comparison': facts_report,
        'generator_comparison': adapters, 'draft_legal_files': draft_files,
        'limitations': profile.get('limitations', []) + [
            'No tax-correctness or runtime tests executed by this exporter',
            'No automatic copyright, relicensing, or PII clearance',
            'Only the selected pinned Git objects are read; working-tree edits are ignored'],
    }
    return profile, plan, sha(jbytes(plan)), payload.files, repos


def write_new(path: Path, data: bytes, mode='100644'):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as f:
        f.write(data)
    path.chmod(0o755 if mode == '100755' else 0o644)


def check_approver_and_date(approval: dict):
    """The approver is a person's name and the date a real past-or-today YYYY-MM-DD date."""
    if set(approval) - APPROVAL_KEYS:
        raise ReleaseError(f'Approval has unexpected keys: {sorted(set(approval) - APPROVAL_KEYS)}')
    if not re.fullmatch(r'[0-9a-f]{64}', str(approval.get('plan_sha256', ''))):
        raise ReleaseError('Approval must name a plan_sha256')
    who, date = approval.get('approved_by'), approval.get('date')
    words = re.findall(r'[^\W\d_]+', who) if isinstance(who, str) else []
    # Split literals: this file ships, and the internal-notes lint must not match it.
    placeholders = {'pending', 'tbd', 'to' 'do', 'complete', 'owner', 'me', 'name', 'dra' 'ft', 'unknown',
                    'placeholder', 'approver', 'test', 'user', 'none', 'nobody', 'someone', 'fix' 'me'}
    if (not isinstance(who, str) or not re.fullmatch(r"[^\W\d_](?:[^\W\d_]|[ .'-]){1,79}", who)
            or sum(len(w) for w in words) < 2 or {w.lower() for w in words} & placeholders):
        raise ReleaseError('Approval must name the approver (a name, not an address or placeholder)')
    valid = isinstance(date, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', date) is not None
    try:
        valid = valid and datetime.date(2026, 1, 1) <= datetime.date.fromisoformat(date) <= datetime.date.today()
    except ValueError:
        valid = False
    if not valid:
        raise ReleaseError('Approval date must be a real YYYY-MM-DD date, not in the future')


def check_approval(approval_path: Path | None, digest: str, plan: dict):
    if plan['draft_legal_files']:
        raise ReleaseError('Public export blocked: prepared documents still contain status words or placeholders')
    if not approval_path:
        raise ReleaseError('Public export requires a reviewed, hash-bound approval file')
    approval = json.loads(approval_path.read_text())
    if approval.get('plan_sha256') != digest or not all(approval.get(x) is True for x in APPROVAL_FLAGS):
        raise ReleaseError('Public approval is missing, incomplete, or stale for this exact plan')
    if approval.get('package') not in (None, plan['package']):
        raise ReleaseError('Public approval names a different package')
    check_approver_and_date(approval)


def kit_file(kit: Path, rel: str) -> Path:
    p = (kit / path_ok(rel)).resolve()
    if not inside(p, kit.resolve()) or not p.is_file():
        raise ReleaseError(f'Missing kit file: {rel}')
    return p


def generated_files(profile: dict, plan: dict, digest: str, audience: str, kit: Path) -> dict[str, bytes]:
    public = audience == 'public'
    template = kit_file(kit, profile['readme']).read_text('utf-8')
    status = ('Public source release' if public else
              'PRIVATE review candidate; not approved for public publication')
    readme = template.replace('{{release_id}}', profile['release_id']).replace('{{audience}}', status)
    lines = ['# Pinned sources\n\n']
    for key, r in plan['repositories'].items():
        lines.append(f'- {key}: `{r["name"]}@{r["commit"]}`\n')
    lines.append('\nSee `provenance/release.json` for per-file identities, comparisons, and checks. '
                 '`upstream/`, where present, is evidence, never a runtime load directory.\n')
    return {
        'README.md': readme.encode(),
        'UPSTREAM.md': ''.join(lines).encode(),
        'provenance/release.json': jbytes({'plan_sha256': digest, 'audience': audience,
                                          'public_publication_approved': public, 'plan': plan}),
        '.gitattributes': b'* -text\n',
        '.gitignore': ''.join(x + '\n' for x in profile.get('gitignore', [])).encode(),
    }


def build(args):
    profile, plan, digest, payload, repos = prepare(args)
    if args.command == 'plan':
        report = {'plan_sha256': digest, 'plan': plan}
        if args.report:
            write_new(args.report, jbytes(report))
        print(json.dumps({'package': plan['package'], 'release_id': plan['release_id'],
                          'plan_sha256': digest, 'payload_files': len(payload),
                          'checks': plan['checks'], 'draft_legal_files': plan['draft_legal_files']},
                         indent=2))
        return
    if args.audience == 'public':
        check_approval(args.approval, digest, plan)
    out = args.out.absolute()
    if out.exists() or out.is_symlink():
        raise ReleaseError('Output must be a new path; no overwrite or merge is permitted')
    out.parent.mkdir(parents=True, exist_ok=True)
    out = out.parent.resolve() / out.name
    inputs = [r.path for r in repos.values()] + [args.kit.resolve()]
    if any(inside(out, p) or inside(p, out) for p in inputs):
        raise ReleaseError('Output must be outside all input repositories and the kit')
    temp = Path(tempfile.mkdtemp(prefix='.ytax-stage-', dir=out.parent))
    try:
        for name, data in sorted(payload.items()):
            write_new(temp / name, data, plan['payload'][name]['mode'])
        for name, data in generated_files(profile, plan, digest, args.audience, args.kit).items():
            if name.casefold() in {p.casefold() for p in payload}:
                raise ReleaseError(f'Generated path collision: {name}')
            write_new(temp / path_ok(name), data)
        files = sorted(p for p in temp.rglob('*') if p.is_file())
        sums = ''.join(f'{sha(p.read_bytes())}  {p.relative_to(temp).as_posix()}\n' for p in files)
        write_new(temp / 'SHA256SUMS', sums.encode())
        verify(temp)
        if out.exists():
            raise ReleaseError('Output was created concurrently; refusing replacement')
        temp.rename(out)
    except BaseException:
        shutil.rmtree(temp, ignore_errors=True)
        raise
    print(json.dumps({'output': str(out), 'package': plan['package'], 'release_id': plan['release_id'],
                      'plan_sha256': digest, 'audience': args.audience,
                      'public_publication_approved': args.audience == 'public',
                      'payload_files': len(payload)}, indent=2))


def verify(root: Path):
    root = root.resolve()
    if not (root / 'SHA256SUMS').is_file():
        raise ReleaseError('SHA256SUMS missing')
    expected = set()
    for line in (root / 'SHA256SUMS').read_text().splitlines():
        digest, name = line.split('  ', 1)
        path_ok(name)
        if name in expected or not re.fullmatch('[0-9a-f]{64}', digest):
            raise ReleaseError('Malformed checksum manifest')
        expected.add(name)
        p = root / name
        if not p.is_file() or p.is_symlink() or sha(p.read_bytes()) != digest:
            raise ReleaseError(f'Missing/changed payload: {name}')
    actual = set()
    for base, dirs, names in os.walk(root, followlinks=False):
        # A newly initialized local .git directory is not part of the source payload.
        if Path(base) == root and '.git' in dirs:
            dirs.remove('.git')
        for name in dirs + names:
            p = Path(base) / name
            if p.is_symlink():
                raise ReleaseError(f'Symlink in output: {p.relative_to(root)}')
        for name in names:
            rel = (Path(base) / name).relative_to(root).as_posix()
            if rel != 'SHA256SUMS':
                actual.add(rel)
    if actual != expected:
        raise ReleaseError(f'Unexpected/missing output paths: {sorted(actual ^ expected)[:10]}')
    release = json.loads((root / 'provenance/release.json').read_text())
    if sha(jbytes(release['plan'])) != release['plan_sha256']:
        raise ReleaseError('Plan digest mismatch')
    for name, record in release['plan']['payload'].items():
        if sha((root / name).read_bytes()) != record['sha256']:
            raise ReleaseError(f'Payload differs from plan: {name}')
        if os.name != 'nt':
            executable = bool((root / name).stat().st_mode & 0o111)
            if executable != (record['mode'] == '100755'):
                raise ReleaseError(f'Executable bit differs from plan: {name}')
    return len(expected)


def verify_index(root: Path):
    """Confirm git add did not omit/transform files before a commit/push."""
    count = verify(root)
    root = root.resolve()
    expected = {}
    for line in (root / 'SHA256SUMS').read_text().splitlines():
        digest, name = line.split('  ', 1)
        expected[name] = digest
    expected['SHA256SUMS'] = sha((root / 'SHA256SUMS').read_bytes())
    cmd = ['git', '-C', str(root)]
    try:
        index = subprocess.check_output(cmd + ['ls-files', '--stage', '-z'], stderr=subprocess.DEVNULL)
        indexed = {}
        for item in index.split(b'\0'):
            if not item:
                continue
            meta, name = item.split(b'\t', 1)
            mode, oid, stage = meta.decode().split()
            name = name.decode('utf-8')
            path_ok(name)
            if stage != '0' or mode not in ('100644', '100755'):
                raise ReleaseError('Index has conflicts, symlinks, or submodules')
            data = subprocess.check_output(cmd + ['cat-file', 'blob', oid], stderr=subprocess.DEVNULL)
            indexed[name] = sha(data)
            expected_mode = '100755' if (root / name).stat().st_mode & 0o111 else '100644'
            if os.name != 'nt' and mode != expected_mode:
                raise ReleaseError(f'Staged executable mode differs: {name}')
        if indexed != expected:
            raise ReleaseError('Git index differs from the release tree (missing, extra, or transformed files)')
    except subprocess.CalledProcessError as exc:
        raise ReleaseError('Cannot read candidate Git index') from exc
    return count + 1


def repo_arg(value: str):
    key, sep, path = value.partition('=')
    if not sep or not re.fullmatch(r'[a-z_]+', key) or not path:
        raise argparse.ArgumentTypeError('expected NAME=PATH')
    return key, path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('plan', 'build'):
        p = sub.add_parser(command)
        p.add_argument('--profile', type=Path, required=True)
        p.add_argument('--repo', type=repo_arg, action='append',
                       help='NAME=PATH of a local Git repository holding the pinned objects')
        p.add_argument('--kit', type=Path, default=KIT, help='release kit root (prepared documents)')
        if command == 'plan':
            p.add_argument('--report', type=Path)
        else:
            p.add_argument('--out', type=Path, required=True)
            p.add_argument('--audience', choices=('private', 'public'), default='private')
            p.add_argument('--approval', type=Path)
    for command in ('verify', 'verify-index'):
        p = sub.add_parser(command)
        p.add_argument('tree', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'verify-index':
            print(f'Verified {verify_index(args.tree)} staged Git files.')
        elif args.command == 'verify':
            print(f'Verified {verify(args.tree)} checksummed files (integrity, not publisher authenticity).')
        else:
            build(args)
    except (ReleaseError, OSError, ValueError, KeyError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
