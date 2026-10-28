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


TRACE = None   # set by the CLI in verbose mode: TRACE(text) prints a detail line


def git(args, cwd=None, timeout=120, check=True):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_ASKPASS="true", LC_ALL="C")
    t0 = time.monotonic()
    try:
        r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        raise KoshaError(f"git {args[0]} took longer than {timeout}s (slow or no network?)") from None
    except FileNotFoundError:
        raise KoshaError("git isn't installed") from None
    if TRACE:
        where = f"  ({cwd.replace(HOME, '~')})" if cwd else ""
        TRACE(f"git {' '.join(args)}{where}  →  exit {r.returncode}, {time.monotonic() - t0:.2f}s")
    if check and (r.returncode < 0 or r.returncode == 130):
        raise KoshaError("cancelled")   # stopped by Ctrl-C along with kosha
    if check and r.returncode != 0:
        msg = (r.stderr.strip() or r.stdout.strip() or f"git {args[0]} failed").splitlines()[-1]
        if "Could not resolve host" in msg or "unable to access" in msg:
            msg = "can't reach GitHub (offline?)"
        elif "not found" in msg.lower() and args[0] in ("clone", "ls-remote"):
            msg = "repository not found"
        raise KoshaError(msg.replace("fatal: ", ""))
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


def registry_tables():
    """The raw package tables of the registry load_registry() uses."""
    with open(load_registry()[1], "rb") as f:
        return tomllib.load(f).get("packages", {})


def registry_diff(old, new):
    """What a newer package list changes: packages added and removed, and
    for each package in both, the fields that differ."""
    both = sorted(set(old) & set(new))
    return {"added": sorted(set(new) - set(old)), "removed": sorted(set(old) - set(new)),
            "changed": {n: sorted(k for k in set(old[n]) | set(new[n]) if old[n].get(k) != new[n].get(k))
                        for n in both if old[n] != new[n]}}


def commits_past(version):
    """How far a checkout is past its tag: "v0.2.0-2-gf807d5e" -> 2; a tag -> 0."""
    m = re.match(r".*-(\d+)-g[0-9a-f]+$", version or "")
    return int(m.group(1)) if m else 0


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

    def version(self, cached=True):
        """The release tag checked out, or `<tag>-<n>-g<commit>` when off a tag."""
        if cached and "_version" in self.__dict__:
            return self._version
        v = None
        if self.installed():
            try:
                v = git(["describe", "--tags", "--always"], cwd=self.path, timeout=10)
            except (KoshaError, subprocess.TimeoutExpired):
                v = "?"
        self._version = v
        return v

    def forget(self):
        self.__dict__.pop("_version", None)

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
        tags = [ln.split("refs/tags/")[1] for ln in out.splitlines() if "refs/tags/" in ln]
        return sorted((t for t in tags if TAG.match(t)), key=vkey)

    def latest(self):
        tags = self.remote_tags()
        return tags[-1] if tags else None

    def missing_commands(self):
        return [c for c in self.commands if not shutil.which(c)]


CACHE_TTL = 15 * 60   # seconds a "newest release" answer is reused (list, info, outdated)


def latest_versions(pkgs, fresh=False, on_start=None, on_done=None):
    """{name: latest tag or Exception}: from the cache when it's recent (unless
    fresh), else asked of every remote in parallel."""
    path = os.path.join(CACHE, "latest.json")
    try:
        cache = json.load(open(path))
    except (OSError, ValueError):
        cache = {}
    now = time.time()
    out, ask = {}, []
    for p in pkgs:
        hit = cache.get(p.name)
        if not fresh and hit and hit.get("repo") == p.repo and now - hit.get("at", 0) < CACHE_TTL:
            out[p.name] = hit.get("latest")
            if on_done:
                on_done(p.name, out[p.name], True)
        else:
            ask.append(p)
    if ask:
        def one(p):
            if on_start:
                on_start(p.name)
            return p.latest()
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(24, len(ask))) as ex:
            futs = {ex.submit(one, p): p for p in ask}
            for f in concurrent.futures.as_completed(futs):
                p = futs[f]
                try:
                    out[p.name] = f.result()
                    cache[p.name] = {"latest": out[p.name], "repo": p.repo, "at": now}
                except Exception as e:   # one unreachable repo mustn't stop the rest
                    out[p.name] = e
                if on_done:
                    on_done(p.name, out[p.name], False)
        try:
            os.makedirs(CACHE, exist_ok=True)
            json.dump(cache, open(path + ".tmp", "w"))
            os.replace(path + ".tmp", path)
        except OSError:
            pass
    return out


def is_cached(pkg):
    try:
        hit = json.load(open(os.path.join(CACHE, "latest.json"))).get(pkg.name)
    except (OSError, ValueError):
        return False
    return bool(hit) and hit.get("repo") == pkg.repo and time.time() - hit.get("at", 0) < CACHE_TTL


def forget_latest(name):
    path = os.path.join(CACHE, "latest.json")
    try:
        cache = json.load(open(path))
        cache.pop(name, None)
        json.dump(cache, open(path, "w"))
    except (OSError, ValueError):
        pass


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
    pkg.forget()


def read_versions(pkgs):
    """Reads every package's version from git in parallel (they're then cached)."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
        list(ex.map(lambda p: p.version(), pkgs))


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


def fetch(pkg):
    """The network half of an install: clone, or fetch an existing clone.
    Safe to run for several packages at once. Returns True if adopted."""
    if pkg.installed():
        if pkg.linked():
            raise KoshaError(f"{pkg.name} is a linked development checkout (kosha unlink {pkg.name} first)")
        remote = git(["remote", "get-url", "origin"], cwd=pkg.path, check=False)
        if pkg.repo.split("/")[-1] not in remote:
            raise KoshaError(f"{pkg.path} is a clone of something else ({remote})")
        git(["fetch", "-q", "--tags", "--force", "origin"], cwd=pkg.path)
        return True
    os.makedirs(os.path.dirname(pkg.path), exist_ok=True)
    # blobless: history and tags now, file contents only for what's checked out
    try:
        git(["clone", "-q", "--filter=blob:none", pkg.url, pkg.path], timeout=300)
    except BaseException:
        shutil.rmtree(pkg.path, ignore_errors=True)   # never leave a half-cloned folder behind
        raise
    return False


def release_tags(pkg):
    """The release tags in the local clone, oldest first."""
    return sorted((t for t in git(["tag", "-l"], cwd=pkg.path).splitlines() if TAG.match(t)), key=vkey)


def target_for(pkg, version, adopted):
    """Which tag to check out: the asked-for version, else (for a fresh clone)
    the newest release; None keeps what's checked out."""
    tags = release_tags(pkg)
    if version:
        for cand in (version, "v" + version.lstrip("v"), version.lstrip("v")):
            if cand in tags:
                return cand
        raise KoshaError(f"{pkg.name} has no release {version} (latest: {', '.join(tags[-4:]) or 'none'})")
    return None if adopted else (tags[-1] if tags else None)


def place(pkg, target):
    """Checks out target (if any) and links the command; returns the link."""
    if target:
        if pkg.dirty():
            raise KoshaError(f"{pkg.path.replace(HOME, '~')} has local changes: commit or stash them first")
        checkout(pkg, target)
    return link_bin(pkg)


def finish(pkg, state, pinned=False, how="install", old=None):
    """Post-install command, reload, and the record of it."""
    run_hook(pkg.post, pkg.path)
    reload_hook(pkg)
    pkg.forget()
    entry = state.get(pkg.name, {})
    entry.update(version=pkg.version(), path=pkg.path, at=int(time.time()),
                 pinned=pinned or entry.get("pinned", False))
    state[pkg.name] = entry
    save_state(state)
    log(f"{how} {pkg.name} {(old + ' -> ') if old else ''}{entry['version']}")
    return entry["version"]


def install(pkg, version=None, state=None, adopted=None):
    """Clones (or adopts an existing clone) and checks out version (default:
    the newest release; a repo without releases stays on its default branch).
    Pass adopted (from fetch()) when the clone/fetch already happened."""
    state = load_state() if state is None else state
    if adopted is None:
        adopted = fetch(pkg)
    link = place(pkg, target_for(pkg, version, adopted))
    v = finish(pkg, state, pinned=bool(version), how="adopt" if adopted and not version else "install")
    return v, adopted, link


def update(pkg, to, state, fetched=False):
    old = pkg.version()
    if pkg.dirty():
        raise KoshaError(f"{pkg.path} has local changes: commit or stash them (or `kosha update --force`)")
    if not fetched:
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
    pkg.forget()
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
    out = []
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


class Lock:
    """One kosha changing things at a time (install, update, remove...)."""

    def __enter__(self):
        import fcntl
        os.makedirs(STATE, exist_ok=True)
        self.f = open(os.path.join(STATE, "lock"), "w")
        try:
            fcntl.flock(self.f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise KoshaError("another kosha is already installing or updating: wait for it to finish") from None
        return self

    def __exit__(self, *exc):
        import fcntl
        fcntl.flock(self.f, fcntl.LOCK_UN)
        self.f.close()
        return False
