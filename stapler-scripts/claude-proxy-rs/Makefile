BINARY=target/release/claude-proxy-rs
PLIST=com.claude-proxy-rs.plist
PLIST_DEST=$(HOME)/Library/LaunchAgents/$(PLIST)

.PHONY: build dev install start stop restart status logs test

build:
	cargo build --release

dev:
	PROXY_PORT=47001 cargo run

install: build
	cp $(BINARY) /usr/local/bin/claude-proxy-rs
	cp $(PLIST) $(PLIST_DEST)
	launchctl load $(PLIST_DEST)

start:
	launchctl load $(PLIST_DEST)

stop:
	launchctl unload $(PLIST_DEST)

restart: stop start

status:
	launchctl list | grep claude-proxy-rs

logs:
	tail -f /tmp/claude-proxy-rs.app.log

test:
	cargo test
