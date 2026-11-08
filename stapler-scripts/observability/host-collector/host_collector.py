#!/usr/bin/env python3
"""macOS host-contention collector: Prometheus text on 127.0.0.1:64891/metrics.

Runs natively (NOT in Docker) because Docker's own node exporter only sees the
Docker VM. No root needed, stdlib only, Python >= 3.9. Alloy scrapes it via
host.docker.internal (see ../alloy-config.alloy).

A background sampler refreshes a cache every SAMPLE_INTERVAL seconds, so a
scrape only formats cached numbers and stays fast even when the host is
starved. Every data source is optional: a failure bumps
host_collector_errors_total{source} and the rest still serve.

Per-process CPU is derived from deltas of cumulative CPU time between samples
(ps %cpu on macOS is a lifetime average, useless for "right now"). Processes
that start and exit entirely between two samples are invisible.
"""
import ctypes
import ctypes.util
import os
import re
import resource
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("HOST_COLLECTOR_PORT", "64891"))  # 61000 + CRC32("host-collector") % 4525
BIND = os.environ.get("HOST_COLLECTOR_BIND", "127.0.0.1")
SAMPLE_INTERVAL = float(os.environ.get("HOST_COLLECTOR_INTERVAL", "10"))
DOCKER_INTERVAL = float(os.environ.get("HOST_COLLECTOR_DOCKER_INTERVAL", "30"))
TOP_OTHERS = 10
TOP_CONTAINERS = 10
THREADS_EVERY = 3  # `ps -M` is the costliest call; refresh thread counts every Nth sample
SLOW_EVERY = 6  # thermal / docker-independent slow sources
DATA_VOLUME = "/System/Volumes/Data"
PAGE = os.sysconf("SC_PAGE_SIZE")
NCPU = os.cpu_count() or 1

# (group, regex over the full executable path); first match wins.
GROUPS = [
    ("docker_vm", r"com\.apple\.Virtualization\.VirtualMachine|Virtual Machine Service"),
    ("edr_falcon", r"Falcon|falcon|[Cc]rowd[Ss]trike"),
    ("fseventsd", r"/fseventsd$"),
    ("opendirectoryd", r"/opendirectoryd$"),
    ("windowserver", r"/WindowServer$"),
    ("kernel_task", r"(^|/)kernel_task$"),
    ("diagnosticd", r"/diagnosticd$"),
    ("spotlight", r"/(mds|mds_stores|mdworker\w*|mdbulkimport|corespotlightd)$"),
    ("backupd", r"/backupd(-helper)?$"),
    ("chrome", r"Google Chrome"),
    ("go_test", r"\.test$"),
    ("go_build", r"/(go|compile|link|asm|cgo|vet|gofmt)$"),
    ("claude", r"/claude$|/claude/"),
    ("stapler_squad", r"/stapler-squad[^/]*$"),
    ("tmux", r"/tmux$"),
    ("docker", r"com\.docker|/Docker\.app|/docker$"),
]
GROUPS = [(n, re.compile(p)) for n, p in GROUPS]
GROUP_NAMES = [n for n, _ in GROUPS]

state_lock = threading.Lock()
metrics_text = "# collector warming up\n"
errors = {}
started = time.time()


def bump_error(source):
    errors[source] = errors.get(source, 0) + 1


def run(cmd, timeout=15):
    """Run a command, return stdout or None (and count the error)."""
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if out.returncode != 0:
            bump_error(cmd[0])
            return None
        return out.stdout
    except (OSError, subprocess.SubprocessError):
        bump_error(cmd[0])
        return None


def esc(v):
    return str(v).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


class Out:
    def __init__(self):
        self.lines = []
        self.declared = set()

    def add(self, metric, mtype, help_text, value, **labels):
        if metric not in self.declared:
            self.declared.add(metric)
            self.lines.append("# HELP %s %s" % (metric, help_text))
            self.lines.append("# TYPE %s %s" % (metric, mtype))
        lab = ""
        if labels:
            lab = "{" + ",".join('%s="%s"' % (k, esc(v)) for k, v in labels.items()) + "}"
        self.lines.append("%s%s %s" % (metric, lab, repr(float(value))))


# ---- CPU ticks via Mach (no exec, uint32 counters that wrap) ----
_libsys = None
try:
    _libsys = ctypes.CDLL(ctypes.util.find_library("System"))
    _libsys.mach_host_self.restype = ctypes.c_uint
except Exception:
    _libsys = None


def cpu_ticks():
    """Return (user, system, idle, nice) cumulative ticks (100 Hz) or None."""
    if _libsys is None:
        return None
    buf = (ctypes.c_uint * 4)()
    cnt = ctypes.c_uint(4)
    if _libsys.host_statistics(_libsys.mach_host_self(), 3, buf, ctypes.byref(cnt)) != 0:
        bump_error("host_statistics")
        return None
    return tuple(buf)


def parse_cputime(s):
    secs = 0.0
    for part in s.split(":"):
        secs = secs * 60 + float(part)
    return secs


class Sampler:
    def __init__(self):
        self.n = 0
        self.last_ticks = None
        self.cum_ticks = [0, 0, 0, 0]  # accumulated, wrap-safe
        self.cpu_pct = None
        self.last_proc = {}  # pid -> cputime seconds
        self.last_proc_t = None
        self.proc_cpu_by_pid = {}
        self.threads_by_pid = {}
        self.total_threads = None
        self.last_io = None
        self.thermal = None
        self.docker = None
        self.docker_lock = threading.Lock()

    # -- individual sources; each returns list of emit callables' effect via Out --
    def sample_cpu(self):
        t = cpu_ticks()
        if t is None:
            return
        if self.last_ticks is not None:
            d = [(t[i] - self.last_ticks[i]) % (1 << 32) for i in range(4)]
            for i in range(4):
                self.cum_ticks[i] += d[i]
            total = sum(d) or 1
            self.cpu_pct = (100.0 * d[1] / total, 100.0 * (d[0] + d[3]) / total, 100.0 * d[2] / total)
        self.last_ticks = t

    def sample_procs(self):
        out = run(["ps", "-axo", "pid=,time=,rss=,comm="])
        if out is None:
            return None
        now = time.time()
        procs = []
        cur = {}
        for line in out.splitlines():
            f = line.split(None, 3)
            if len(f) < 4:
                continue
            try:
                pid, ct, rss = int(f[0]), parse_cputime(f[1]), int(f[2])
            except ValueError:
                continue
            cur[pid] = ct
            procs.append((pid, ct, rss, f[3]))
        dt = (now - self.last_proc_t) if self.last_proc_t else None
        pcpu = {}
        if dt and dt > 0.5:
            for pid, ct, _, _ in procs:
                prev = self.last_proc.get(pid)
                delta = ct - prev if prev is not None and ct >= prev else ct
                pcpu[pid] = max(0.0, 100.0 * delta / dt)
            self.proc_cpu_by_pid = pcpu
        self.last_proc, self.last_proc_t = cur, now
        return procs if dt else None

    def sample_threads(self):
        out = run(["ps", "-axM"], timeout=20)
        if out is None:
            return
        counts, pid, total = {}, None, 0
        for line in out.splitlines()[1:]:
            if line and not line[0].isspace():
                f = line.split(None, 2)
                try:
                    pid = int(f[1])
                except (IndexError, ValueError):
                    pid = None
            if pid is not None:
                counts[pid] = counts.get(pid, 0) + 1
                total += 1
        self.threads_by_pid, self.total_threads = counts, total

    def sample_io(self):
        out = run(["ioreg", "-rc", "IOBlockStorageDriver", "-k", "Statistics", "-w0"])
        if out is None:
            return
        rd = sum(int(x) for x in re.findall(r'"Bytes \(Read\)"=(\d+)', out))
        wr = sum(int(x) for x in re.findall(r'"Bytes \(Write\)"=(\d+)', out))
        self.last_io = (rd, wr)

    def sample_thermal(self):
        out = run(["pmset", "-g", "therm"])
        if out is None:
            return
        res = {}
        m = re.search(r"CPU_Speed_Limit\s*=\s*(\d+)", out)
        if m:
            res["speed_limit"] = int(m.group(1))
        res["warning"] = 0 if "No thermal warning level" in out else 1
        self.thermal = res

    def sample_docker(self):
        ps = run(["docker", "ps", "--format", "{{.Names}}\t{{.Image}}"], timeout=20)
        st = run(["docker", "stats", "--no-stream", "--format", "{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"], timeout=60)
        if ps is None or st is None:
            self.docker = None
            return
        images = dict(l.split("\t", 1) for l in ps.splitlines() if "\t" in l)
        rows = []
        for l in st.splitlines():
            f = l.split("\t")
            if len(f) < 3:
                continue
            try:
                cpu = float(f[1].rstrip("%"))
            except ValueError:
                continue
            rows.append((f[0], images.get(f[0], "unknown"), cpu))
        rows.sort(key=lambda r: -r[2])
        keep = rows[:TOP_CONTAINERS]
        rest = rows[TOP_CONTAINERS:]
        if rest:
            keep.append(("other", "other", sum(r[2] for r in rest)))
        with self.docker_lock:
            self.docker = keep

    def docker_loop(self):
        while True:
            try:
                self.sample_docker()
            except Exception:
                bump_error("docker_loop")
            time.sleep(DOCKER_INTERVAL)

    # -- rendering --
    def classify(self, procs):
        agg = {}

        def slot(g):
            return agg.setdefault(g, {"cpu": 0.0, "rss": 0, "threads": 0, "count": 0})

        for pid, _, rss, comm in procs:
            g = next((n for n, rx in GROUPS if rx.search(comm)), None)
            if g is None:
                g = "~" + os.path.basename(comm.split(".app/")[0].rstrip("/")) if comm else "~unknown"
            s = slot(g)
            s["cpu"] += self.proc_cpu_by_pid.get(pid, 0.0)
            s["rss"] += rss * 1024
            s["threads"] += self.threads_by_pid.get(pid, 0)
            s["count"] += 1
        for n in GROUP_NAMES:
            slot(n)
        named = {g: v for g, v in agg.items() if not g.startswith("~")}
        others = sorted(((g, v) for g, v in agg.items() if g.startswith("~")), key=lambda kv: -kv[1]["cpu"])
        final = dict(named)
        rest = {"cpu": 0.0, "rss": 0, "threads": 0, "count": 0}
        for i, (g, v) in enumerate(others):
            if i < TOP_OTHERS and v["cpu"] > 0.5:
                final[g] = v
            else:
                for k in rest:
                    rest[k] += v[k]
        final["other"] = rest
        return final

    def render(self, procs):
        o = Out()
        if self.cpu_pct:
            for mode, v in zip(("system", "user", "idle"), self.cpu_pct):
                o.add("host_cpu_percent", "gauge", "Host CPU time share over the last sample (all cores = 100).", v, mode=mode)
        names = ("user", "system", "idle", "nice")
        for i, mode in enumerate(names):
            o.add("host_cpu_seconds_total", "counter", "Host CPU seconds summed over all cores, since collector start.", self.cum_ticks[i] / 100.0, mode=mode)
        o.add("host_cpu_count", "gauge", "Logical CPU count.", NCPU)
        try:
            l1, l5, l15 = os.getloadavg()
            o.add("host_load1", "gauge", "1-minute load average.", l1)
            o.add("host_load5", "gauge", "5-minute load average.", l5)
            o.add("host_load15", "gauge", "15-minute load average.", l15)
        except OSError:
            bump_error("getloadavg")

        vm = run(["vm_stat"])
        if vm:
            pg = {}
            for line in vm.splitlines():
                m = re.match(r'"?([^":]+)"?:\s+(\d+)\.', line)
                if m:
                    pg[m.group(1).strip()] = int(m.group(2))
            for state, key in (("free", "Pages free"), ("active", "Pages active"), ("inactive", "Pages inactive"),
                               ("wired", "Pages wired down"), ("compressed", "Pages occupied by compressor"),
                               ("speculative", "Pages speculative")):
                if key in pg:
                    o.add("host_memory_bytes", "gauge", "Physical memory by vm_stat state.", pg[key] * PAGE, state=state)
            for name, key in (("pagein", "Pageins"), ("pageout", "Pageouts"), ("swapin", "Swapins"), ("swapout", "Swapouts")):
                if key in pg:
                    o.add("host_vm_%s_bytes_total" % name, "counter", "Cumulative %s traffic since boot." % name, pg[key] * PAGE)
        mt = run(["sysctl", "-n", "hw.memsize"])
        if mt and mt.strip().isdigit():
            o.add("host_memory_total_bytes", "gauge", "Installed RAM.", int(mt))
        sw = run(["sysctl", "-n", "vm.swapusage"])
        if sw:
            m = re.search(r"total = ([\d.]+)M\s+used = ([\d.]+)M", sw)
            if m:
                o.add("host_swap_total_bytes", "gauge", "Swap file size currently allocated.", float(m.group(1)) * 1048576)
                o.add("host_swap_used_bytes", "gauge", "Swap in use.", float(m.group(2)) * 1048576)
        pr = run(["sysctl", "-n", "kern.memorystatus_vm_pressure_level"])
        if pr and pr.strip().isdigit():
            o.add("host_memory_pressure_level", "gauge", "kern.memorystatus_vm_pressure_level: 1 normal, 2 warn, 4 critical.", int(pr))

        try:
            st = os.statvfs(DATA_VOLUME)
            o.add("host_filesystem_free_bytes", "gauge", "Free bytes available to non-root (excludes APFS purgeable space).", st.f_bavail * st.f_frsize, mount=DATA_VOLUME)
            o.add("host_filesystem_size_bytes", "gauge", "Volume size.", st.f_blocks * st.f_frsize, mount=DATA_VOLUME)
        except OSError:
            bump_error("statvfs")
        if self.last_io:
            o.add("host_disk_io_bytes_total", "counter", "Cumulative block-device bytes (ioreg IOBlockStorageDriver).", self.last_io[0], direction="read")
            o.add("host_disk_io_bytes_total", "counter", "Cumulative block-device bytes (ioreg IOBlockStorageDriver).", self.last_io[1], direction="write")

        if procs is not None:
            o.add("host_process_count", "gauge", "Total processes.", len(procs))
        if self.total_threads is not None:
            o.add("host_thread_count", "gauge", "Total threads.", self.total_threads)
        if self.thermal:
            if "speed_limit" in self.thermal:
                o.add("host_thermal_cpu_speed_limit_percent", "gauge", "pmset CPU_Speed_Limit (100 = unthrottled); absent when macOS reports none.", self.thermal["speed_limit"])
            o.add("host_thermal_warning", "gauge", "1 if pmset reports a recorded thermal warning level.", self.thermal["warning"])

        if procs:
            for g, v in sorted(self.classify(procs).items()):
                o.add("host_process_cpu_percent", "gauge", "Group CPU, 100 = one core (Activity Monitor units).", v["cpu"], group=g)
                o.add("host_process_rss_bytes", "gauge", "Group resident memory.", v["rss"], group=g)
                o.add("host_process_threads", "gauge", "Group thread count.", v["threads"], group=g)
                o.add("host_process_instances", "gauge", "Group process count.", v["count"], group=g)

        with self.docker_lock:
            dk = self.docker
        o.add("host_docker_up", "gauge", "1 if `docker stats` worked on the last attempt.", 0 if dk is None else 1)
        for name, image, cpu in dk or []:
            o.add("host_docker_container_cpu_percent", "gauge", "Container CPU, 100 = one core of the Docker VM.", cpu, name=name, image=image)
        return o

    def loop(self):
        global metrics_text
        procs = None
        while True:
            t0 = time.time()
            try:
                self.sample_cpu()
                got = self.sample_procs()
                if got is not None:
                    procs = got
                if self.n % THREADS_EVERY == 0:
                    self.sample_threads()
                self.sample_io()
                if self.n % SLOW_EVERY == 0:
                    self.sample_thermal()
                o = self.render(procs)
            except Exception as e:  # never die: a dead sampler serves stale data forever
                bump_error("sampler")
                sys.stderr.write("sample failed: %r\n" % (e,))
                o = Out()
            dur = time.time() - t0
            o.add("host_collector_sample_duration_seconds", "gauge", "Wall time of the last sampling cycle.", dur)
            ru, rc = resource.getrusage(resource.RUSAGE_SELF), resource.getrusage(resource.RUSAGE_CHILDREN)
            o.add("host_collector_cpu_seconds_total", "counter", "CPU seconds used by the collector and the ps/vm_stat/docker children it spawned.", ru.ru_utime + ru.ru_stime + rc.ru_utime + rc.ru_stime)
            o.add("host_collector_up_seconds", "gauge", "Seconds since the collector started.", time.time() - started)
            for src in sorted(errors):
                o.add("host_collector_errors_total", "counter", "Failed data-source calls by source.", errors[src], source=src)
            with state_lock:
                metrics_text = "\n".join(o.lines) + "\n"
            self.n += 1
            time.sleep(max(0.5, SAMPLE_INTERVAL - dur) if self.n > 1 else 1.0)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?")[0] not in ("/metrics", "/"):
            self.send_error(404)
            return
        with state_lock:
            body = metrics_text.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def main():
    s = Sampler()
    threading.Thread(target=s.loop, daemon=True).start()
    threading.Thread(target=s.docker_loop, daemon=True).start()
    ThreadingHTTPServer((BIND, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
