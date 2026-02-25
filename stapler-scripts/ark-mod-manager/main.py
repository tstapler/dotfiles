import json
import os
import shutil
import re
import argparse
import glob
from datetime import datetime
import diff_utils

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MAPPING_FILE = os.path.join(SCRIPT_DIR, "mod_mapping.json")
CONFIGS_FILE = os.path.join(SCRIPT_DIR, "mod_configs.json")
PRESETS_FILE = os.path.join(SCRIPT_DIR, "tuning_presets.json")
BACKUP_DIR = os.path.join(SCRIPT_DIR, ".backups")

STEAM_APPS = os.path.expanduser("~/.local/share/Steam/steamapps/common")
ARK_ROOT = os.path.join(STEAM_APPS, "ARK Survival Ascended")
ARK_CONFIG_DIR = os.path.join(ARK_ROOT, "ShooterGame/Saved/Config/Windows")
GUS_PATH = os.path.join(ARK_CONFIG_DIR, "GameUserSettings.ini")
GAME_INI_PATH = os.path.join(ARK_CONFIG_DIR, "Game.ini")
MODS_DIR = os.path.join(ARK_ROOT, "ShooterGame/Binaries/Win64/ShooterGame/Mods/83374")

def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, 'r') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)

def perform_backup(file_path):
    if not os.path.exists(file_path):
        print(f"Warning: File to backup not found: {file_path}")
        return False

    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

    filename = os.path.basename(file_path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{filename}.{timestamp}.bak"
    backup_path = os.path.join(BACKUP_DIR, backup_name)

    try:
        shutil.copy2(file_path, backup_path)
        print(f"Backed up {filename} to {backup_path}")
    except Exception as e:
        print(f"Error creating backup: {e}")
        return False

    try:
        backups = sorted(glob.glob(os.path.join(BACKUP_DIR, f"{filename}.*.bak")))
        if len(backups) > 50:
            to_delete = backups[:-50]
            for old_backup in to_delete:
                os.remove(old_backup)
                print(f"Rotated (deleted) old backup: {os.path.basename(old_backup)}")
    except Exception as e:
        print(f"Error rotating backups: {e}")

    return True

def get_active_mods(config_content):
    match = re.search(r"ActiveMods=([0-9,]+)", config_content)
    if match:
        return match.group(1).split(",")
    return []

def get_installed_mod_ids():
    if not os.path.exists(MODS_DIR):
        return []
    ids = []
    for item in os.listdir(MODS_DIR):
        match = re.match(r"^(\d+)_", item)
        if match:
            ids.append(match.group(1))
    return list(set(ids))

def get_mod_info(mod_id, mapping):
    info = mapping.get(mod_id)
    if isinstance(info, str):
        return {"name": info, "url": ""}
    elif isinstance(info, dict):
        return info
    return {"name": "Unknown Mod", "url": ""}

def list_mods(active_mods, mapping, show_all=False):
    configs = load_json(CONFIGS_FILE)
    installed_ids = get_installed_mod_ids()
    
    print(f"Mod Status Report:")
    print(f"  Active: {len(active_mods)}")
    print(f"  Installed: {len(installed_ids)}")
    print("-" * 30)

    print("\n[ENABLED MODS]")
    for mod_id in active_mods:
        info = get_mod_info(mod_id, mapping)
        name = info["name"]
        config_status = " [Configured]" if mod_id in configs else ""
        print(f"  - {mod_id}: {name}{config_status}")

    if show_all:
        print("\n[DISABLED MODS (Installed but not active)]")
        inactive = sorted([m for m in installed_ids if m not in active_mods])
        if not inactive:
            print("  None")
        for mod_id in inactive:
            info = get_mod_info(mod_id, mapping)
            print(f"  - {mod_id}: {info['name']}")

def tag_mod(mod_id, name, mapping):
    info = get_mod_info(mod_id, mapping)
    info["name"] = name
    mapping[mod_id] = info
    save_json(MAPPING_FILE, mapping)
    print(f"Mapped {mod_id} to '{name}'")

def scan_local_mods(mapping):
    if not os.path.exists(MODS_DIR):
        print(f"Mods directory not found: {MODS_DIR}")
        return

    print(f"Scanning mods in {MODS_DIR}...")
    found_count = 0
    
    for item in os.listdir(MODS_DIR):
        mod_dir = os.path.join(MODS_DIR, item)
        if not os.path.isdir(mod_dir):
            continue
        match = re.match(r"^(\d+)_", item)
        if not match:
            continue
        
        mod_id = match.group(1)
        uplugin_files = glob.glob(os.path.join(mod_dir, "**", "*.uplugin"), recursive=True)
        
        if uplugin_files:
            try:
                with open(uplugin_files[0], 'r', encoding='utf-8', errors='ignore') as f:
                    data = json.load(f)
                    friendly_name = data.get("FriendlyName")
                    url = data.get("MarketplaceURL", "")
                    
                    if friendly_name:
                        current = get_mod_info(mod_id, mapping)
                        if current["name"] == "Unknown Mod" or current["name"] != friendly_name or (url and not current["url"]):
                            mapping[mod_id] = {
                                "name": friendly_name,
                                "url": url
                            }
                            found_count += 1
                            print(f"Updated {mod_id}: {friendly_name}")
            except Exception as e:
                print(f"Error parsing {uplugin_files[0]}: {e}")

    save_json(MAPPING_FILE, mapping)
    print(f"Scan complete. Updated {found_count} mods.")

def show_mod_info(mod_id, mapping):
    info = get_mod_info(mod_id, mapping)
    print(f"Mod ID:   {mod_id}")
    print(f"Name:     {info['name']}")
    if info['url']:
        print(f"URL:      {info['url']}")
    else:
        print("URL:      (Not found in local metadata)")
    
    configs = load_json(CONFIGS_FILE)
    if mod_id in configs:
        print("\nConfiguration:")
        print(json.dumps(configs[mod_id], indent=4))
    else:
        print("\nConfiguration: None set locally.")

def set_ini_value(content, section, key, value):
    escaped_section = re.escape(section)
    section_pattern = re.compile(fr"^\[{escaped_section}\]", re.MULTILINE)
    
    if not section_pattern.search(content):
        return content + f"\n[{section}]\n{key}={value}\n"
    
    lines = content.splitlines()
    new_lines = []
    in_section = False
    key_found = False
    
    for line in lines:
        strip_line = line.strip()
        if strip_line.startswith("[") and strip_line.endswith("]"):
            if in_section and not key_found:
                new_lines.append(f"{key}={value}")
                key_found = True
            
            if strip_line == f"[{section}]":
                in_section = True
            else:
                in_section = False
        
        if in_section:
            if "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                if k.lower() == key.lower():
                    if v.strip() != str(value):
                        print(f"  Updating {key}: {v.strip()} -> {value}")
                    new_lines.append(f"{key}={value}")
                    key_found = True
                    continue
        
        new_lines.append(line)
        
    if in_section and not key_found:
        print(f"  Adding key {key}={value}")
        new_lines.append(f"{key}={value}")
        
    return "\n".join(new_lines)

def apply_tuning(profile_name):
    presets = load_json(PRESETS_FILE)
    if profile_name not in presets:
        print(f"Error: Profile '{profile_name}' not found in {PRESETS_FILE}")
        return

    print(f"Applying Tuning Profile: '{profile_name}'...")
    profile = presets[profile_name]
    
    if "GUS" in profile and os.path.exists(GUS_PATH):
        perform_backup(GUS_PATH)
        with open(GUS_PATH, 'r') as f:
            content = f.read()
        changes_made = False
        for section, settings in profile["GUS"].items():
            for key, value in settings.items():
                new_content = set_ini_value(content, section, key, value)
                if new_content != content:
                    content = new_content
                    changes_made = True
        if changes_made:
            with open(GUS_PATH, 'w') as f:
                f.write(content)
            print("Updated GameUserSettings.ini")
        else:
            print("GameUserSettings.ini is already optimized.")
    
    if "Game" in profile and os.path.exists(GAME_INI_PATH):
        perform_backup(GAME_INI_PATH)
        with open(GAME_INI_PATH, 'r') as f:
            content = f.read()
        changes_made = False
        for section, settings in profile["Game"].items():
            for key, value in settings.items():
                new_content = set_ini_value(content, section, key, value)
                if new_content != content:
                    content = new_content
                    changes_made = True
        if changes_made:
            with open(GAME_INI_PATH, 'w') as f:
                f.write(content)
            print("Updated Game.ini")
        else:
            print("Game.ini is already optimized.")

def apply_configs(config_path, active_mods, configs):
    with open(config_path, 'r') as f:
        content = f.read()
    original_content = content
    updated_mods = list(active_mods)
    mods_added = False
    for mod_id in configs.keys():
        if mod_id not in updated_mods:
            print(f"Activating missing mod {mod_id}")
            updated_mods.append(mod_id)
            mods_added = True
    if mods_added:
        new_active_mods_line = "ActiveMods=" + ",".join(updated_mods)
        content = re.sub(r"ActiveMods=[0-9,]+", new_active_mods_line, content)
        active_mods = updated_mods

    for mod_id, sections in configs.items():
        for section_name, settings in sections.items():
            section_header = f"[{section_name}]"
            if section_header not in content:
                print(f"Adding section {section_header} for mod {mod_id}")
                content += f"\n{section_header}\n"
                for k, v in settings.items():
                    content += f"{k}={v}\n"
            else:
                pass
    if content != original_content:
        with open(config_path, 'w') as f:
            f.write(content)
        print("Updated configuration file.")
    else:
        print("Configuration is up to date.")

def parse_ini_value(content, key):
    match = re.search(f"^{key}=(.*)", content, re.MULTILINE | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return "Default"

def show_status():
    print("=== Ark Survival Ascended: Server Status ===\n")
    if os.path.exists(GUS_PATH):
        with open(GUS_PATH, 'r') as f:
            gus_content = f.read()
        print("[Gameplay Rates]")
        print(f"  Taming Speed:       {parse_ini_value(gus_content, 'TamingSpeedMultiplier')}")
        print(f"  Harvest Amount:     {parse_ini_value(gus_content, 'HarvestAmountMultiplier')}")
        print(f"  XP Multiplier:      {parse_ini_value(gus_content, 'XPMultiplier')}")
        print(f"  Difficulty Offset:  {parse_ini_value(gus_content, 'DifficultyOffset')}")
    else:
        print("GameUserSettings.ini not found!")

    if os.path.exists(GAME_INI_PATH):
        with open(GAME_INI_PATH, 'r') as f:
            game_content = f.read()
        print("\n[Breeding & Maturation]")
        print(f"  Mating Interval:    {parse_ini_value(game_content, 'MatingIntervalMultiplier')}")
        print(f"  Egg Hatch Speed:    {parse_ini_value(game_content, 'EggHatchSpeedMultiplier')}")
        print(f"  Baby Mature Speed:  {parse_ini_value(game_content, 'BabyMatureSpeedMultiplier')}")
        print(f"  Cuddle Interval:    {parse_ini_value(game_content, 'BabyCuddleIntervalMultiplier')}")
    else:
        print("\nGame.ini not found!")

def run_diff(args):
    """
    Diff command implementation.
    """
    target_path = args.target_file
    
    if args.base_file:
        base_path = args.base_file
        print(f"Comparing BASE: {base_path} \n      VS\nTARGET: {target_path}")
    else:
        # Infer base file based on the target filename if possible, otherwise error
        target_name = os.path.basename(target_path).lower()
        if "gameusersettings" in target_name:
            base_path = GUS_PATH
        elif "game.ini" in target_name or "gameini" in target_name:
            base_path = GAME_INI_PATH
        else:
            print("Error: Could not infer base configuration type from target filename.")
            print("Please specify --base-file explicitly (e.g. path to your active Game.ini).")
            return

        print(f"Comparing CURRENT SYSTEM CONFIG ({base_path}) \n      VS\nTARGET: {target_path}")

    base_config = diff_utils.parse_ini_file(base_path)
    target_config = diff_utils.parse_ini_file(target_path)
    
    diff = diff_utils.diff_configs(base_config, target_config)
    
    if not diff:
        print("No differences found.")
        return

    # Print Diff
    print(f"\nDifferences found in {len(diff)} sections:")
    for section, items in diff.items():
        print(f"\n  [{section}]")
        for k, v in items.items():
            print(f"    {k} = {v}")

    # Save to Presets
    if args.save_as:
        profile_name = args.save_as
        presets = load_json(PRESETS_FILE)
        
        # Determine category (GUS vs Game)
        target_name = os.path.basename(target_path).lower()
        category = "GUS" if "gameusersettings" in target_name else "Game"
        
        if profile_name not in presets:
            presets[profile_name] = {}
            
        presets[profile_name][category] = diff
        save_json(PRESETS_FILE, presets)
        print(f"\nSaved differences to profile '{profile_name}' in {PRESETS_FILE}")
        print(f"You can apply this overlay using: python3 manage_mods.py tune --profile {profile_name}")

def main():
    parser = argparse.ArgumentParser(description="Manage Ark Survival Ascended Mods")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    list_parser = subparsers.add_parser("list", help="List active mods")
    list_parser.add_argument("--all", action="store_true", help="Show all installed mods")
    
    subparsers.add_parser("apply", help="Apply configurations")
    subparsers.add_parser("scan", help="Scan local mod files")
    subparsers.add_parser("status", help="Show server gameplay settings")
    
    tune_parser = subparsers.add_parser("tune", help="Apply optimal gameplay settings")
    tune_parser.add_argument("--profile", default="solo", help="Profile name from tuning_presets.json")
    
    tag_parser = subparsers.add_parser("tag", help="Map a mod ID to a name")
    tag_parser.add_argument("mod_id", help="Mod ID")
    tag_parser.add_argument("name", help="Mod Name")
    
    info_parser = subparsers.add_parser("info", help="Show details for a specific mod")
    info_parser.add_argument("mod_id", help="Mod ID")

    # New Diff Command
    diff_parser = subparsers.add_parser("diff", help="Compare INI files and create overlays")
    diff_parser.add_argument("target_file", help="The INI file to import/compare")
    diff_parser.add_argument("--base-file", help="The INI file to compare against (defaults to active system config)")
    diff_parser.add_argument("--save-as", help="Save the differences as a new tuning profile")
    
    args = parser.parse_args()
    
    mapping = load_json(MAPPING_FILE)
    configs = load_json(CONFIGS_FILE)

    if args.command == "tag":
        tag_mod(args.mod_id, args.name, mapping)
        return
    elif args.command == "scan":
        scan_local_mods(mapping)
        return
    elif args.command == "status":
        show_status()
        return
    elif args.command == "tune":
        apply_tuning(args.profile)
        return
    elif args.command == "info":
        show_mod_info(args.mod_id, mapping)
        return
    elif args.command == "diff":
        run_diff(args)
        return

    if not os.path.exists(GUS_PATH):
        print(f"Ark config file not found at {GUS_PATH}")
        return

    with open(GUS_PATH, 'r') as f:
        raw_content = f.read()

    active_mods = get_active_mods(raw_content)

    if args.command == "list":
        list_mods(active_mods, mapping, show_all=args.all)
    elif args.command == "apply" or args.command is None:
        if not perform_backup(GUS_PATH):
            return
        apply_configs(GUS_PATH, active_mods, configs)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()