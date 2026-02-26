import os
import configparser
import json

def parse_ini_file(path):
    """
    Parses an INI file into a dictionary structure: {Section: {Key: Value}}.
    Keys and sections are stored as-is but comparisons should be case-insensitive.
    """
    if not os.path.exists(path):
        return {}
    
    config = {}
    current_section = None
    
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith(';') or line.startswith('#'):
                    continue
                
                if line.startswith('[') and line.endswith(']'):
                    current_section = line[1:-1]
                    if current_section not in config:
                        config[current_section] = {}
                    continue
                
                if '=' in line and current_section:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # Store with original casing, but we might need to normalize for diffing
                    config[current_section][key] = value
    except Exception as e:
        print(f"Error reading {path}: {e}")
        return {}

    return config

def diff_configs(base_config, target_config):
    """
    Compares target_config AGAINST base_config.
    Returns a dictionary of settings that are in target_config but different (or missing) in base_config.
    This is effectively the 'Overlay' or 'Patch' needed to transform Base into Target.
    """
    diff = {}
    
    # Normalize base for easier lookup (lowercase keys)
    base_lookup = {}
    for section, items in base_config.items():
        base_lookup[section.lower()] = {k.lower(): v for k, v in items.items()}

    for section, items in target_config.items():
        section_lower = section.lower()
        
        for key, value in items.items():
            key_lower = key.lower()
            
            # Check if this setting exists in base and is the same
            in_base = False
            if section_lower in base_lookup:
                if key_lower in base_lookup[section_lower]:
                    if base_lookup[section_lower][key_lower] == value:
                        in_base = True
            
            if not in_base:
                if section not in diff:
                    diff[section] = {}
                diff[section][key] = value
                
    return diff

def generate_preset_from_diff(diff_data, profile_name):
    """
    Converts a diff dictionary into the structure used by tuning_presets.json
    """
    # tuning_presets.json usually separates by "GUS" (GameUserSettings) and "Game"
    # We might need heuristics or user input to know which file the diff came from.
    # For now, we return the raw structure, and the caller (main.py) assigns it to the right file category.
    return diff_data
