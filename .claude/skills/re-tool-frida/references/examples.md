# Worked Examples

## Core Hook: Network Payload Capture

```python
# hook-network.py
import frida, sys, os, time

SESSION_DIR = os.environ.get('SESSION_DIR', '/tmp/re-work/target')
os.makedirs(f'{SESSION_DIR}/captures', exist_ok=True)
capture_file = open(f'{SESSION_DIR}/captures/session-{int(time.time())}.bin', 'wb')

SCRIPT = """
const ws2 = Process.getModuleByName("ws2_32.dll");

Interceptor.attach(ws2.getExportByName("send"), {
    onEnter(args) {
        const len = args[2].toInt32();
        const buf = args[1].readByteArray(Math.min(len, 4096));
        send({direction: "send", sock: args[0].toInt32(), len}, buf);
    }
});

Interceptor.attach(ws2.getExportByName("recv"), {
    onEnter(args) {
        this.buf = args[1]; this.maxlen = args[2].toInt32(); this.sock = args[0].toInt32();
    },
    onLeave(retval) {
        const len = retval.toInt32();
        if (len > 0)
            send({direction: "recv", sock: this.sock, len}, this.buf.readByteArray(len));
    }
});
console.log("[frida] hooks installed");
"""

def on_message(msg, data):
    if msg.get('type') == 'send' and data:
        d = msg['payload']
        print(f"[{d['direction']}] sock={d['sock']} len={d['len']}")
        print("  " + data[:32].hex() + ("..." if len(data) > 32 else ""))
        capture_file.write(data)
        capture_file.flush()

# Connect via gadget
device = frida.get_device_manager().add_remote_device('127.0.0.1:27042')
session = device.attach('target.exe')
script = session.create_script(SCRIPT)
script.on('message', on_message)
script.load()
print(f"[frida] capturing to {SESSION_DIR}/captures/")
sys.stdin.read()
```

## Output Template

```markdown
# Frida Hook Results: <target>

## Hooks Deployed
| Target | Trigger |

## Captures
| Session | Direction | Packets | Bytes | File |

## Protocol Observations
- First 4 bytes: `52 41 56 4E` ("RAVN") — likely magic
- Byte 5 = message type (values: 0x01, 0x02, 0x10)

## Raw Excerpts (32 bytes max each)

## Open Questions
- [ ] Is length inclusive or exclusive of header?
```
