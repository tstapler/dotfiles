# USB / HID Capture

For hardware device protocols over USB:

```bash
# Load usbmon kernel module
sudo modprobe usbmon

# Grant capture permissions (or run as root)
sudo setfacl -m u:$USER:r /dev/usbmon*

# Find USB device bus number
lsusb | grep -i "scanner\|device-name"
# e.g. "Bus 001 Device 004" → capture on usbmon1

# Capture USB traffic
sudo tcpdump -i usbmon1 -w $SESSION_DIR/captures/usb-session.pcap

# In Wireshark/tshark: filter by device address
tshark -r usb-session.pcap -Y "usb.device_address==4" \
  -T fields -e usb.capdata 2>/dev/null | tr -d ':' | xxd -r -p \
  > $SESSION_DIR/captures/usb-payload.bin

# For HID devices: simpler — read directly
xxd /dev/hidraw0 | head -40
```
