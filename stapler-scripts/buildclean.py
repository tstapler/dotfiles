#!/usr/bin/env python3
"""Find and remove rebuildable build dirs (node_modules, cargo target) fast.

Refuses to start on a metadata-starved btrfs (where every write blocks in the
kernel), walks directories in parallel and streams hits straight into
deletion, opens with O_NOATIME so reads don't dirty metadata, and runs a
watchdog that says why it is stalled. Dry run unless --apply.
"""
from __future__ import annotations

import argparse
import functools
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

HOME = Path.home()
DEFAULT_ROOTS = [HOME / "Programming", HOME / "code", HOME / "dotfiles"]
KINDS = {"node_modules": "package.json", "target": "Cargo.toml"}  # dir -> sibling marker
SKIP_WALK = {".git", ".hg", ".svn"}
STALL_AFTER_S = 15
MIN_UNALLOCATED = 1 << 30  # below this, metadata cannot grow
MIN_META_HEADROOM = 64 << 20


# ── btrfs preflight ──────────────────────────────────────────────────────────
def btrfs_alloc(path: Path) -> dict | None:
    """Allocation stats for the btrfs fs holding `path`; None if not btrfs."""
    src, best, fstype_found = None, -1, ""
    real = str(path.resolve())
    for line in Path("/proc/mounts").read_text().splitlines():
        dev, mnt, fstype, *_ = line.split()
        covers = real == mnt or real.startswith(mnt.rstrip("/") + "/")
        if covers and len(mnt) > best:  # longest mount wins, whatever its fstype
            src, best, fstype_found = dev, len(mnt), fstype
    if fstype_found != "btrfs":
        return None
    name = os.path.basename(os.path.realpath(src))
    for fs in Path("/sys/fs/btrfs").iterdir():
        devdir = fs / "devices"
        if not devdir.is_dir() or name not in os.listdir(devdir):
            continue
        read = lambda *p: int((fs / "allocation" / Path(*p)).read_text())  # noqa: E731
        size = int((Path("/sys/class/block") / name / "size").read_text()) * 512
        alloc = sum(read(t, "disk_total") for t in ("data", "metadata", "system"))
        # Normal writes can't touch the global reserve, so subtract it (and
        # in-flight reservations) or the headroom looks ~512 MiB too healthy.
        grsv = int((fs / "allocation" / "global_rsv_size").read_text())
        headroom = (read("metadata", "total_bytes") - read("metadata", "bytes_used")
                    - read("metadata", "bytes_reserved") - read("metadata", "bytes_may_use") - grsv)
        return {"unallocated": size - alloc, "meta_headroom": headroom}
    return None


def starved(a: dict) -> bool:
    return a["unallocated"] < MIN_UNALLOCATED and a["meta_headroom"] < MIN_META_HEADROOM


# ── model + counters ─────────────────────────────────────────────────────────
@dataclass
class Hit:
    path: str
    kind: str
    inodes: int = 0
    bytes: int = 0
    removed: bool = False
    error: str = ""


@dataclass
class Progress:
    lock: threading.Lock = field(default_factory=threading.Lock)
    dirs_scanned: int = 0
    hits: int = 0
    inodes_done: int = 0
    pending: int = 0
    skipped: list = field(default_factory=list)

    def tick(self) -> int:
        return self.dirs_scanned + self.inodes_done + self.hits


def open_dir(path: str) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        return os.open(path, flags | os.O_NOATIME)
    except PermissionError:  # O_NOATIME needs file ownership
        return os.open(path, flags)


# ── deletion / measurement ───────────────────────────────────────────────────
def open_subdir(name: str, dir_fd: int, apply: bool) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        return os.open(name, flags, dir_fd=dir_fd)
    except PermissionError:
        if not apply:
            raise
        os.chmod(name, 0o700, dir_fd=dir_fd)  # bazel/go-mod trees ship read-only
        return os.open(name, flags, dir_fd=dir_fd)


def process_build_dir(hit: Hit, apply: bool, prog: Progress) -> Hit:
    def walk(fd: int) -> None:
        if apply and not os.fstat(fd).st_mode & 0o200:
            os.fchmod(fd, 0o700)  # unlinking needs write permission on the parent dir
        with os.scandir(fd) as it:
            for e in it:
                hit.inodes += 1
                try:
                    if e.is_dir(follow_symlinks=False):
                        sub = open_subdir(e.name, fd, apply)
                        try:
                            walk(sub)
                        finally:
                            os.close(sub)
                        if apply:
                            os.rmdir(e.name, dir_fd=fd)
                    else:
                        hit.bytes += e.stat(follow_symlinks=False).st_size
                        if apply:
                            os.unlink(e.name, dir_fd=fd)
                except OSError as exc:
                    hit.error = hit.error or f"{e.name}: {exc.strerror}"
        with prog.lock:
            prog.inodes_done += 1

    try:
        fd = open_dir(hit.path)
        try:
            walk(fd)
        finally:
            os.close(fd)
        if apply and not hit.error:
            os.rmdir(hit.path)
            hit.removed = True
    except OSError as exc:
        hit.error = hit.error or f"{hit.path}: {exc.strerror}"
    return hit


# ── parallel discovery ───────────────────────────────────────────────────────
def scan_dir(path: str, dev: int, ctx: dict) -> None:
    prog: Progress = ctx["prog"]
    try:
        fd = open_dir(path)
    except OSError:
        return finish(ctx)
    # scandir(fd) yields bare names and can't stat after the fd closes, so
    # collect names and stat only the rare build-dir candidates up front.
    subdirs, names, cand = [], set(), {}
    try:
        with os.scandir(fd) as it:
            for e in it:
                names.add(e.name)
                if not e.is_dir(follow_symlinks=False):
                    continue
                subdirs.append(e.name)
                if e.name in KINDS:
                    cand[e.name] = e.stat(follow_symlinks=False)
    except OSError:
        pass
    finally:
        os.close(fd)
    for name in subdirs:
        marker = KINDS.get(name)
        full = os.path.join(path, name)
        if marker and marker in names:
            consider_hit(full, name, cand[name], dev, ctx)
        elif name not in SKIP_WALK and name not in KINDS:
            submit_scan(full, dev, ctx)
    with prog.lock:
        prog.dirs_scanned += 1
    finish(ctx)


def process_cwds() -> list[str]:
    """Working dirs of this user's running processes (others' are unreadable)."""
    cwds = set()
    for p in Path("/proc").iterdir():
        if p.name.isdigit():
            try:
                cwds.add(os.readlink(p / "cwd"))
            except OSError:
                pass
    return sorted(cwds)


@functools.lru_cache(maxsize=None)
def checkout_root(directory: str) -> str | None:
    """Nearest ancestor-or-self holding .git (a dir, or a file for linked worktrees)."""
    d = directory
    while d not in ("/", ""):
        if os.path.exists(os.path.join(d, ".git")):
            return d
        d = os.path.dirname(d)
    return None


def in_use(path: str, cwds: list[str]) -> bool:
    """True if a process works in the same checkout that owns `path`.

    A session at a main checkout does not block nested worktrees, which have
    their own .git; without any .git above, fall back to the parent directory.
    """
    project = os.path.dirname(path)
    root = checkout_root(project) or project
    return any((c == root or c.startswith(root + "/")) and (checkout_root(c) or root) == root
               for c in cwds)


def consider_hit(full: str, name: str, st: os.stat_result, dev: int, ctx: dict) -> None:
    prog: Progress = ctx["prog"]
    if st.st_dev != dev:
        return
    age = time.time() - st.st_mtime
    if age < ctx["min_age_s"]:
        prog.skipped.append(f"{full} (touched {int(age // 60)}m ago)")
        return
    if in_use(full, ctx["cwds"]):
        prog.skipped.append(f"{full} (a running process is working there)")
        return
    hit = Hit(full, name)
    with prog.lock:
        prog.hits += 1
        prog.pending += 1
    ctx["results"].append(ctx["delete_pool"].submit(process_build_dir, hit, ctx["apply"], prog))


def submit_scan(path: str, dev: int, ctx: dict) -> None:
    with ctx["prog"].lock:
        ctx["scan_pending"] += 1
    ctx["scan_pool"].submit(scan_dir, path, dev, ctx)


def finish(ctx: dict) -> None:
    with ctx["prog"].lock:
        ctx["scan_pending"] -= 1
        if ctx["scan_pending"] == 0:
            ctx["scan_done"].set()


# ── watchdog ─────────────────────────────────────────────────────────────────
def kernel_waits() -> str:
    waits: dict[str, int] = {}
    for t in Path("/proc/self/task").iterdir():
        try:
            w = (t / "wchan").read_text().strip()
        except OSError:
            continue
        if w and w != "0":
            waits[w] = waits.get(w, 0) + 1
    return ", ".join(f"{k}×{v}" for k, v in sorted(waits.items(), key=lambda kv: -kv[1])[:3])


def watchdog(prog: Progress, stop: threading.Event, t0: float) -> None:
    last, last_t = prog.tick(), time.time()
    while not stop.wait(5):
        cur = prog.tick()
        now = time.time()
        line = (f"  [{now - t0:5.0f}s] scanned {prog.dirs_scanned} dirs, {prog.hits} build dirs, "
                f"{prog.inodes_done} dir-batches done")
        if cur == last and now - last_t >= STALL_AFTER_S:
            line += f"  STALLED {now - last_t:.0f}s, kernel waits: {kernel_waits() or 'unknown'}"
        elif cur != last:
            last, last_t = cur, now
        print(line, file=sys.stderr, flush=True)


# ── main ─────────────────────────────────────────────────────────────────────
def human(n: float) -> str:
    for u in ("B", "K", "M", "G", "T"):
        if abs(n) < 1024 or u == "T":
            return f"{int(n)}B" if u == "B" else f"{n:.1f}{u}"
        n /= 1024
    return f"{n:.1f}T"


MIN_REMOVE_DEPTH = 3  # parts below $HOME: ~/.cache/x/y ok, ~/.cache/x refused


def refuse_reason(path: Path) -> str | None:
    """Why an explicit --remove target is unsafe, or None if allowed."""
    if path.is_symlink():
        return "is a symlink"
    if not path.is_dir():
        return "not a directory"
    try:
        rel = path.resolve().relative_to(HOME)
    except ValueError:
        return "outside $HOME"
    if len(rel.parts) < MIN_REMOVE_DEPTH:
        return f"too shallow (need >= {MIN_REMOVE_DEPTH} path parts below $HOME)"
    return None


def submit_explicit(paths: list[Path], ctx: dict) -> list[str]:
    refused = []
    for p in paths:
        p = p.expanduser()
        why = refuse_reason(p)
        age = time.time() - p.stat().st_mtime if not why else 0
        if not why and age < ctx["min_age_s"]:
            why = f"touched {int(age // 60)}m ago"
        if not why and in_use(str(p.resolve()), ctx["cwds"]):
            why = "a running process is working there"
        if why:
            refused.append(f"{p} ({why})")
            continue
        ctx["prog"].hits += 1
        ctx["results"].append(ctx["delete_pool"].submit(
            process_build_dir, Hit(str(p), "explicit"), ctx["apply"], ctx["prog"]))
    return refused


def run(args: argparse.Namespace) -> int:
    for kind in [k for k in KINDS if k not in args.kinds]:
        del KINDS[kind]
    roots = [] if args.remove else [r.expanduser() for r in args.roots if r.expanduser().is_dir()]
    if args.remove:
        roots = [Path.home()]  # preflight only; nothing is scanned
    for root in roots:
        a = btrfs_alloc(root)
        if a:
            print(f"btrfs {root}: unallocated {human(a['unallocated'])}, "
                  f"metadata headroom {human(a['meta_headroom'])}")
            if starved(a) and not args.force:
                print("STARVED: no unallocated space and no metadata headroom. Every read/unlink will block\n"
                      "in the kernel (reserve_bytes). Free space as root first, e.g.\n"
                      "  sudo mount -o remount,noatime /   # stop reads dirtying metadata\n"
                      "  sudo btrfs device add <spare dev> /   # temporary extra space\n"
                      "then rerun, or pass --force to try anyway.", file=sys.stderr)
                return 3

    prog = Progress()
    ctx = {"prog": prog, "apply": args.apply, "min_age_s": args.min_age_min * 60, "results": [],
           "scan_pending": 0, "scan_done": threading.Event(), "cwds": process_cwds(),
           "scan_pool": ThreadPoolExecutor(args.scan_jobs), "delete_pool": ThreadPoolExecutor(args.jobs)}
    stop, t0 = threading.Event(), time.time()
    threading.Thread(target=watchdog, args=(prog, stop, t0), daemon=True).start()

    if args.remove:
        for refusal in submit_explicit(args.remove, ctx):
            print(f"  refused: {refusal}")
        ctx["scan_done"].set()
    else:
        for root in roots:
            submit_scan(str(root), root.stat().st_dev, ctx)
    ctx["scan_done"].wait()
    ctx["scan_pool"].shutdown()
    hits = [f.result() for f in list(ctx["results"])]
    ctx["delete_pool"].shutdown()
    stop.set()

    hits.sort(key=lambda h: h.inodes, reverse=True)
    mode = "APPLIED" if args.apply else "dry run"
    print(f"\n{mode}: {len(hits)} build dirs in {time.time() - t0:.1f}s")
    for s in prog.skipped:
        print(f"  skipped: {s}")
    for h in hits[: args.top]:
        state = "removed" if h.removed else ("ERR" if h.error else "would remove")
        print(f"  {h.inodes:>9,} inodes {human(h.bytes):>7} {h.kind:<12} {state:<12} {h.path}")
    for kind in sorted({h.kind for h in hits}):
        sel = [h for h in hits if h.kind == kind]
        print(f"  total {kind:<12} {len(sel):>4} dirs {sum(h.inodes for h in sel):>11,} inodes "
              f"{human(sum(h.bytes for h in sel)):>8}")
    errs = [h for h in hits if h.error]
    for h in errs[:10]:
        print(f"  error: {h.error}")
    if args.json:
        Path(args.json).write_text(json.dumps([h.__dict__ for h in hits], indent=1))
    return 1 if errs else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("roots", nargs="*", type=Path, default=DEFAULT_ROOTS)
    ap.add_argument("--apply", action="store_true", help="actually delete (default: dry run)")
    ap.add_argument("-j", "--jobs", type=int, default=24, help="delete/measure threads")
    ap.add_argument("--scan-jobs", type=int, default=16)
    ap.add_argument("--min-age-min", type=float, default=60, help="skip build dirs touched this recently")
    ap.add_argument("--kinds", nargs="+", default=list(KINDS), choices=list(KINDS),
                    help="build dir kinds to remove (default: all)")
    ap.add_argument("--remove", nargs="+", type=Path, metavar="DIR",
                    help="remove these exact dirs instead of scanning (must be >=3 parts below $HOME)")
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--json", help="write per-dir results here")
    ap.add_argument("--force", action="store_true", help="skip the starvation preflight")
    sys.stdout.reconfigure(line_buffering=True)
    return run(ap.parse_args())


if __name__ == "__main__":
    sys.exit(main())
