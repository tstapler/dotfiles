#!/usr/bin/env python3
"""Shared host-network discovery helpers.

Runs on the Docker host (not inside a container) since only the host has a
real view of the LAN/WAN path. Skips VPN/tunnel interfaces so a split-tunnel
VPN's virtual default route doesn't get mistaken for the real gateway.
"""
import platform
import re
import subprocess
import sys

TUNNEL_PREFIXES = ("utun", "ipsec", "ppp", "awdl", "llw", "tun", "wg", "tailscale")
IP_RE = re.compile(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})")


def _is_tunnel_iface(iface):
    return any(iface.startswith(p) for p in TUNNEL_PREFIXES)


def get_default_route():
    """Return (gateway_ip, interface) for the real (non-tunnel) default route."""
    system = platform.system().lower()

    if system == "darwin":
        try:
            output = subprocess.check_output(["netstat", "-nr", "-f", "inet"]).decode()
            for line in output.splitlines():
                parts = line.split()
                if len(parts) >= 4 and parts[0] == "default" and not _is_tunnel_iface(parts[3]):
                    return parts[1], parts[3]
        except Exception as e:
            print(f"net_discovery: default route lookup failed: {e}", file=sys.stderr)
    elif system == "linux":
        try:
            output = subprocess.check_output(["ip", "route"]).decode()
            for line in output.splitlines():
                parts = line.split()
                if parts and parts[0] == "default" and "dev" in parts:
                    iface = parts[parts.index("dev") + 1]
                    if not _is_tunnel_iface(iface):
                        return parts[2], iface
        except Exception as e:
            print(f"net_discovery: default route lookup failed: {e}", file=sys.stderr)
    else:
        print(f"net_discovery: unsupported platform {system!r}", file=sys.stderr)

    return None, None


def get_gateway_ip():
    gateway, _ = get_default_route()
    if gateway is None:
        print(
            "net_discovery: gateway discovery failed, falling back to 192.168.1.1",
            file=sys.stderr,
        )
        return "192.168.1.1"
    return gateway


def is_private(ip):
    octets = [int(o) for o in ip.split(".")]
    return (
        octets[0] == 10
        or (octets[0] == 172 and 16 <= octets[1] <= 31)
        or (octets[0] == 192 and octets[1] == 168)
        or octets[0] == 127
    )


def discover_isp_hops(target="8.8.8.8", max_hops=8, timeout=1):
    """Traceroute toward `target` via the real (non-tunnel) interface and
    return the public-IP hops beyond the LAN gateway (i.e. ISP infrastructure).
    """
    _, iface = get_default_route()
    if not iface:
        return []

    cmd = ["traceroute", "-n", "-i", iface, "-m", str(max_hops), "-w", str(timeout), "-q", "1", target]
    try:
        output = subprocess.check_output(
            cmd, stderr=subprocess.DEVNULL, timeout=max_hops * timeout + 10
        ).decode()
    except Exception as e:
        print(f"net_discovery: traceroute failed: {e}", file=sys.stderr)
        return []

    hops = []
    seen = set()
    for line in output.splitlines()[1:]:
        match = IP_RE.search(line)
        if not match:
            continue
        ip = match.group(1)
        if ip in seen or is_private(ip):
            continue
        seen.add(ip)
        hops.append(ip)
    return hops


if __name__ == "__main__":
    gw, iface = get_default_route()
    print(f"Gateway: {gw} (via {iface})")
    print(f"ISP hops: {discover_isp_hops()}")
