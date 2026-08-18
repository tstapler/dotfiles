#!/usr/bin/env python3
"""Renders config.yaml from config.yaml.template: substitutes the live
LAN gateway IP and injects freshly traceroute-discovered ISP hops.

Must run on the Docker host, not inside a container -- only the host has a
real view of the LAN/WAN path.
"""
from pathlib import Path

from net_discovery import discover_isp_hops, get_gateway_ip

TEMPLATE = Path(__file__).parent / "config.yaml.template"
OUTPUT = Path(__file__).parent / "config.yaml"

# Hosts already present in config.yaml.template's static lists -- don't
# duplicate them if traceroute happens to hit one along the way.
STATIC_HOSTS = {"8.8.8.8", "1.1.1.1", "208.67.222.222", "136.27.58.1"}


def render_hosts_block(hops):
    lines = []
    for i, ip in enumerate(hops, start=1):
        lines.append(f"          - host: {ip}")
        lines.append(f"            name: ISP hop {i}")
    return "\n".join(lines)


def main():
    gateway_ip = get_gateway_ip()
    hops = [ip for ip in discover_isp_hops() if ip not in STATIC_HOSTS and ip != gateway_ip]
    hosts_block = render_hosts_block(hops)

    text = TEMPLATE.read_text()
    text = text.replace("${GATEWAY_IP}", gateway_ip)
    text = text.replace("${TRACEROUTE_HOSTS}", hosts_block)
    OUTPUT.write_text(text)

    print(f"Gateway IP: {gateway_ip}")
    print(f"Discovered {len(hops)} ISP hop(s): {', '.join(hops) or 'none'}")


if __name__ == "__main__":
    main()
