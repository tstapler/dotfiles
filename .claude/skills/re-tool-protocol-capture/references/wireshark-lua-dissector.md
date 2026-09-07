# Wireshark Lua Dissector (once structure is known)

```lua
-- minimal_dissector.lua
-- Load: tshark -X lua_script:minimal_dissector.lua -r session.pcap
local proto = Proto("myproto", "My Protocol")

local fields = {
    magic      = ProtoField.uint32("myproto.magic",   "Magic",   base.HEX),
    length     = ProtoField.uint32("myproto.length",  "Length",  base.DEC),
    msg_type   = ProtoField.uint8 ("myproto.type",    "Type",    base.HEX),
    payload    = ProtoField.bytes ("myproto.payload", "Payload"),
}
proto.fields = fields

function proto.dissector(buf, pinfo, tree)
    if buf:len() < 9 then
        pinfo.desegment_len = DESEGMENT_ONE_MORE_SEGMENT
        return
    end
    local payload_len = buf(4, 4):le_uint()
    local total = 9 + payload_len
    if buf:len() < total then
        pinfo.desegment_len = total - buf:len()
        return
    end
    pinfo.cols.protocol = "MYPROTO"
    local t = tree:add(proto, buf(0, total))
    t:add_le(fields.magic,    buf(0, 4))
    t:add_le(fields.length,   buf(4, 4))
    t:add   (fields.msg_type, buf(8, 1))
    t:add   (fields.payload,  buf(9, payload_len))
end

-- Register on port (or use heuristic checker)
DissectorTable.get("tcp.port"):add(9999, proto)
```
