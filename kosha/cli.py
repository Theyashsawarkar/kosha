"""kosha's commands, their help, and their output."""
import concurrent.futures
import difflib
import json
import os
import shutil
import subprocess
import sys
import time

from . import VERSION, core, ui
from .core import KoshaError
from .ui import c

# ===================================================================== help
# Every command's help lives here: `kosha help`, `kosha <cmd> --help` and the
# shell completions are generated from it.
COMMANDS = {
    "list": dict(group="Find", aliases=["ls"], args="[--installed] [--json] [--refresh]",
                 summary="Every package: your version, the newest release, its status",
                 options=[("-i, --installed", "only what's installed"), ("--json", "machine-readable output"),
                          ("-r, --refresh", "ask GitHub now instead of using the last 15 minutes' answer")],
                 examples=["kosha list", "kosha ls -i", "kosha list --json | jq '.[] | select(.latest != .installed)'"]),
    "search": dict(group="Find", aliases=["find"], args="<words>",
                   summary="Find packages by name, kind or description",
                   examples=["kosha search music", "kosha search vyom tool"]),
    "info": dict(group="Find", aliases=["show"], args="<package>",
                 summary="Everything about one package: versions, location, what it needs",
                 examples=["kosha info nada"]),
    "install": dict(group="Install", aliases=["add", "i"], args="<package>[@version] ... [-y]",
                    summary="Install the newest release (or a pinned one), dependencies first",
                    description="Downloads every package in parallel, then installs them in dependency order. "
                                "A package already on disk is adopted as it is. `@version` installs that release "
                                "and pins it, so `kosha update` leaves it alone.",
                    options=[("-y, --yes", "don't ask before installing")],
                    examples=["kosha install nada", "kosha install dvara ganit smriti", "kosha install ganit@0.1.2"]),
    "update": dict(group="Install", aliases=["upgrade", "up"], args="[<package> ...] [-y] [--force]",
                   summary="Update to the newest releases (everything, or the packages named)",
                   description="Checks every installed package at once, shows what will change, and after you "
                               "confirm, downloads in parallel and prints each package's changelog since your "
                               "version. Pinned packages are skipped unless named.",
                   options=[("-y, --yes", "don't ask before updating"),
                            ("--force", "update even with local changes (they're stashed, not lost)")],
                   examples=["kosha update", "kosha up nada", "kosha update -y"]),
    "remove": dict(group="Install", aliases=["rm", "uninstall"], args="<package> ... [-y] [--force]",
                   summary="Uninstall packages (refused while another needs them)",
                   options=[("-y, --yes", "don't ask"), ("--force", "remove even with local changes")],
                   examples=["kosha remove patra", "kosha rm ganit vyom"]),
    "outdated": dict(group="Maintain", aliases=[], args="[--json]",
                     summary="What has a newer release",
                     options=[("--json", "machine-readable output (for scripts and status bars)")],
                     examples=["kosha outdated", "kosha outdated --json"]),
    "pin": dict(group="Maintain", aliases=[], args="<package> ...",
                summary="Keep packages on their current version",
                examples=["kosha pin nada"]),
    "unpin": dict(group="Maintain", aliases=[], args="<package> ...",
                  summary="Let pinned packages update again",
                  examples=["kosha unpin nada"]),
    "changelog": dict(group="Maintain", aliases=["log"], args="<package> [<since version>]",
                      summary="What changed in a package (since a version)",
                      examples=["kosha changelog nada", "kosha log vyom v0.2.5"]),
    "doctor": dict(group="Maintain", aliases=["check"], args="",
                   summary="Check every installed package: programs, links, local changes",
                   examples=["kosha doctor"]),
    "refresh": dict(group="Maintain", aliases=[], args="",
                    summary="Download the newest package list",
                    examples=["kosha refresh"]),
    "self-update": dict(group="Maintain", aliases=[], args="[-y]",
                        summary="Update kosha itself",
                        examples=["kosha self-update"]),
    "link": dict(group="Develop", aliases=[], args="<package> <path>",
                 summary="Run your own checkout instead of the release",
                 description="Moves the release aside and links your checkout in its place, so the desktop "
                             "runs your code. `kosha unlink` puts the release back.",
                 examples=["kosha link nada ~/code/nada"]),
    "unlink": dict(group="Develop", aliases=[], args="<package>",
                   summary="Go back to the release after `kosha link`",
                   examples=["kosha unlink nada"]),
    "help": dict(group="Help", aliases=[], args="[<command>]",
                 summary="This overview, or one command's details",
                 examples=["kosha help", "kosha help install", "kosha install --help"]),
    "completions": dict(group="Help", aliases=[], args="zsh|bash",
                        summary="Print shell completions (tab-complete commands and packages)",
                        examples=["kosha completions zsh > ~/.zfunc/_kosha", "eval \"$(kosha completions bash)\""]),
}
GROUPS = ["Find", "Install", "Maintain", "Develop", "Help"]
ALIASES = {a: name for name, d in COMMANDS.items() for a in d["aliases"]}
GLOBAL = [("-y, --yes", "answer yes to every question"), ("-q, --quiet", "only errors and the result"),
          ("--no-color", "plain output (also: NO_COLOR=1)"), ("-h, --help", "help for kosha or a command"),
          ("-V, --version", "the version")]


def logo():
    return c("❯", "mauve", bold=True) + c(" kosha", "text", bold=True) + c(" कोश", "mauve") + c(f"  v{VERSION}", "dim")


def help_all():
    ui.out(logo() + c("   the package manager for Vayu's tools", "sub"))
    ui.out()
    ui.out(f"{c('Usage', 'text', bold=True)}  kosha {c('<command>', 'mauve')} {c('[options]', 'dim')}")
    nw = max(len(n) for n in COMMANDS) + 2
    for g in GROUPS:
        ui.out()
        ui.out(c(g.upper(), "peach", bold=True))
        for name, d in COMMANDS.items():
            if d["group"] != g:
                continue
            al = c(f" ({', '.join(d['aliases'])})", "dim") if d["aliases"] else ""
            ui.out(f"  {c(ui.pad(name, nw), 'mauve')}{d['summary']}{al}")
    ui.out()
    ui.out(c("OPTIONS", "peach", bold=True))
    for o, d in GLOBAL:
        ui.out(f"  {c(ui.pad(o, 16), 'sky')}{d}")
    ui.out()
    ui.out(c("EXAMPLES", "peach", bold=True))
    for ex, what in [("kosha list", "what's installed and what's new"), ("kosha install nada", "install the music player"),
                     ("kosha update", "update everything"), ("kosha help update", "details of one command")]:
        ui.out(f"  {c('$', 'faint')} {ui.pad(ex, 22)} {c(what, 'dim')}")
    ui.out()
    ui.out(c("Docs: https://theyashsawarkar.github.io/kosha/   ·   kosha <command> --help for any command", "dim"))


def help_cmd(name):
    d = COMMANDS[name]
    ui.out(logo())
    ui.out()
    ui.out(f"{c('kosha ' + name, 'mauve', bold=True)} {c(d['args'], 'sky')}")
    ui.out(f"  {d['summary']}")
    if d.get("description"):
        ui.out()
        import textwrap
        for line in textwrap.wrap(d["description"], min(ui.cols(), 90) - 2):
            ui.out(f"  {c(line, 'sub')}")
    if d["aliases"]:
        ui.out()
        ui.out(f"{c('ALIASES', 'peach', bold=True)}  {', '.join(d['aliases'])}")
    if d.get("options"):
        ui.out()
        ui.out(c("OPTIONS", "peach", bold=True))
        for o, w in d["options"]:
            ui.out(f"  {c(ui.pad(o, 18), 'sky')}{w}")
    ui.out()
    ui.out(c("EXAMPLES", "peach", bold=True))
    for ex in d["examples"]:
        ui.out(f"  {c('$', 'faint')} {ex}")


def suggest(word, choices):
    m = difflib.get_close_matches(word, choices, n=1, cutoff=0.6)
    return m[0] if m else None


# ===================================================================== helpers
class Ctx:
    def __init__(self, args):
        self.yes = bool({"-y", "--yes"} & set(args))
        self.quiet = bool({"-q", "--quiet"} & set(args))
        self.json = "--json" in args
        self.force = "--force" in args
        self.fresh = bool({"-r", "--refresh"} & set(args))
        self.flags = set(a for a in args if a.startswith("-"))
        self.args = [a for a in args if not a.startswith("-")]
        self.t0 = time.monotonic()


def registry():
    return core.load_registry()[0]


def get(reg, name):
    if name not in reg:
        s = suggest(name, list(reg))
        raise KoshaError(f"no package called {c(name, 'bold' and 'text', bold=True)}" + (f" (did you mean {c(s, 'mauve')}?)" if s else "")
                         + c("  kosha search lists them", "dim"))
    return reg[name]


def vstr(v, color="text"):
    return c(v, color) if v else c("—", "faint")


def status_of(p, latest, state):
    cur = p.version()
    if not cur:
        return c("not installed", "dim")
    if p.linked():
        return c("◆ linked", "sky")
    new = latest.get(p.name)
    pinned = state.get(p.name, {}).get("pinned")
    newer = isinstance(new, str) and core.vkey(new) > core.vkey(p.exact_tag() or (cur or "").split("-")[0])
    if pinned:
        return c("● pinned", "peach") + (c(f" ({new} out)", "dim") if newer else "")
    if newer:
        return c("▲ update", "yellow", bold=True)
    if isinstance(new, Exception):
        return c("? offline", "dim")
    return c("● up to date", "green")


def kind_label(k):
    return {"vyom": c("runtime", "lavender"), "vyom-tool": c("vyom tool", "blue"), "app": c("app", "pink"),
            "tmux-plugin": c("tmux", "teal")}.get(k, k)


def done(ctx, msg):
    if not ctx.quiet:
        ui.out(f"{c('━━', 'mauve')} {msg} {c('in ' + ui.elapsed(ctx.t0), 'dim')}")


# ===================================================================== find
def cmd_list(ctx):
    reg = registry()
    only = bool({"-i", "--installed"} & ctx.flags)
    pkgs = [p for p in reg.values() if p.installed() or not only]
    with ui.Spinner("checking releases…"):
        with concurrent.futures.ThreadPoolExecutor(2) as ex:
            v = ex.submit(core.read_versions, pkgs)
            latest = core.latest_versions(pkgs, ctx.fresh)
            v.result()
    state = core.load_state()
    if ctx.json:
        ui.out(json.dumps([{"name": p.name, "kind": p.kind, "installed": p.version(),
                            "latest": latest.get(p.name) if not isinstance(latest.get(p.name), Exception) else None,
                            "pinned": state.get(p.name, {}).get("pinned", False), "linked": p.linked(),
                            "description": p.description} for p in pkgs], indent=2))
        return 0
    order = {"vyom": 1, "vyom-tool": 2, "app": 0, "tmux-plugin": 3}
    pkgs.sort(key=lambda p: (not p.installed(), order.get(p.kind, 9), p.name))
    rows = []
    for p in pkgs:
        new = latest.get(p.name)
        newer = isinstance(new, str) and p.installed() and core.vkey(new) > core.vkey(p.exact_tag() or "")
        rows.append([c(p.name, "text", bold=True) if p.installed() else c(p.name, "dim"),
                     vstr(p.version()), c(new, "yellow" if newer else "sub") if isinstance(new, str) else c("?", "dim"),
                     kind_label(p.kind), status_of(p, latest, state)])
    n_inst = sum(1 for p in pkgs if p.installed())
    n_up = sum(1 for p in pkgs if p.installed() and not p.linked() and isinstance(latest.get(p.name), str)
               and core.vkey(latest[p.name]) > core.vkey(p.exact_tag() or ""))
    ui.table(rows, ["Package", "Installed", "Latest", "Kind", "Status"], title="Packages")
    ui.summary([("Installed", n_inst, "green"), ("Updates", n_up, "yellow"),
                ("Available", len(pkgs) - n_inst, "sub")])
    if n_up:
        ui.note("kosha update installs them")
    return 0


def cmd_search(ctx):
    if not ctx.args:
        raise KoshaError("what to search for? kosha search <words>")
    reg = registry()
    words = [w.lower() for w in ctx.args]
    hits = [p for p in reg.values() if all(w in f"{p.name} {p.description} {p.kind}".lower() for w in words)]
    if not hits:
        ui.warn(f"nothing matches {' '.join(ctx.args)}")
        return 1
    ui.header("Search", f"{len(hits)} found")
    for p in sorted(hits, key=lambda p: p.name):
        mark = c(f"  installed {p.version()}", "green") if p.installed() else ""
        ui.out(f"{c(p.name, 'mauve', bold=True)}  {kind_label(p.kind)}{mark}")
        ui.out(f"  {c(p.description, 'sub')}")
    return 0


def cmd_info(ctx):
    if not ctx.args:
        raise KoshaError("which package? kosha info <package>")
    reg = registry()
    p = get(reg, ctx.args[0])
    state = core.load_state().get(p.name, {})
    with ui.Spinner("checking releases…"):
        latest = core.latest_versions([p], ctx.fresh).get(p.name)
    rows = [("About", p.description), ("Kind", kind_label(p.kind)),
            ("Installed", (c(p.version(), "green") if p.installed() else c("no", "dim"))
             + (c("  pinned", "peach") if state.get("pinned") else "") + (c("  linked", "sky") if p.linked() else "")),
            ("Latest", latest if isinstance(latest, str) else c("unknown (offline?)", "dim")),
            ("Location", p.path.replace(core.HOME, "~")), ("Repository", p.url),
            ("Website", f"https://theyashsawarkar.github.io/{p.repo.split('/')[-1]}/")]
    if p.requires:
        rows.append(("Requires", ", ".join(c(r, "green" if reg.get(r) and reg[r].installed() else "red") for r in p.requires)))
    if p.commands:
        miss = p.missing_commands()
        rows.append(("Needs", ", ".join(c(x, "red") + c(" (missing)", "dim") if x in miss else x for x in p.commands)))
    deps = core.dependents(p.name, reg)
    if deps:
        rows.append(("Needed by", ", ".join(deps)))
    ui.header(p.name, p.kind)
    w = max(len(k) for k, _ in rows)
    for k, v in rows:
        ui.out(f"  {c(ui.pad(k, w), 'dim')}  {v}")
    return 0


# ===================================================================== install
def plan_table(rows, title):
    ui.table(rows, ["Package", "Version", "", "Kind"], title=title)


def run_parallel(items, work, label):
    """items: [(name, arg)]; work(arg, report) runs on a thread per item.
    Returns {name: result or Exception}."""
    results = {}
    with ui.Progress([n for n, _ in items], label) as prog:
        def one(name, arg):
            prog.set(name, "run", "downloading")
            try:
                r = work(arg)
                results[name] = r
                prog.set(name, "ok", c("downloaded", "dim"))
            except Exception as e:
                results[name] = e
                prog.set(name, "err", str(e)[:80])
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(12, len(items) or 1)) as ex:
            list(ex.map(lambda it: one(*it), items))
        return results, prog


def cmd_install(ctx):
    if not ctx.args:
        raise KoshaError("which packages? kosha install <package>[@version] ...")
    reg = registry()
    wanted, versions = [], {}
    for a in ctx.args:
        name, _, ver = a.partition("@")
        get(reg, name)
        wanted.append(name)
        if ver:
            versions[name] = ver
    order = core.resolve(wanted, reg)
    todo = [n for n in order if not reg[n].installed() or n in versions or n in wanted]
    fresh = [n for n in todo if not reg[n].installed()]
    with ui.Spinner("checking releases…"):
        latest = core.latest_versions([reg[n] for n in todo], ctx.fresh)
    rows = []
    for n in todo:
        p = reg[n]
        target = versions.get(n) or (latest.get(n) if isinstance(latest.get(n), str) else "main")
        target = target if target.startswith("v") or target == "main" else "v" + target
        if p.installed() and n not in versions:
            rows.append([c(n, "text", bold=True), vstr(p.version(), "sub"), c("adopt", "sky"), kind_label(p.kind)])
        else:
            rows.append([c(n, "text", bold=True), c(target, "green"), c("pinned", "peach") if n in versions else
                         (c("dependency", "dim") if n not in wanted else ""), kind_label(p.kind)])
    if not ctx.quiet:
        plan_table(rows, "Installing")
        ui.summary([("Install", len(fresh), "green"), ("Adopt", len([n for n in todo if reg[n].installed() and n not in versions]), "sky"),
                    ("Pin", len(versions), "peach")])
    if not ui.confirm(assume=True if ctx.yes else None):
        ui.warn("nothing changed")
        return 1
    results, _ = run_parallel([(n, reg[n]) for n in todo], core.fetch, "Downloading") if todo else ({}, None)
    state = core.load_state()
    installed, failed = [], []
    for n in todo:   # dependency order: finish (checkout, link, hooks) one by one
        r = results.get(n)
        if isinstance(r, Exception):
            failed.append(n)
            continue
        try:
            v, adopted, link = core.install(reg[n], versions.get(n), state, adopted=r)
            installed.append((n, v, link))
        except KoshaError as e:
            ui.err(f"{n}: {e}")
            failed.append(n)
    if not ctx.quiet:
        for n, v, link in installed:
            ui.ok(f"{c(n, 'text', bold=True)} {c(v, 'green')}" + (c(f"  → {link.replace(core.HOME, '~')}", "dim") if link else ""))
    offer_system(ctx, [reg[n] for n, _, _ in installed])
    done(ctx, f"{len(installed)} installed" + (c(f", {len(failed)} failed", "red") if failed else ""))
    return 1 if failed else 0


def offer_system(ctx, pkgs):
    missing = {p.name: p.missing_commands() for p in pkgs if p.missing_commands()}
    if not missing:
        return
    arch = sorted({a for p in pkgs if p.name in missing for a in p.arch})
    for n, cmds in missing.items():
        ui.warn(f"{c(n, 'text', bold=True)} needs {c(', '.join(cmds), 'peach')}, which isn't installed")
    if not arch or not shutil.which("pacman"):
        return
    asker = shutil.which("anumati")
    if asker and sys.stdin.isatty() and ui.confirm(f"Install {', '.join(arch)} (through anumati)?", assume=True if ctx.yes else None):
        req = {"requester": "kosha", "reason": f"Programs the tools you installed need: {', '.join(missing)}",
               "commands": [{"cmd": f"pacman -S --needed --noconfirm {' '.join(arch)}",
                             "why": f"Install {', '.join(arch)} (needed by {', '.join(missing)})"}]}
        r = subprocess.run([asker], input=json.dumps(req), capture_output=True, text=True)
        ui.ok("installed") if r.returncode == 0 else ui.warn(f"not installed ({json.loads(r.stdout or '{}').get('status', 'failed')})")
    else:
        ui.note(f"to install them: sudo pacman -S --needed {' '.join(arch)}")


def cmd_update(ctx):
    reg = registry()
    names = ctx.args
    for n in names:
        get(reg, n)
    state = core.load_state()
    pkgs = [reg[n] for n in names] if names else [p for p in reg.values() if p.installed()]
    for p in pkgs:
        if not p.installed():
            raise KoshaError(f"{p.name} isn't installed (kosha install {p.name})")
    linked = [p for p in pkgs if p.linked()]
    pkgs = [p for p in pkgs if not p.linked()]
    core.read_versions(pkgs)
    with ui.Spinner(f"checking {len(pkgs)} packages for updates…"):
        latest = core.latest_versions(pkgs, fresh=True)
    todo, pinned, offline = [], [], []
    for p in pkgs:
        new = latest.get(p.name)
        if isinstance(new, Exception):
            offline.append(p.name)
            continue
        if not new or core.vkey(new) <= core.vkey(p.exact_tag() or (p.version() or "").split("-")[0]):
            continue
        if state.get(p.name, {}).get("pinned") and p.name not in names:
            pinned.append((p, new))
            continue
        todo.append((p, new))
    for p in linked:
        ui.note(f"{p.name}: linked development checkout, skipped")
    for n in offline:
        ui.warn(f"{n}: couldn't check (offline?)")
    if not todo:
        if pinned and not ctx.quiet:
            ui.note("pinned: " + ", ".join(f"{p.name} ({p.version()}, {n} out)" for p, n in pinned))
        done(ctx, c("everything is up to date", "green"))
        return 0
    if not ctx.quiet:
        ui.table([[c(p.name, "text", bold=True), c(p.version(), "sub"), c("→", "dim"), c(n, "green", bold=True), kind_label(p.kind)]
                  for p, n in todo], ["Package", "Installed", "", "New", "Kind"], title="Upgrading")
        if pinned:
            ui.note("pinned, not updated: " + ", ".join(f"{p.name} ({n} out)" for p, n in pinned))
        ui.summary([("Upgrade", len(todo), "yellow"), ("Pinned", len(pinned), "peach")])
    if not ui.confirm(assume=True if ctx.yes else None):
        ui.warn("nothing changed")
        return 1
    dirty = [p for p, _ in todo if p.dirty()]
    for p in dirty:
        if not ctx.force:
            ui.err(f"{p.name}: {p.path.replace(core.HOME, '~')} has local changes (commit or stash them, or --force)")
    todo = [(p, n) for p, n in todo if p not in dirty or ctx.force]
    for p in dirty:
        if ctx.force:
            core.git(["stash", "-q"], cwd=p.path)
            ui.warn(f"{p.name}: local changes stashed (git -C {p.path.replace(core.HOME, '~')} stash pop brings them back)")
    fetched, _ = run_parallel([(p.name, p) for p, _ in todo],
                              lambda p: core.git(["fetch", "-q", "--tags", "--force", "origin"], cwd=p.path), "Downloading")
    ok, failed, logs = [], [], []
    for p, new in todo:
        if isinstance(fetched.get(p.name), Exception):
            failed.append(p.name)
            continue
        try:
            old = core.update(p, new, state, fetched=True)
            ok.append((p, old, new))
            logs.append((p, core.changelog_between(p, old, new)))
        except KoshaError as e:
            ui.err(f"{p.name}: {e}")
            failed.append(p.name)
    if not ctx.quiet:
        for p, old, new in ok:
            ui.ok(f"{c(p.name, 'text', bold=True)} {c(old, 'dim')} {c('→', 'dim')} {c(new, 'green', bold=True)}")
        for p, text in logs:
            if not text:
                continue
            ui.header(f"What's new in {p.name}")
            shown = 0
            for line in text.splitlines():
                if shown >= 16:
                    ui.note(f"… kosha changelog {p.name} for the rest")
                    break
                if line.startswith("## "):
                    ui.out(c(line[3:], "mauve", bold=True))
                elif line.strip():
                    ui.out("  " + c(line, "sub"))
                shown += 1
    done(ctx, f"{len(ok)} upgraded" + (c(f", {len(failed)} failed", "red") if failed else ""))
    return 1 if failed else 0


def cmd_remove(ctx):
    if not ctx.args:
        raise KoshaError("which packages? kosha remove <package> ...")
    reg = registry()
    pkgs = [get(reg, n) for n in ctx.args]
    for p in pkgs:
        if not p.installed():
            raise KoshaError(f"{p.name} isn't installed")
        deps = [d for d in core.dependents(p.name, reg) if d not in ctx.args]
        if deps:
            raise KoshaError(f"{p.name} is needed by {', '.join(deps)}: remove those too, or keep it")
        if p.dirty() and not ctx.force:
            raise KoshaError(f"{p.path.replace(core.HOME, '~')} has local changes (--force removes it anyway)")
    if not ctx.quiet:
        ui.table([[c(p.name, "text", bold=True), c(p.version(), "sub"), p.path.replace(core.HOME, "~")] for p in pkgs],
                 ["Package", "Version", "Folder (deleted)"], title="Removing")
        ui.summary([("Remove", len(pkgs), "red")])
    if not ui.confirm(default=True, assume=True if ctx.yes else None):
        ui.warn("nothing changed")
        return 1
    state = core.load_state()
    for p in pkgs:
        core.remove(p, state)
        core.forget_latest(p.name)
        if not ctx.quiet:
            ui.ok(f"removed {c(p.name, 'text', bold=True)}")
    done(ctx, f"{len(pkgs)} removed")
    return 0


# ===================================================================== maintain
def cmd_outdated(ctx):
    reg = registry()
    state = core.load_state()
    pkgs = [p for p in reg.values() if p.installed() and not p.linked()]
    core.read_versions(pkgs)
    if ctx.json:
        latest = core.latest_versions(pkgs, ctx.fresh)
    else:
        with ui.Spinner("checking releases…"):
            latest = core.latest_versions(pkgs, ctx.fresh)
    out = []
    for p in pkgs:
        new = latest.get(p.name)
        if isinstance(new, str) and core.vkey(new) > core.vkey(p.exact_tag() or (p.version() or "").split("-")[0]):
            out.append({"name": p.name, "installed": p.version(), "latest": new,
                        "pinned": state.get(p.name, {}).get("pinned", False)})
    if ctx.json:
        ui.out(json.dumps(out))
        return 0
    if not out:
        ui.ok(c("everything is up to date", "green"))
        return 0
    ui.table([[c(o["name"], "text", bold=True), c(o["installed"], "sub"), c("→", "dim"), c(o["latest"], "green", bold=True),
               c("pinned", "peach") if o["pinned"] else ""] for o in out], ["Package", "Installed", "", "Latest", ""], title="Outdated")
    ui.note("kosha update installs them")
    return 0


def cmd_pin(ctx, on=True):
    if not ctx.args:
        raise KoshaError(f"which package? kosha {'pin' if on else 'unpin'} <package>")
    reg = registry()
    state = core.load_state()
    for n in ctx.args:
        p = get(reg, n)
        if not p.installed():
            raise KoshaError(f"{n} isn't installed")
        state.setdefault(n, {"path": p.path})["pinned"] = on
        state[n]["version"] = p.version()
        ui.ok(f"{c(n, 'text', bold=True)} " + (f"pinned at {c(p.version(), 'peach')}" if on else "will update again"))
    core.save_state(state)
    return 0


def cmd_changelog(ctx):
    if not ctx.args:
        raise KoshaError("which package? kosha changelog <package> [<since>]")
    reg = registry()
    p = get(reg, ctx.args[0])
    if not p.installed():
        raise KoshaError(f"{p.name} isn't installed: https://theyashsawarkar.github.io/{p.repo.split('/')[-1]}/changelog.html")
    text = open(os.path.join(p.path, "CHANGELOG.md")).read()
    if len(ctx.args) > 1:
        text = core.changelog_between(p, ctx.args[1], "v999.0.0") or f"nothing since {ctx.args[1]}"
    lines = []
    for line in text.splitlines():
        if line.startswith("# "):
            continue
        lines.append(c(line[3:], "mauve", bold=True) if line.startswith("## ") else c(line, "sub"))
    body = "\n".join(lines).strip()
    if ui.TTY and len(lines) > ui.shutil.get_terminal_size().lines - 2:
        subprocess.run(os.environ.get("PAGER", "less -R"), shell=True, input=body, text=True)
    else:
        ui.header(f"{p.name} changelog")
        ui.out(body)
    return 0


def cmd_doctor(ctx):
    reg = registry()
    ui.header("Doctor")
    core.read_versions([p for p in reg.values() if p.installed()])
    problems = 0
    if not shutil.which("git"):
        ui.err("git isn't installed")
        return 1
    if core.BIN not in os.environ.get("PATH", "").split(":"):
        ui.warn(f"{core.BIN.replace(core.HOME, '~')} isn't on your PATH: installed commands won't be found")
        problems += 1
    for p in sorted(reg.values(), key=lambda p: p.name):
        if not p.installed():
            continue
        issues = []
        missing_deps = [d for d in p.requires if d not in reg or not reg[d].installed()]
        if missing_deps:
            issues.append(f"requires {', '.join(missing_deps)}  {c('kosha install ' + ' '.join(missing_deps), 'dim')}")
        miss = p.missing_commands()
        if miss:
            issues.append(f"needs {c(', '.join(miss), 'peach')} on PATH")
        t = p.bin_target
        if t and os.path.exists(t[1]) and not (os.path.islink(t[0]) and os.path.realpath(t[0]) == os.path.realpath(t[1])):
            issues.append(f"{t[0].replace(core.HOME, '~')} doesn't point to it  {c('kosha install ' + p.name, 'dim')}")
        if p.dirty():
            issues.append("has local changes (updates are refused until they're committed or stashed)")
        if not p.linked() and not p.exact_tag():
            issues.append(f"not on a release ({p.version()})  {c('kosha update ' + p.name, 'dim')}")
        if issues:
            problems += 1
            ui.warn(c(p.name, "text", bold=True))
            for i in issues:
                ui.out(f"    {c('└', 'faint')} {i}")
        elif not ctx.quiet:
            ui.ok(f"{p.name} {c(p.version(), 'dim')}" + (c("  linked", "sky") if p.linked() else ""))
    ui.out()
    if problems:
        ui.warn(f"{problems} package{'s' if problems > 1 else ''} need attention")
    else:
        ui.ok(c("no problems", "green"))
    return 1 if problems else 0


def cmd_refresh(ctx):
    with ui.Spinner("downloading the package list…"):
        core.refresh_registry()
    ui.ok(f"package list updated: {len(registry())} packages")
    return 0


def cmd_link(ctx):
    if len(ctx.args) != 2:
        raise KoshaError("kosha link <package> <path to your checkout>")
    reg = registry()
    p = get(reg, ctx.args[0])
    src = os.path.abspath(os.path.expanduser(ctx.args[1]))
    if not os.path.isdir(os.path.join(src, ".git")):
        raise KoshaError(f"{src} isn't a git checkout")
    state = core.load_state()
    if p.installed() and not p.linked():
        backup = p.path + ".kosha-release"
        if os.path.exists(backup):
            raise KoshaError(f"{backup} is in the way")
        os.rename(p.path, backup)
        state.setdefault(p.name, {})["release_backup"] = backup
    elif p.linked():
        os.remove(p.path)
    os.makedirs(os.path.dirname(p.path), exist_ok=True)
    os.symlink(src, p.path)
    core.link_bin(p)
    core.reload_hook(p)
    state.setdefault(p.name, {}).update(path=p.path, linked=src)
    core.save_state(state)
    core.log(f"link {p.name} {src}")
    ui.ok(f"{c(p.name, 'text', bold=True)} now runs from {c(src.replace(core.HOME, '~'), 'sky')}  {c('kosha unlink ' + p.name + ' goes back', 'dim')}")
    return 0


def cmd_unlink(ctx):
    if not ctx.args:
        raise KoshaError("which package? kosha unlink <package>")
    reg = registry()
    p = get(reg, ctx.args[0])
    if not p.linked():
        raise KoshaError(f"{p.name} isn't linked")
    os.remove(p.path)
    state = core.load_state()
    backup = state.get(p.name, {}).pop("release_backup", None)
    state.get(p.name, {}).pop("linked", None)
    core.save_state(state)
    if backup and os.path.isdir(backup):
        os.rename(backup, p.path)
        core.link_bin(p)
        core.reload_hook(p)
    else:
        core.install(p, None, state)
    ui.ok(f"{c(p.name, 'text', bold=True)} back on {c(p.version(), 'green')}")
    return 0


def cmd_completions(ctx):
    shell = ctx.args[0] if ctx.args else os.path.basename(os.environ.get("SHELL", "zsh"))
    cmds = " ".join(list(COMMANDS) + list(ALIASES))
    pkg_cmds = "install add i update upgrade up remove rm uninstall info show pin unpin changelog log link unlink"
    if shell == "zsh":
        ui.out(f"""#compdef kosha
# kosha's zsh completions: `kosha completions zsh > ~/.zfunc/_kosha` (with ~/.zfunc in fpath)
_kosha() {{
  local -a cmds pkgs
  cmds=({cmds})
  if (( CURRENT == 2 )); then
    _describe 'command' cmds
  else
    case ${{words[2]}} in
      {pkg_cmds.replace(' ', '|')}) pkgs=(${{(f)"$(kosha list --json 2>/dev/null | python3 -c 'import json,sys; [print(p["name"]) for p in json.load(sys.stdin)]')"}}); _describe 'package' pkgs ;;
      help) _describe 'command' cmds ;;
      completions) _values 'shell' zsh bash ;;
    esac
  fi
}}
compdef _kosha kosha""")
    elif shell == "bash":
        ui.out(f"""# kosha's bash completions: eval "$(kosha completions bash)"
_kosha() {{
  local cur=${{COMP_WORDS[COMP_CWORD]}}
  if [ "$COMP_CWORD" -eq 1 ]; then COMPREPLY=($(compgen -W "{cmds}" -- "$cur")); return; fi
  case ${{COMP_WORDS[1]}} in
    {pkg_cmds.replace(' ', '|')}) COMPREPLY=($(compgen -W "$(kosha list --json 2>/dev/null | python3 -c 'import json,sys; [print(p["name"]) for p in json.load(sys.stdin)]')" -- "$cur")) ;;
    help) COMPREPLY=($(compgen -W "{cmds}" -- "$cur")) ;;
  esac
}}
complete -F _kosha kosha""")
    else:
        raise KoshaError("kosha completions zsh|bash")
    return 0


HANDLERS = {"list": cmd_list, "search": cmd_search, "info": cmd_info, "install": cmd_install, "update": cmd_update,
            "remove": cmd_remove, "outdated": cmd_outdated, "pin": lambda x: cmd_pin(x, True),
            "unpin": lambda x: cmd_pin(x, False), "changelog": cmd_changelog, "doctor": cmd_doctor,
            "refresh": cmd_refresh, "link": cmd_link, "unlink": cmd_unlink, "completions": cmd_completions}


def main(argv):
    if "--no-color" in argv:
        ui.set_color(False)
        argv = [a for a in argv if a != "--no-color"]
    if not argv:
        help_all()
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd in ("-h", "--help"):
        help_all()
        return 0
    if cmd in ("-V", "--version", "version"):
        ui.out(f"kosha {VERSION}")
        return 0
    cmd = ALIASES.get(cmd, cmd)
    if cmd == "help":
        if rest:
            name = ALIASES.get(rest[0], rest[0])
            if name not in COMMANDS:
                s = suggest(name, list(COMMANDS) + list(ALIASES))
                ui.err(f"no command {rest[0]}" + (f" (did you mean {c(s, 'mauve')}?)" if s else ""))
                return 2
            help_cmd(name)
        else:
            help_all()
        return 0
    if cmd not in COMMANDS:
        s = suggest(cmd, list(COMMANDS) + list(ALIASES))
        ui.err(f"no command {c(cmd, 'text', bold=True)}" + (f": did you mean {c('kosha ' + s, 'mauve', bold=True)}?" if s else "")
               + c("   kosha help lists them", "dim"))
        return 2
    if {"-h", "--help"} & set(rest):
        help_cmd(cmd)
        return 0
    ctx = Ctx(rest)
    try:
        if cmd == "self-update":
            ctx.args = ["kosha"]
            return cmd_update(ctx) or 0
        return HANDLERS[cmd](ctx) or 0
    except KoshaError as e:
        ui.err(str(e))
        return 1
    except KeyboardInterrupt:
        ui.out()
        ui.warn("interrupted")
        return 130
