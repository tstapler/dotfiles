#!/usr/bin/env python3
"""Times DNS resolution for a single hostname and prints the result as
YAML matching fping's per-host output shape (host/cnt/loss/min/max/avg),
so prometheus_plugin.py's existing fping handling applies to it unchanged.

Invoked per-host by vaping's `command` probe type via
`python3 dns_probe.py <hostname>`. Resolution goes through the container's
configured system resolver (glibc getaddrinfo), so repeated lookups may hit
local resolver caching -- this measures end-to-end resolver latency as seen
by an application, not raw uncached upstream server latency.
"""
import socket
import sys
import time

COUNT = 5


def main():
    host = sys.argv[1]
    times = []
    for _ in range(COUNT):
        start = time.monotonic()
        try:
            socket.getaddrinfo(host, None)
            times.append((time.monotonic() - start) * 1000)
        except socket.gaierror:
            pass

    lost = COUNT - len(times)
    loss = lost / float(COUNT)

    print(f"host: {host}")
    print(f"cnt: {COUNT}")
    print(f"loss: {loss}")
    if times:
        print(f"min: {min(times)}")
        print(f"max: {max(times)}")
        print(f"avg: {sum(times) / len(times)}")


if __name__ == "__main__":
    main()
