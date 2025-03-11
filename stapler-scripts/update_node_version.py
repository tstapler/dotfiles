import urllib.request
import json
from datetime import datetime
import re

def get_latest_lts_version():
    url = 'https://nodejs.org/download/release/index.json'
    with urllib.request.urlopen(url) as response:
        data = json.load(response)
    
    # Filter LTS releases and parse semantic versions
    lts_versions = []
    for release in data:
        if release['lts']:
            version_str = release['version'].lstrip('v')
            # Parse semver components as integers for correct numeric comparison
            major, minor, patch = map(int, version_str.split('.')[0:3])
            lts_versions.append((major, minor, patch, version_str))
    
    if not lts_versions:
        raise ValueError("No LTS versions found in Node.js releases")
    
    # Sort by semantic version descending and get latest
    lts_versions.sort(reverse=True)
    latest = lts_versions[0][3]
    
    return latest

def update_tool_versions(new_version):
    file_path = '.tool-versions'
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Find and replace nodejs version
    updated = False
    for i, line in enumerate(lines):
        if line.startswith('nodejs '):
            lines[i] = f'nodejs {new_version}\n'
            updated = True
            break
    
    if not updated:
        raise ValueError("nodejs entry not found in .tool-versions")
    
    with open(file_path, 'w') as f:
        f.writelines(lines)

if __name__ == '__main__':
    try:
        latest_version = get_latest_lts_version()
        print(f"Latest Node.js LTS version: {latest_version}")
        update_tool_versions(latest_version)
        print("Successfully updated .tool-versions file")
    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)
