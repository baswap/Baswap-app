#!/usr/bin/env python3
"""
requirements_versions.py

Scan requirements*.txt in a repo and print:
 - package name
 - declared version (== pinned, or specifier/range, or VCS tag if detectable)
 - installed version in current Python env (if available)
 - source file and original line

Usage:
    python requirements_versions.py [root_dir]
"""

from pathlib import Path
import re
import sys
import csv

try:
    from packaging.requirements import Requirement
    from packaging.specifiers import SpecifierSet
    HAS_PACKAGING = True
except Exception:
    HAS_PACKAGING = False

try:
    # Python 3.8+
    from importlib import metadata
except Exception:
    metadata = None

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')

VCS_EGG_RE = re.compile(r'[?#&]egg=([^&\s]+)', re.I)
VCS_TAG_RE = re.compile(r'@(?P<tag>[^/#\s]+)')  # finds @tag in URLs like ...git@v1.2.3 or ...@v1.2.3#
REQ_LINE_RE = re.compile(r'^\s*([A-Za-z0-9_.\-]+)\s*([=<>!~]{1,2}\s*[^;,\s]+)?', re.I)

def find_requirements_files(root: Path):
    for p in root.rglob('requirements*.txt'):
        if p.is_file():
            yield p

def parse_req_line(line: str):
    """Return tuple (name, declared_version_string_or_None, kind, original_line)
       kind: 'pin' for exact ==, 'range' for >=/<=/~=, 'vcs' for egg/url, 'editable', 'unknown'
    """
    raw = line.strip()
    if not raw or raw.startswith('#'):
        return None

    # include / constraint directives handled at higher level; here just parse normal lines
    if raw.startswith('-r') or raw.startswith('--requirement'):
        return ('__include__', raw.split(maxsplit=1)[1].strip() if len(raw.split())>1 else '', 'include', raw)
    if raw.startswith('-c') or raw.startswith('--constraint'):
        return ('__constraint__', raw.split(maxsplit=1)[1].strip() if len(raw.split())>1 else '', 'constraint', raw)

    # editable
    if raw.startswith('-e') or raw.startswith('--editable'):
        rem = raw.split(maxsplit=1)[1] if len(raw.split())>1 else ''
        m = VCS_EGG_RE.search(rem)
        if m:
            return (m.group(1), None, 'vcs', raw)
        # try to extract module name if there is package==syntax after -e
        try:
            if HAS_PACKAGING:
                req = Requirement(rem)
                spec = str(req.specifier) if req.specifier else None
                kind = 'pin' if req.specifier and '==' in str(req.specifier) else ('range' if req.specifier else 'editable')
                return (req.name, spec, kind, raw)
        except Exception:
            return ('__editable__', rem, 'editable', raw)
        return ('__editable__', rem, 'editable', raw)

    # VCS or URL with #egg
    m = VCS_EGG_RE.search(raw)
    if m:
        name = m.group(1)
        # try to get tag after @ in URL (best-effort)
        mt = VCS_TAG_RE.search(raw)
        tag = mt.group('tag') if mt else None
        return (name, tag, 'vcs', raw)

    # normal parsing: try packaging.Requirement if available
    if HAS_PACKAGING:
        try:
            req = Requirement(raw)
            name = req.name
            spec = str(req.specifier) if req.specifier else None
            if spec and '==' in spec:
                # pick the first '==' pin
                exact = None
                for s in str(req.specifier).split(','):
                    if s.strip().startswith('=='):
                        exact = s.strip().lstrip('=')
                        break
                return (name, exact or spec, 'pin' if exact else 'range', raw)
            return (name, spec, 'range' if spec else 'unversioned', raw)
        except Exception:
            pass

    # fallback simple regex
    m = REQ_LINE_RE.match(raw)
    if m:
        name = m.group(1)
        spec = m.group(2).strip() if m.group(2) else None
        kind = 'pin' if spec and '==' in spec else ('range' if spec else 'unversioned')
        # if spec like "==1.2.3", normalize to "1.2.3"
        if spec and '==' in spec:
            spec_val = spec.split('==',1)[1].strip()
            return (name, spec_val, 'pin', raw)
        return (name, spec, kind, raw)

    return ('__unknown__', None, 'unknown', raw)

def parse_requirements_file(path: Path, seen=None):
    if seen is None:
        seen = set()
    try:
        real = path.resolve()
    except Exception:
        real = path
    if real in seen:
        return []
    seen.add(real)
    out = []
    try:
        txt = real.read_text(encoding='utf-8', errors='ignore').splitlines()
    except Exception:
        return []
    for ln in txt:
        parsed = parse_req_line(ln)
        if not parsed:
            continue
        name, declared, kind, original = parsed
        if name in ('__include__', '__constraint__'):
            # resolve relative include path
            included = Path(declared)
            included_path = (real.parent / included).resolve()
            out.extend(parse_requirements_file(included_path, seen))
            continue
        out.append({
            'name': name,
            'declared': declared,
            'kind': kind,
            'source': str(real),
            'line': original
        })
    return out

def collect_all(root: Path):
    results = []
    for reqfile in find_requirements_files(root):
        results.extend(parse_requirements_file(reqfile))
    return results

def get_installed_version(name: str):
    if not name or name.startswith('__'):
        return None
    # try importlib.metadata
    if metadata is not None:
        try:
            return metadata.version(name)
        except Exception:
            # try normalized name fallback: replace '_' -> '-' etc
            alt = name.replace('_','-')
            try:
                return metadata.version(alt)
            except Exception:
                pass
    # try importing module and checking __version__
    modname = name.split('[')[0]  # handle extras
    modname = modname.split(':')[-1]
    # heuristic: try a few possible module names
    candidates = [modname, modname.split('-')[0], modname.split('.')[-1]]
    for c in candidates:
        try:
            m = __import__(c)
            ver = getattr(m, '__version__', None)
            if ver:
                return ver
        except Exception:
            pass
    return None

def print_table(rows):
    if not rows:
        print("No requirements*.txt entries found.")
        return
    # dedupe by (name, declared, source, line)
    seen = set()
    dedup = []
    for r in rows:
        key = (r['name'], r['declared'], r['source'], r['line'])
        if key in seen:
            continue
        seen.add(key)
        dedup.append(r)

    # gather installed versions
    for r in dedup:
        if r['name'] and not r['name'].startswith('__'):
            r['installed'] = get_installed_version(r['name'])
        else:
            r['installed'] = None

    # pretty print table
    width_name = 28
    width_decl = 20
    print(f"{'PACKAGE':{width_name}} {'DECLARED':{width_decl}} {'INSTALLED':12}  SOURCE")
    print("-"*(width_name + width_decl + 12 + 3 + 30))
    for r in sorted(dedup, key=lambda x: (x['installed'] is None, x['name'] or '')):
        name = r['name'] or ''
        declared = r['declared'] or ''
        installed = r.get('installed') or ''
        print(f"{name:{width_name}} {declared:{width_decl}} {installed:12}  {r['source']}")
    print("-"*10)
    print(f"Total entries: {len(dedup)}")

if __name__ == "__main__":
    rows = collect_all(ROOT)
    print_table(rows)

