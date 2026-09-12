"""
Regression checks for the ssh-bastion-client config rendering.

Run directly: uv run test_ssh_bastion_client.py
"""

from deploys.ssh_bastion_client import (
    BastionConnection,
    escutcheon_toml,
    ssh_config_fragment,
)

CONN = BastionConnection(name="bastion-1", host="203.0.113.5", port="2222")


def test_ssh_config_fragment_has_expected_fields() -> None:
    fragment = ssh_config_fragment(CONN, key_path="/home/t/.ssh/id_ed25519_bastion")

    assert "Host bastion-1" in fragment
    assert "HostName 203.0.113.5" in fragment
    assert "Port 2222" in fragment
    assert "IdentityFile /home/t/.ssh/id_ed25519_bastion" in fragment


def test_escutcheon_toml_serializes_knock_sequence_as_json_array() -> None:
    toml = escutcheon_toml(
        CONN, knock_sequence=[1111, 2222, 3333], knock_proto="udp", knock_ttl_secs=300
    )

    assert 'host     = "203.0.113.5"' in toml
    assert "port     = 2222" in toml
    assert "sequence = [1111, 2222, 3333]" in toml
    assert 'proto    = "udp"' in toml
    assert "ttl_secs = 300" in toml


if __name__ == "__main__":
    tests = [value for key, value in list(globals().items()) if key.startswith("test_")]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"\n{len(tests)} checks passed")
