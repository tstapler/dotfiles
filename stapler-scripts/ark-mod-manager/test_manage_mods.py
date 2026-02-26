import pytest
from unittest.mock import patch, mock_open, MagicMock
import manage_mods
import os
import json

# Sample Config Content
SAMPLE_CONFIG = """
[ServerSettings]
ActiveMods=12345,67890
"""

def test_get_active_mods():
    mods = manage_mods.get_active_mods(SAMPLE_CONFIG)
    assert mods == ["12345", "67890"]

@patch("manage_mods.load_json")
@patch("builtins.print")
def test_list_mods(mock_print, mock_load):
    mock_load.side_effect = [
        {"12345": "Mod A"}, # mapping
        {"12345": {"S": {"K": "V"}}} # configs
    ]
    manage_mods.list_mods(["12345", "67890"], {"12345": "Mod A"})
    # Verify print was called for both mods
    calls = [call[0][0] for call in mock_print.call_args_list]
    assert any("Mod A" in c for m in calls for c in [m])
    assert any("Unknown Mod" in c for m in calls for c in [m])

@patch("manage_mods.save_json")
def test_tag_mod(mock_save):
    mapping = {}
    manage_mods.tag_mod("111", "Name", mapping)
    assert mapping["111"] == "Name"
    mock_save.assert_called()

@patch("builtins.open", new_callable=mock_open, read_data=SAMPLE_CONFIG)
def test_apply_configs_adds_section(mock_file):
    configs = {
        "99999": {
            "NewModSection": {
                "SomeKey": "SomeValue"
            }
        }
    }
    # 99999 must be in active_mods for it to apply
    manage_mods.apply_configs("fake_path.ini", ["12345", "99999"], configs)
    
    handle = mock_file()
    written_content = handle.write.call_args[0][0]
    assert "[NewModSection]" in written_content
    assert "SomeKey=SomeValue" in written_content

@patch("builtins.open", new_callable=mock_open, read_data=SAMPLE_CONFIG)
def test_apply_configs_activates_missing_mod(mock_file):
    mod_id = "11111"
    configs = {
        mod_id: {
            "ModSection": {"Key": "Val"}
        }
    }
    
    manage_mods.apply_configs("fake_path.ini", ["12345", "67890"], configs)
    
    handle = mock_file()
    written_content = handle.write.call_args[0][0]
    assert f"ActiveMods=12345,67890,{mod_id}" in written_content