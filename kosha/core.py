"""Packages, the registry, and what's installed.

A package is a git repository. Installing clones it into the folder its
kind prescribes and checks out its newest release tag; updating fetches
and checks out a newer tag. What kosha installed is recorded in
~/.local/state/kosha/installed.json, but the git checkout itself is the
truth: kosha reads the version from it, so a tool installed by hand is
recognised ("adopted") too.
"""
import concurrent.futures
import json
import os
import re
import shutil
import subprocess
import time
import tomllib
import urllib.request

HOME = os.path.expanduser("~")
DATA = os.environ.get("XDG_DATA_HOME") or os.path.join(HOME, ".local/share")
STATE = os.path.join(os.environ.get("XDG_STATE_HOME") or os.path.join(HOME, ".local/state"), "kosha")
CACHE = os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.join(HOME, ".cache"), "kosha")
BIN = os.path.join(HOME, ".local/bin")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY_URL = "https://raw.githubusercontent.com/Theyashsawarkar/kosha/main/registry.toml"
TAG = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


class KoshaError(Exception):
    pass


def vkey(tag):
    m = TAG.match(tag or "")
    return tuple(int(x) for x in m.groups()) if m else (-1, -1, -1)


def git(args, cwd=None, timeout=120, check=True):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_ASKPASS="true")
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
    if check and r.returncode != 0:
        raise KoshaError((r.stderr.strip() or r.stdout.strip() or f"git {args[0]} failed").splitlines()[-1])
    return r.stdout.strip()


# ===================================================================== registry
def load_registry():
    """The newest of: the cached copy `kosha refresh` downloaded, and the one
    shipped with kosha."""
    cands = [os.path.join(CACHE, "registry.toml"), os.path.join(ROOT, "registry.toml")]
    best = None
    for p in cands:
        try:
            with open(p, "rb") as f:
                reg = tomllib.load(f)
        except (OSError, tomllib.TOMLDecodeError):
            continue
        mtime = os.path.getmtime(p)
        if best is None or mtime > best[0]:
            best = (mtime, reg, p)
    if best is None:
        raise KoshaError("no registry: reinstall kosha or run `kosha refresh`")
    reg = best[1]
    if reg.get("format", 1) > 1:
        raise KoshaError("the registry is newer than this kosha: run `kosha self-update`")
    return {n: Package(n, d) for n, d in reg.get("packages", {}).items()}, best[2]


def refresh_registry():
    req = urllib.request.Request(REGISTRY_URL, headers={"User-Agent": "kosha"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = r.read()
    tomllib.loads(data.decode())   # don't keep something broken
    os.makedirs(CACHE, exist_ok=True)
    tmp = os.path.join(CACHE, "registry.toml.tmp")
    open(tmp, "wb").write(data)
    os.replace(tmp, os.path.join(CACHE, "registry.toml"))


# ===================================================================== state
def load_state():
    try:
        with open(os.path.join(STATE, "installed.json")) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_state(state):
    os.makedirs(STATE, exist_ok=True)
    tmp = os.path.join(STATE, "installed.json.tmp")
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
    os.replace(tmp, os.path.join(STATE, "installed.json"))


def log(line):
    os.makedirs(STATE, exist_ok=True)
    with open(os.path.join(STATE, "history.log"), "a") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + line + "\n")


# ===================================================================== packages
class Package:
    def __init__(self, name, d):
        self.name = name
        self.repo = d["repo"]
        self.kind = d.get("kind", "app")
        self.description = d.get("description", "")
        self.requires = d.get("requires", [])
        self.commands = d.get("commands", [])
        self.arch = d.get("arch", [])
        self.post = d.get("post")
        # a new or removed Vyom tool shows up once the running Vyom reloads
        self.reload = d.get("reload", "vyom reload" if self.kind == "vyom-tool" else None)
        self.link = d.get("link", True)

    @property
    def url(self):
        return self.repo if "://" in self.repo or self.repo.startswith("git@") else f"https://github.com/{self.repo}"

    @property
    def path(self):
        if self.kind == "vyom":
            return os.path.join(DATA, "vyom", "core")
        if self.kind == "vyom-tool":
            return os.path.join(DATA, "vyom", "plugins", self.name)
        if self.kind == "tmux-plugin":
            return os.path.join(HOME, ".tmux", "plugins", self.name)
        return os.path.join(DATA, self.name)

    @property
    def bin_target(self):
        """(link in ~/.local/bin, what it points to) or None."""
        if not self.link or self.kind == "vyom-tool":
            return None
        return os.path.join(BIN, self.name), os.path.join(self.path, "bin", self.name)

    # ---- what's on disk
    def installed(self):
        return os.path.isdir(os.path.join(self.path, ".git")) or os.path.islink(self.path)

    def linked(self):
        """A development checkout linked in place (`kosha link`)."""
        return os.path.islink(self.path)

    def version(self):
        """The release tag checked out, or `<tag>+<n>` / a short commit when off a tag."""
        if not self.installed():
            return None
        try:
            return git(["describe", "--tags", "--always"], cwd=self.path, timeout=10)
        except (KoshaError, subprocess.TimeoutExpired):
            return "?"

    def exact_tag(self):
        v = self.version() or ""
        return v if TAG.match(v) else None

    def dirty(self):
        if not self.installed():
            return False
        try:
            return bool(git(["status", "--porcelain", "--untracked-files=no"], cwd=self.path, timeout=10))
        except KoshaError:
            return False

    def remote_tags(self):
        out = git(["ls-remote", "--tags", "--refs", self.url], timeout=30)
        tags = [l.split("refs/tags/")[1] for l in out.splitlines() if "refs/tags/" in l]
        return sorted((t for t in tags if TAG.match(t)), key=vkey)

    def latest(self):
        tags = self.remote_tags()
        return tags[-1] if tags else None

    def missing_commands(self):
        return [c for c in self.commands if not shutil.which(c)]


def latest_versions(pkgs):
    """{name: latest tag or Exception}, asked in parallel."""
    out = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
        futs = {ex.submit(p.latest): p.name for p in pkgs}
        for f in concurrent.futures.as_completed(futs):
            try:
                out[futs[f]] = f.result()
            except Exception as e:   # one unreachable repo mustn't stop the rest
                out[futs[f]] = e
    return out


def resolve(names, registry):
    """names plus everything they require, dependencies first."""
    order, seen = [], set()

    def visit(n, chain):
        if n in chain:
            raise KoshaError(f"dependency cycle: {' -> '.join(chain + [n])}")
        if n in seen:
            return
        if n not in registry:
            raise KoshaError(f"no package called {n} (kosha search lists them)")
        for dep in registry[n].requires:
            visit(dep, chain + [n])
        seen.add(n)
        order.append(n)
    for n in names:
        visit(n, [])
    return order


def dependents(name, registry):
    return [p.name for p in registry.values() if name in p.requires and p.installed()]


# ===================================================================== actions
def checkout(pkg, tag):
    git(["-c", "advice.detachedHead=false", "checkout", "-q", tag], cwd=pkg.path)


def link_bin(pkg):
    t = pkg.bin_target
    if not t or not os.path.exists(t[1]):
        return None
    link, target = t
    os.makedirs(BIN, exist_ok=True)
    if os.path.lexists(link):
        if os.path.islink(link) and os.readlink(link) == target:
            return link
        if not os.path.islink(link):
            raise KoshaError(f"{link} exists and isn't a link: move it away first")
        os.remove(link)
    os.symlink(target, link)
    return link


def run_hook(cmd, cwd):
    if not cmd:
        return
    r = subprocess.run(cmd, shell=True, cwd=cwd)
    if r.returncode != 0:
        raise KoshaError(f"`{cmd}` failed (exit {r.returncode})")


def reload_hook(pkg):
    if pkg.reload:
        try:
            subprocess.run(pkg.reload, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
        except Exception:
            pass


def install(pkg, version=None, state=None):
    """Clones (or adopts an existing clone) and checks out version (default:
    the newest release; a repo without releases stays on its default branch)."""
    state = load_state() if state is None else state
    adopted = False
    if pkg.installed():
        if pkg.linked():
            raise KoshaError(f"{pkg.name} is a linked development checkout (kosha unlink {pkg.name} first)")
        remote = git(["remote", "get-url", "origin"], cwd=pkg.path, check=False)
        if pkg.repo.split("/")[-1] not in remote:
            raise KoshaError(f"{pkg.path} is a clone of something else ({remote})")
        adopted = True
        git(["fetch", "-q", "--tags", "--force", "origin"], cwd=pkg.path)
    else:
        os.makedirs(os.path.dirname(pkg.path), exist_ok=True)
        git(["clone", "-q", pkg.url, pkg.path], timeout=300)
    tags = sorted((t for t in git(["tag", "-l"], cwd=pkg.path).splitlines() if TAG.match(t)), key=vkey)
    # adopting a clone keeps the version it's on; a fresh clone gets the newest release
    target = version or (None if adopted else tags[-1] if tags else None)
    if version and version not in tags:
        alt = "v" + version if not version.startswith("v") else version[1:]
        target = alt if alt in tags else None
        if not target:
            raise KoshaError(f"{pkg.name} has no release {version} (has: {', '.join(tags[-5:]) or 'none'})")
    if target:
        if pkg.dirty():
            raise KoshaError(f"{pkg.path} has local changes: commit or stash them first")
        checkout(pkg, target)
    link = link_bin(pkg)
    run_hook(pkg.post, pkg.path)
    reload_hook(pkg)
    entry = state.get(pkg.name, {})
    entry.update(version=pkg.version(), path=pkg.path, at=int(time.time()),
                 pinned=bool(version) or entry.get("pinned", False))
    state[pkg.name] = entry
    save_state(state)
    log(f"{'adopt' if adopted and not version else 'install'} {pkg.name} {entry['version']}")
    return entry["version"], adopted, link


def update(pkg, to, state):
    old = pkg.version()
    if pkg.dirty():
        raise KoshaError(f"{pkg.path} has local changes: commit or stash them (or `kosha update --force`)")
    git(["fetch", "-q", "--tags", "--force", "origin"], cwd=pkg.path)
    checkout(pkg, to)
    link_bin(pkg)
    run_hook(pkg.post, pkg.path)
    reload_hook(pkg)
    state.setdefault(pkg.name, {}).update(version=pkg.version(), path=pkg.path, at=int(time.time()))
    save_state(state)
    log(f"update {pkg.name} {old} -> {to}")
    return old


def remove(pkg, state):
    if pkg.linked():
        os.remove(pkg.path)
    elif pkg.installed():
        shutil.rmtree(pkg.path)
    t = pkg.bin_target
    if t and os.path.islink(t[0]) and os.readlink(t[0]).startswith(pkg.path):
        os.remove(t[0])
    state.pop(pkg.name, None)
    save_state(state)
    reload_hook(pkg)
    log(f"remove {pkg.name}")


def changelog_between(pkg, old, new):
    """The CHANGELOG sections after old up to new (from the checkout)."""
    try:
        text = open(os.path.join(pkg.path, "CHANGELOG.md")).read()
    except OSError:
        return ""
    out, take = [], False
    for part in re.split(r"(?m)^## ", text)[1:]:
        head = part.split("\n", 1)[0]
        m = re.match(r"\s*(v?[\d.]+)", head)
        if not m:
            continue
        v = m.group(1) if m.group(1).startswith("v") else "v" + m.group(1)
        if vkey(v) <= vkey((old or "").split("-")[0]):
            break
        if vkey(v) <= vkey(new):
            out.append("## " + part.strip())
    return "\n\n".join(out)
