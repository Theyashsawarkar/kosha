"""kosha's terminal interface: colours (Catppuccin Mocha), boxed tables,
a live multi-line progress display, and the transaction summary. Falls
back to plain text when stdout isn't a terminal or NO_COLOR is set."""
import os
import shutil
import sys
import threading
import time
import unicodedata

TTY = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None and os.environ.get("TERM") != "dumb"
_COLORS = {
    "text": (205, 214, 244), "sub": (166, 173, 200), "dim": (127, 132, 156), "faint": (88, 91, 112),
    "mauve": (203, 166, 247), "pink": (245, 194, 231), "green": (166, 227, 161), "yellow": (249, 226, 175),
    "peach": (250, 179, 135), "red": (243, 139, 168), "sky": (137, 220, 235), "blue": (137, 180, 250),
    "teal": (148, 226, 213), "lavender": (180, 190, 254),
}


def set_color(on):
    global TTY
    TTY = on


def c(text, color=None, bold=False, dim=False):
    if not TTY:
        return str(text)
    codes = []
    if bold:
        codes.append("1")
    if dim:
        codes.append("2")
    if color:
        r, g, b = _COLORS[color]
        codes.append(f"38;2;{r};{g};{b}")
    return f"\033[{';'.join(codes)}m{text}\033[0m" if codes else str(text)


def width(text):
    """Display width without ANSI codes (wide characters count 2)."""
    out, i, s = 0, 0, str(text)
    while i < len(s):
        if s[i] == "\033":
            j = s.find("m", i)
            i = j + 1 if j != -1 else len(s)
            continue
        out += 2 if unicodedata.east_asian_width(s[i]) in "WF" else (0 if unicodedata.combining(s[i]) else 1)
        i += 1
    return out


def pad(text, w, right=False):
    gap = max(0, w - width(text))
    return (" " * gap + str(text)) if right else (str(text) + " " * gap)


def cols():
    return shutil.get_terminal_size((100, 24)).columns


def out(text=""):
    sys.stdout.write(str(text) + "\n")
    sys.stdout.flush()


# ===================================================================== pieces
ICON = {"ok": "✓", "err": "✗", "warn": "!", "info": "•", "arrow": "→", "step": "❯"}


def ok(msg):
    out(f"{c(ICON['ok'], 'green', bold=True)} {msg}")


def warn(msg):
    out(f"{c(ICON['warn'], 'yellow', bold=True)} {msg}")


def err(msg):
    sys.stderr.write(f"{c(ICON['err'], 'red', bold=True)} {msg}\n")


def note(msg):
    out(f"{c(ICON['info'], 'dim')} {c(msg, 'dim')}")


def header(title, right=""):
    """A full-width rule with the title, like nala's section headers."""
    w = min(cols(), 110)
    left = f" {title} "
    rgt = f" {right} " if right else ""
    line = "━" * max(4, w - width(left) - width(rgt) - 2)
    out(c("━━", "mauve") + c(left, "text", bold=True) + c(line, "faint") + (c(rgt, "dim") if rgt else ""))


def table(rows, headers, aligns=None, title=None):
    """A rounded, boxed table. rows: lists of (already coloured) strings."""
    aligns = aligns or ["l"] * len(headers)
    w = [max([width(h) for h in [headers[i]]] + [width(r[i]) for r in rows]) for i in range(len(headers))]
    avail = min(cols(), 140) - (3 * len(w) + 1)
    while sum(w) > avail and max(w) > 12:   # squeeze the widest column to fit the terminal
        i = w.index(max(w))
        w[i] -= 1
    def cell(text, i):
        t = str(text)
        if width(t) > w[i]:
            plain = _strip(t)
            t = plain[: max(1, w[i] - 1)] + "…"
        return pad(t, w[i], aligns[i] == "r")
    bc = lambda s: c(s, "faint")
    top = bc("╭─" + "─┬─".join("─" * x for x in w) + "─╮")
    mid = bc("├─" + "─┼─".join("─" * x for x in w) + "─┤")
    bot = bc("╰─" + "─┴─".join("─" * x for x in w) + "─╯")
    if title:
        header(title)
    out(top)
    out(bc("│ ") + bc(" │ ").join(c(cell(h, i), "sub", bold=True) for i, h in enumerate(headers)) + bc(" │"))
    out(mid)
    for r in rows:
        out(bc("│ ") + bc(" │ ").join(cell(x, i) for i, x in enumerate(r)) + bc(" │"))
    out(bot)


def _strip(s):
    import re
    return re.sub(r"\033\[[0-9;]*m", "", s)


def summary(parts):
    """`Summary: Install 2 · Upgrade 3 · Remove 1` with coloured counts."""
    bits = [f"{label} {c(n, color, bold=True)}" for label, n, color in parts if n]
    out(c("Summary", "text", bold=True) + c(":  ", "dim") + c("  ·  ", "faint").join(bits))


def confirm(question="Do you want to continue?", default=True, assume=None):
    if assume is not None:
        return assume
    if not sys.stdin.isatty():
        return default
    hint = "[Y/n]" if default else "[y/N]"
    sys.stdout.write(f"{c('?', 'mauve', bold=True)} {question} {c(hint, 'dim')} ")
    sys.stdout.flush()
    try:
        ans = input().strip().lower()
    except EOFError:
        return default
    return default if not ans else ans in ("y", "yes")


def elapsed(t0):
    s = time.monotonic() - t0
    return f"{s:.1f}s" if s < 60 else f"{int(s // 60)}m {int(s % 60)}s"


# ===================================================================== live progress
class Progress:
    """One line per task, redrawn in place while tasks run in parallel:

        ⠹ ganit    fetching        ━━━━━━━━━──────
        ✓ dvara    v0.1.4 → v0.1.5
    Plain lines (one per finished task) when not on a terminal."""
    FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self, names, title=None):
        self.names = list(names)
        self.state = {n: ("wait", "waiting") for n in self.names}
        self.lock = threading.Lock()
        self.frame = 0
        self.title = title
        self.drawn = 0
        self.stop_ev = threading.Event()
        self.nw = max([width(n) for n in self.names] + [4])
        self.t0 = time.monotonic()

    def __enter__(self):
        if self.title:
            header(self.title, f"{len(self.names)} package{'s' if len(self.names) != 1 else ''}")
        if TTY:
            sys.stdout.write("\033[?25l")   # hide the cursor while drawing
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.start()
        return self

    def __exit__(self, *exc):
        self.stop_ev.set()
        if TTY:
            self.thread.join()
            self._draw()
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()

    def set(self, name, kind, text):
        """kind: wait | run | ok | err | skip"""
        with self.lock:
            self.state[name] = (kind, text)
        if not TTY and kind in ("ok", "err", "skip"):
            icon = {"ok": ICON["ok"], "err": ICON["err"], "skip": "-"}[kind]
            out(f"{icon} {pad(name, self.nw)}  {text}")

    def _loop(self):
        while not self.stop_ev.wait(0.08):
            self.frame += 1
            self._draw()

    def _line(self, name):
        kind, text = self.state[name]
        if kind == "run":
            icon = c(self.FRAMES[self.frame % len(self.FRAMES)], "mauve")
            bar_w = 14
            pos = self.frame % (bar_w * 2)
            pos = pos if pos < bar_w else bar_w * 2 - pos
            bar = c("━" * pos, "faint") + c("━━━", "mauve") + c("━" * max(0, bar_w - pos), "faint")
            return f"{icon} {c(pad(name, self.nw), 'text', bold=True)}  {pad(c(text, 'sub'), 22)} {bar}"
        if kind == "ok":
            return f"{c(ICON['ok'], 'green', bold=True)} {pad(name, self.nw)}  {text}"
        if kind == "err":
            return f"{c(ICON['err'], 'red', bold=True)} {pad(name, self.nw)}  {c(text, 'red')}"
        if kind == "skip":
            return f"{c('–', 'dim')} {c(pad(name, self.nw), 'dim')}  {c(text, 'dim')}"
        return f"{c('·', 'faint')} {c(pad(name, self.nw), 'dim')}  {c(text, 'faint')}"

    def _draw(self):
        with self.lock:
            lines = [self._line(n) for n in self.names]
        buf = []
        if self.drawn:
            buf.append(f"\033[{self.drawn}F")
        for l in lines:
            buf.append("\033[2K" + l + "\n")
        sys.stdout.write("".join(buf))
        sys.stdout.flush()
        self.drawn = len(lines)


class Spinner:
    """A single spinner line for a short wait ("checking for updates")."""

    def __init__(self, text):
        self.text = text
        self.ev = threading.Event()

    def __enter__(self):
        if TTY:
            sys.stdout.write("\033[?25l")
            self.t = threading.Thread(target=self._spin, daemon=True)
            self.t.start()
        return self

    def _spin(self):
        i = 0
        while not self.ev.wait(0.08):
            sys.stdout.write(f"\r\033[2K{c(Progress.FRAMES[i % 10], 'mauve')} {c(self.text, 'sub')}")
            sys.stdout.flush()
            i += 1

    def __exit__(self, *exc):
        self.ev.set()
        if TTY:
            self.t.join()
            sys.stdout.write("\r\033[2K\033[?25h")
            sys.stdout.flush()
