# TLS Interception (Wine Targets)

Wine's `secur32.dll` calls the **host system's `libgnutls.so`** via a push/pull adapter.
This means `ecapture gnutls` intercepts Wine app TLS at the libgnutls layer — no proxy,
no certificate pinning bypass needed.

```bash
# Install ecapture (eBPF-based TLS capture)
# Arch: yay -S ecapture  OR  download from: https://github.com/gojue/ecapture/releases

# Capture TLS plaintext from Wine process
sudo ecapture gnutls --pid <wine-pid> \
  -w $SESSION_DIR/captures/tls-plaintext.pcap

# Alternatively, extract session keys and embed in pcapng
SSLKEYLOGFILE=$SESSION_DIR/captures/tls-keys.log \
  WINEPREFIX=~/.wine-target wine target.exe

# Embed keys into pcapng for self-contained sharing
editcap --inject-secrets tls,$SESSION_DIR/captures/tls-keys.log \
  session-001.pcap $SESSION_DIR/captures/session-tls.pcapng
```

Note: If target uses statically-linked BoringSSL (uncommon in Win32 apps), ecapture may
not intercept — use Frida hooks on the SSL_write/SSL_read functions instead.
