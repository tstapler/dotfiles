#!/usr/bin/env python3
"""
jvm-optimizer: Detect and interactively apply JVM and Gradle performance settings.

Covers: Gradle daemon JVM heap, GC selection, Transparent Huge Pages,
parallel builds, task caching, worker count, Kotlin daemon heap,
code cache size, and shell-level JAVA_TOOL_OPTIONS.

Writes to ~/.gradle/gradle.properties (no sudo required).
"""

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional


# ── terminal helpers ──────────────────────────────────────────────────────────

def bold(s: str) -> str:   return f"\033[1m{s}\033[0m"
def green(s: str) -> str:  return f"\033[32m{s}\033[0m"
def yellow(s: str) -> str: return f"\033[33m{s}\033[0m"
def red(s: str) -> str:    return f"\033[31m{s}\033[0m"
def dim(s: str) -> str:    return f"\033[2m{s}\033[0m"
def cyan(s: str) -> str:   return f"\033[36m{s}\033[0m"


def header(title: str):
    print(f"\n{bold(title)}")
    print("─" * len(title))


def ask(prompt: str, default: bool = True) -> bool:
    suffix = " [Y/n] " if default else " [y/N] "
    try:
        ans = input(f"  {prompt}{suffix}").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    return ans.startswith("y") if ans else default


def wrap(text: str, width: int = 70, indent: str = "  ") -> str:
    words, lines, line = text.split(), [], ""
    for w in words:
        if len(line) + len(w) + 1 > width:
            lines.append(indent + line)
            line = w
        else:
            line = (line + " " + w).lstrip()
    if line:
        lines.append(indent + line)
    return "\n".join(lines)


# ── helpers ───────────────────────────────────────────────────────────────────

def run_output(*cmd: str) -> str:
    try:
        return subprocess.check_output(
            list(cmd), stderr=subprocess.STDOUT, text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def read_file(path: str, default: str = "") -> str:
    try:
        return Path(path).read_text()
    except OSError:
        return default


def which(cmd: str) -> Optional[str]:
    return shutil.which(cmd)


# ── Gradle properties parsing ─────────────────────────────────────────────────

def parse_gradle_props(path: Path) -> dict[str, str]:
    """Parse key=value pairs from a gradle.properties file."""
    props: dict[str, str] = {}
    if not path.exists():
        return props
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            props[k.strip()] = v.strip()
    return props


def parse_xmx(jvmargs: str) -> Optional[int]:
    """Parse -Xmx value from a jvmargs string. Returns MB."""
    m = re.search(r"-Xmx(\d+)([gGmM]?)", jvmargs)
    if not m:
        return None
    val, unit = int(m.group(1)), m.group(2).lower()
    return val * 1024 if unit == "g" else val


def jvm_has_flag(jvmargs: str, flag: str) -> bool:
    return flag in jvmargs


def jvm_gc(jvmargs: str) -> Optional[str]:
    for gc in ("UseZGC", "UseShenandoahGC", "UseG1GC", "UseParallelGC"):
        if gc in jvmargs:
            return gc
    return None


# ── system detection ──────────────────────────────────────────────────────────

@dataclass
class JavaInfo:
    # Hardware
    cpu_count: int = 0
    ram_gb: float = 0.0

    # JVM on PATH
    java_path: str = ""
    java_version: int = 0        # major version: 8, 11, 17, 21, 25 …
    java_version_str: str = ""
    java_vendor: str = ""

    # Gradle
    gradle_path: str = ""
    gradle_version: str = ""
    gradle_java_home: str = ""   # from GRADLE_HOME or gradle.properties
    gradle_java_version: int = 0

    # gradle.properties
    gradle_props_path: Path = field(default_factory=lambda: Path.home() / ".gradle" / "gradle.properties")
    gradle_props: dict = field(default_factory=dict)

    # Parsed current settings
    current_daemon: Optional[bool] = None
    current_parallel: Optional[bool] = None
    current_caching: Optional[bool] = None
    current_configure_on_demand: Optional[bool] = None
    current_workers: Optional[int] = None
    current_xmx_mb: Optional[int] = None
    current_gc: Optional[str] = None
    current_has_thp: bool = False
    current_has_pretouch: bool = False
    current_has_code_cache: bool = False
    current_jvmargs: str = ""
    current_daemon_idle_ms: Optional[int] = None

    # Shell env
    java_tool_options: str = ""
    gradle_opts: str = ""
    java_opts: str = ""


def _java_major(version_str: str) -> int:
    """Extract major Java version (8, 11, 17, 21, 25 …) from version string."""
    m = re.search(r'version "(?:1\.)?(\d+)', version_str)
    return int(m.group(1)) if m else 0


def detect() -> JavaInfo:
    info = JavaInfo()

    # Hardware
    info.cpu_count = os.cpu_count() or 1
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                info.ram_gb = int(line.split()[1]) / 1024 / 1024
                break
    except OSError:
        pass

    # Java on PATH
    info.java_path = which("java") or ""
    if info.java_path:
        version_out = run_output("java", "-version")
        info.java_version_str = version_out
        info.java_version = _java_major(version_out)
        m = re.search(r"(OpenJDK|GraalVM|Eclipse|Amazon|Zulu|Corretto|Microsoft)", version_out, re.I)
        info.java_vendor = m.group(1) if m else "Unknown"

    # Gradle
    info.gradle_path = which("gradle") or ""
    if info.gradle_path:
        gradle_out = run_output("gradle", "--version")
        m = re.search(r"Gradle\s+(\S+)", gradle_out)
        info.gradle_version = m.group(1) if m else ""

    # gradle.properties
    info.gradle_props = parse_gradle_props(info.gradle_props_path)
    props = info.gradle_props

    # Gradle JDK
    gradle_java_home = (
        props.get("org.gradle.java.home")
        or os.environ.get("GRADLE_JAVA_HOME")
        or os.environ.get("JAVA_HOME")
        or info.java_path.replace("/bin/java", "") if info.java_path else ""
    )
    info.gradle_java_home = gradle_java_home
    if gradle_java_home:
        java_bin = Path(gradle_java_home) / "bin" / "java"
        if java_bin.exists():
            v = run_output(str(java_bin), "-version")
            info.gradle_java_version = _java_major(v)
    if not info.gradle_java_version:
        info.gradle_java_version = info.java_version

    # Parse existing settings
    def to_bool(v: str) -> Optional[bool]:
        if v.lower() == "true": return True
        if v.lower() == "false": return False
        return None

    info.current_daemon = to_bool(props.get("org.gradle.daemon", ""))
    info.current_parallel = to_bool(props.get("org.gradle.parallel", ""))
    info.current_caching = to_bool(props.get("org.gradle.caching", ""))
    info.current_configure_on_demand = to_bool(props.get("org.gradle.configureondemand", ""))
    workers = props.get("org.gradle.workers.max", "")
    info.current_workers = int(workers) if workers.isdigit() else None
    idle = props.get("org.gradle.daemon.idletimeout", "")
    info.current_daemon_idle_ms = int(idle) if idle.isdigit() else None

    jvmargs = props.get("org.gradle.jvmargs", "")
    info.current_jvmargs = jvmargs
    info.current_xmx_mb = parse_xmx(jvmargs)
    info.current_gc = jvm_gc(jvmargs)
    info.current_has_thp = "-XX:+UseTransparentHugePages" in jvmargs
    info.current_has_pretouch = "-XX:+AlwaysPreTouch" in jvmargs
    info.current_has_code_cache = "ReservedCodeCacheSize" in jvmargs

    # Shell env
    info.java_tool_options = os.environ.get("JAVA_TOOL_OPTIONS", "")
    info.gradle_opts = os.environ.get("GRADLE_OPTS", "")
    info.java_opts = os.environ.get("JAVA_OPTS", "")

    return info


def print_summary(info: JavaInfo):
    header("System & JVM Summary")
    print(f"  {'CPUs':<24} {info.cpu_count}")
    print(f"  {'RAM':<24} {info.ram_gb:.1f} GB")
    print()
    print(f"  {'Java on PATH':<24} {info.java_version_str.splitlines()[0] if info.java_version_str else red('not found')}")
    if info.gradle_path:
        print(f"  {'Gradle':<24} {info.gradle_version} ({info.gradle_path})")
        jdk_str = f"JDK {info.gradle_java_version}"
        if info.gradle_java_home:
            jdk_str += f"  {dim(info.gradle_java_home)}"
        print(f"  {'Gradle JDK':<24} {jdk_str}")
    else:
        print(f"  {'Gradle':<24} {red('not found on PATH')}")
    print()
    print(f"  {dim('─── gradle.properties ───────────────────────────')}")

    def show(label: str, val, good=True, suffix: str = ""):
        if val is None:
            status = yellow("not set")
        elif isinstance(val, bool):
            status = (green if (val == good) else red)(str(val).lower())
        else:
            status = str(val) + suffix
        print(f"  {'  ' + label:<24} {status}")

    show("daemon", info.current_daemon, good=True)
    show("parallel", info.current_parallel, good=True)
    show("caching", info.current_caching, good=True)
    show("configureondemand", info.current_configure_on_demand, good=True)
    show("workers.max", info.current_workers)
    show("daemon.idletimeout", info.current_daemon_idle_ms, suffix=" ms")
    if info.current_xmx_mb:
        show("jvmargs Xmx", f"{info.current_xmx_mb} MB")
    else:
        show("jvmargs Xmx", None)
    show("jvmargs GC", info.current_gc or (yellow("none (default G1GC)") if not info.current_gc else info.current_gc))
    show("jvmargs THP", info.current_has_thp)
    show("jvmargs AlwaysPreTouch", info.current_has_pretouch)
    show("jvmargs CodeCache", info.current_has_code_cache)

    if info.java_tool_options or info.gradle_opts:
        print()
        if info.java_tool_options:
            print(f"  {'JAVA_TOOL_OPTIONS':<24} {dim(info.java_tool_options)}")
        if info.gradle_opts:
            print(f"  {'GRADLE_OPTS':<24} {dim(info.gradle_opts)}")


# ── gradle.properties writer ──────────────────────────────────────────────────

def set_gradle_prop(path: Path, key: str, value: str):
    """Set or add a key=value in gradle.properties, preserving comments."""
    if path.exists():
        content = path.read_text()
        lines = content.splitlines(keepends=True)
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("#") or "=" not in stripped:
                continue
            k = stripped.split("=", 1)[0].strip()
            if k == key:
                lines[i] = f"{key}={value}\n"
                path.write_text("".join(lines))
                return
        # Not found — append
        if not content.endswith("\n"):
            content += "\n"
        path.write_text(content + f"{key}={value}\n")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{key}={value}\n")


def update_jvmargs(path: Path, current: str, new_flags: dict[str, str]):
    """
    Merge new_flags into the current org.gradle.jvmargs value.
    new_flags: {flag_pattern_to_replace_or_add: replacement_string}
    Each entry is either a regex substitution or a straight append.
    """
    args = current

    for pattern, replacement in new_flags.items():
        if re.search(pattern, args):
            args = re.sub(pattern, replacement, args)
        else:
            args = args.rstrip() + " " + replacement

    args = " ".join(args.split())  # normalise whitespace
    set_gradle_prop(path, "org.gradle.jvmargs", args)
    return args


# ── recommendations ───────────────────────────────────────────────────────────

@dataclass
class Rec:
    id: str
    title: str
    reason: str
    action: str
    apply: Callable[[], Optional[bool]]


def build_recs(info: JavaInfo) -> list[Rec]:
    recs: list[Rec] = []
    props_path = info.gradle_props_path
    jdk = info.gradle_java_version or info.java_version

    # Derived values
    # Heap: leave ~50% RAM for OS, file cache, and other processes; cap at 16 GB
    safe_heap_gb = min(16, max(2, int(info.ram_gb * 0.40)))
    # Workers: for CPU-bound compilation, N-2 so UI stays responsive; min 2
    ideal_workers = max(2, min(info.cpu_count - 2, 16))

    # ── 1. Daemon enable ──────────────────────────────────────────────────────
    if info.current_daemon is not True:
        def _apply_daemon():
            set_gradle_prop(props_path, "org.gradle.daemon", "true")
            set_gradle_prop(props_path, "org.gradle.daemon.idletimeout", "10800000")
            return True

        recs.append(Rec(
            id="daemon",
            title="Enable Gradle daemon",
            reason=(
                "The Gradle daemon keeps a warm JVM alive between builds, avoiding "
                "2–5 s of JVM startup and class-loading on every invocation. Daemon "
                "is the default since Gradle 3.0 but worth making explicit. The "
                "3-hour idle timeout (10800000 ms) suits a workday without leaking "
                "daemon processes overnight."
            ),
            action="Set org.gradle.daemon=true, org.gradle.daemon.idletimeout=10800000",
            apply=_apply_daemon,
        ))

    # ── 2. Parallel builds ────────────────────────────────────────────────────
    if info.current_parallel is not True:
        def _apply_parallel():
            set_gradle_prop(props_path, "org.gradle.parallel", "true")
            return True

        recs.append(Rec(
            id="parallel",
            title="Enable parallel project execution",
            reason=(
                "Gradle can execute independent subprojects in parallel across "
                f"your {info.cpu_count} CPUs. For multi-module builds this routinely "
                "halves build time. Safe for projects with correctly declared "
                "inter-project dependencies (which Gradle enforces)."
            ),
            action="Set org.gradle.parallel=true",
            apply=_apply_parallel,
        ))

    # ── 3. Task caching ───────────────────────────────────────────────────────
    if info.current_caching is not True:
        def _apply_caching():
            set_gradle_prop(props_path, "org.gradle.caching", "true")
            return True

        recs.append(Rec(
            id="caching",
            title="Enable Gradle build cache",
            reason=(
                "The build cache stores task outputs keyed by inputs. On a clean "
                "checkout or after a branch switch, tasks whose inputs haven't "
                "changed (tests, compilation of unchanged modules) are served from "
                "the cache instead of re-run. Local cache hits are nearly instant."
            ),
            action="Set org.gradle.caching=true",
            apply=_apply_caching,
        ))

    # ── 4. Configure-on-demand ────────────────────────────────────────────────
    if info.current_configure_on_demand is not True:
        def _apply_cod():
            set_gradle_prop(props_path, "org.gradle.configureondemand", "true")
            return True

        recs.append(Rec(
            id="configureondemand",
            title="Enable configure-on-demand",
            reason=(
                "With configure-on-demand, Gradle only configures subprojects that "
                "are actually needed for the requested tasks. In large multi-module "
                "builds this cuts configuration time significantly — only the "
                "relevant dependency graph is evaluated."
            ),
            action="Set org.gradle.configureondemand=true",
            apply=_apply_cod,
        ))

    # ── 5. Worker count ───────────────────────────────────────────────────────
    if info.current_workers is None or info.current_workers < ideal_workers - 2:
        def _apply_workers():
            set_gradle_prop(props_path, "org.gradle.workers.max", str(ideal_workers))
            return True

        current_str = str(info.current_workers) if info.current_workers else "default (# CPUs)"
        recs.append(Rec(
            id="workers",
            title=f"Set worker parallelism: {current_str} → {ideal_workers}",
            reason=(
                f"You have {info.cpu_count} CPUs. Setting workers.max={ideal_workers} "
                f"(CPUs - 2) maximises compilation parallelism while leaving 2 CPUs "
                f"free for IDE, browser, and OS work. Without this, Gradle defaults "
                f"to all CPUs, which can cause UI stutter during heavy builds."
            ),
            action=f"Set org.gradle.workers.max={ideal_workers}",
            apply=_apply_workers,
        ))

    # ── 6. JVM heap (Xmx) ────────────────────────────────────────────────────
    target_xmx_mb = safe_heap_gb * 1024
    current_xmx = info.current_xmx_mb or 0
    if current_xmx < target_xmx_mb // 2:   # only recommend if less than half of target
        def _apply_heap():
            current = info.current_jvmargs or ""
            if "-Xmx" in current:
                new = re.sub(r"-Xmx\S+", f"-Xmx{safe_heap_gb}g", current)
            else:
                new = current + f" -Xmx{safe_heap_gb}g"
            new = new.strip()
            set_gradle_prop(props_path, "org.gradle.jvmargs", new)
            # Update info so later recs can read current_jvmargs
            info.current_jvmargs = new
            return True

        current_str = f"{current_xmx} MB" if current_xmx else "default (~512 MB)"
        recs.append(Rec(
            id="heap",
            title=f"Increase Gradle daemon heap: {current_str} → {safe_heap_gb} GB",
            reason=(
                f"The default Gradle daemon heap (~512 MB) is far too small for "
                f"Kotlin compilation, annotation processing, and large dependency "
                f"graphs. With {info.ram_gb:.0f} GB RAM, allocating {safe_heap_gb} GB "
                f"(40% of RAM) to the Gradle daemon eliminates GC pauses during "
                f"builds and prevents out-of-memory crashes on large modules."
            ),
            action=f"Set -Xmx{safe_heap_gb}g in org.gradle.jvmargs",
            apply=_apply_heap,
        ))

    # ── 7. GC selection ───────────────────────────────────────────────────────
    current_gc = info.current_gc
    if jdk >= 21:
        target_gc_flag = "-XX:+UseZGC -XX:+ZGenerational"
        target_gc_name = "ZGC (Generational, JDK 21+)"
        already_good = current_gc == "UseZGC" and "ZGenerational" in info.current_jvmargs
    elif jdk >= 11:
        target_gc_flag = "-XX:+UseZGC"
        target_gc_name = "ZGC (JDK 11+)"
        already_good = current_gc == "UseZGC"
    else:
        target_gc_flag = ""
        already_good = True  # nothing better available; skip

    if target_gc_flag and not already_good:
        def _apply_gc(flag=target_gc_flag):
            current = info.current_jvmargs or ""
            # Remove any existing GC flag
            new = re.sub(r"-XX:[+-]Use(?:ZGC|ShenandoahGC|G1GC|ParallelGC)", "", current)
            new = re.sub(r"-XX:[+-]ZGenerational\b", "", new)
            new = (new.strip() + " " + flag).strip()
            set_gradle_prop(props_path, "org.gradle.jvmargs", new)
            info.current_jvmargs = new
            return True

        gc_reason = {
            "UseZGC": (
                f"ZGC (JDK {jdk}) is a concurrent garbage collector with <1ms pause "
                f"times regardless of heap size. For a {safe_heap_gb} GB Gradle daemon "
                f"heap, G1GC (the default) pauses for 50–500ms during major GCs — "
                f"you see this as Gradle freezing mid-build. ZGC eliminates those "
                f"pauses entirely, at the cost of slightly higher memory overhead (~15%)."
            ),
            "UseZGC + ZGenerational": (
                f"Generational ZGC (default in JDK 23+) achieves 10% better throughput "
                f"than non-generational ZGC and uncommits unused heap back to the OS by "
                f"default. For a {safe_heap_gb} GB daemon heap with idle periods between "
                f"builds, this means other JVMs (IDE, app servers) get that memory back "
                f"without restarting Gradle."
            ),
        }.get(target_gc_name.split(" (")[0], "")

        recs.append(Rec(
            id="gc",
            title=f"Switch Gradle daemon GC: {current_gc or 'G1GC (default)'} → {target_gc_name}",
            reason=gc_reason or f"Use {target_gc_name} for lower GC pause latency.",
            action=f"Add {target_gc_flag} to org.gradle.jvmargs (remove existing GC flags)",
            apply=_apply_gc,
        ))

    # ── 8. ZGC heap uncommit delay ────────────────────────────────────────────
    is_using_zgc = (
        info.current_gc == "UseZGC"
        or (target_gc_flag and "UseZGC" in target_gc_flag)
    )
    # Only suggest if ZGC is already present or we just recommended it
    zgc_planned = "gc" in [r.id for r in recs] and "UseZGC" in target_gc_flag
    if is_using_zgc or zgc_planned:
        if "ZUncommitDelay" not in info.current_jvmargs:
            def _apply_uncommit():
                current = info.current_jvmargs or ""
                new = (current.strip() + " -XX:ZUncommitDelay=60").strip()
                set_gradle_prop(props_path, "org.gradle.jvmargs", new)
                info.current_jvmargs = new
                return True

            recs.append(Rec(
                id="zgc_uncommit",
                title="Set ZGC heap uncommit delay to 60 s",
                reason=(
                    "ZGC returns unused heap to the OS after ZUncommitDelay seconds "
                    "of inactivity (default: 300 s). With a 5-minute idle window, "
                    "the Gradle daemon holds onto gigabytes of unused heap while you "
                    "read a PR or context-switch. 60 s means idle daemons release "
                    "memory quickly, benefiting your IDE and other running JVMs."
                ),
                action="Add -XX:ZUncommitDelay=60 to org.gradle.jvmargs",
                apply=_apply_uncommit,
            ))

    # ── 9. Transparent Huge Pages ─────────────────────────────────────────────
    if not info.current_has_thp:
        # Only meaningful if THP is enabled at the OS level
        thp_os = ""
        thp_file = Path("/sys/kernel/mm/transparent_hugepage/enabled")
        if thp_file.exists():
            raw = thp_file.read_text()
            import re as _re
            m = _re.search(r"\[(\w+)\]", raw)
            thp_os = m.group(1) if m else ""

        if thp_os in ("madvise", "always"):
            def _apply_thp():
                current = info.current_jvmargs or ""
                new = (current.strip() + " -XX:+UseTransparentHugePages").strip()
                set_gradle_prop(props_path, "org.gradle.jvmargs", new)
                info.current_jvmargs = new
                return True

            recs.append(Rec(
                id="thp",
                title="Add -XX:+UseTransparentHugePages to Gradle JVM args",
                reason=(
                    "Your OS has THP enabled (mode: " + thp_os + "). The JVM flag "
                    "tells the JVM to use madvise() to request 2 MB huge pages for "
                    "heap regions. This reduces TLB pressure — Meta production data "
                    "shows 20% of CPU cycles go to TLB misses on large JVM heaps "
                    "without THP. Effective with your OS-level THP=madvise setting."
                ),
                action="Add -XX:+UseTransparentHugePages to org.gradle.jvmargs",
                apply=_apply_thp,
            ))

    # ── 10. AlwaysPreTouch ────────────────────────────────────────────────────
    if not info.current_has_pretouch:
        def _apply_pretouch():
            current = info.current_jvmargs or ""
            new = (current.strip() + " -XX:+AlwaysPreTouch").strip()
            set_gradle_prop(props_path, "org.gradle.jvmargs", new)
            info.current_jvmargs = new
            return True

        recs.append(Rec(
            id="pretouch",
            title="Add -XX:+AlwaysPreTouch to Gradle JVM args",
            reason=(
                "AlwaysPreTouch faults the entire heap into physical memory at JVM "
                "startup. Without it, the OS page-faults each heap page on first "
                "write, adding latency throughout the build. With it, all faults "
                "happen at daemon start (before your build begins) and builds run "
                "faster with no runtime page-fault interruptions. The daemon startup "
                f"cost is ~0.5–2 s for a {safe_heap_gb} GB heap."
            ),
            action="Add -XX:+AlwaysPreTouch to org.gradle.jvmargs",
            apply=_apply_pretouch,
        ))

    # ── 11. Code cache ────────────────────────────────────────────────────────
    if not info.current_has_code_cache:
        def _apply_code_cache():
            current = info.current_jvmargs or ""
            new = (current.strip() + " -XX:ReservedCodeCacheSize=512m").strip()
            set_gradle_prop(props_path, "org.gradle.jvmargs", new)
            info.current_jvmargs = new
            return True

        recs.append(Rec(
            id="code_cache",
            title="Increase JIT code cache to 512 MB",
            reason=(
                "The default JIT code cache is 240 MB. Gradle builds that compile "
                "large Kotlin or Java codebases frequently exhaust it, causing the "
                "JIT to flush compiled code and fall back to interpreting — visible "
                "as a sudden build slowdown. 512 MB comfortably fits the compiled "
                "methods from a large multi-module Kotlin project."
            ),
            action="Add -XX:ReservedCodeCacheSize=512m to org.gradle.jvmargs",
            apply=_apply_code_cache,
        ))

    # ── 12. Kotlin daemon heap ────────────────────────────────────────────────
    kotlin_daemon_flag = "-Dkotlin.daemon.jvm.options="
    has_kotlin_daemon = kotlin_daemon_flag in info.current_jvmargs
    if not has_kotlin_daemon:
        def _apply_kotlin_daemon():
            current = info.current_jvmargs or ""
            kotlin_opts = '-Dkotlin.daemon.jvm.options="-Xmx2g -XX:ReservedCodeCacheSize=320m"'
            new = (current.strip() + " " + kotlin_opts).strip()
            set_gradle_prop(props_path, "org.gradle.jvmargs", new)
            info.current_jvmargs = new
            return True

        recs.append(Rec(
            id="kotlin_daemon",
            title="Set Kotlin daemon JVM options (heap + code cache)",
            reason=(
                "Kotlin compilation runs in a separate Kotlin daemon process. Without "
                "explicit settings it defaults to 700 MB heap, which causes GC pauses "
                "and OOM errors on large Kotlin modules. 2 GB heap eliminates "
                "Kotlin-daemon-induced build pauses. 320 MB code cache prevents JIT "
                "flush in the Kotlin compiler itself."
            ),
            action='Add -Dkotlin.daemon.jvm.options="-Xmx2g -XX:ReservedCodeCacheSize=320m" to org.gradle.jvmargs',
            apply=_apply_kotlin_daemon,
        ))

    return recs


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    print(bold("\n╔══════════════════════════════╗"))
    print(bold("║   JVM / Gradle Optimizer     ║"))
    print(bold("╚══════════════════════════════╝"))
    print("Inspects your JVM and Gradle configuration and proposes performance settings.")
    print(f"Writes to: {Path.home() / '.gradle' / 'gradle.properties'}")
    print("No sudo required.\n")

    print("Detecting Java and Gradle configuration...")
    info = detect()
    print_summary(info)

    recs = build_recs(info)

    if not recs:
        print(green("\nNo optimizations needed — your Gradle configuration is already solid."))
        return

    header(f"Recommendations  ({len(recs)} found)")

    applied = skipped = failed = 0

    for i, rec in enumerate(recs, 1):
        print(f"\n{'─' * 64}")
        print(f"{bold(f'[{i}/{len(recs)}]')}  {bold(rec.title)}")
        print()
        print(wrap(rec.reason))
        print(f"\n  {yellow('Action:')} {rec.action}")

        if not ask("\nApply?"):
            print(yellow("  Skipped."))
            skipped += 1
            continue

        print()
        result = rec.apply()
        if result is False:
            print(red(f"  ✗ Failed: {rec.title}"))
            failed += 1
        else:
            print(green(f"  ✓ Done: {rec.title}"))
            applied += 1

    print(f"\n{'═' * 64}")
    print(bold(f"Summary:  {green(str(applied))} applied  "
               f"{yellow(str(skipped))} skipped  "
               f"{red(str(failed)) if failed else str(failed)} failed"))

    if applied > 0:
        props_path = info.gradle_props_path
        print(f"\n{yellow('Updated:')} {props_path}")
        print()
        print("Current jvmargs:")
        jvmargs = parse_gradle_props(props_path).get("org.gradle.jvmargs", "(none)")
        # Pretty-print long jvmargs
        flags = jvmargs.split()
        for f in flags:
            print(f"  {cyan(f)}")

        print(f"\n{dim('Tip:')} Run `gradle --stop` to restart daemons with the new settings.")
        print(dim("     New settings take effect on the next Gradle invocation."))


if __name__ == "__main__":
    main()
