import os
import re
import json
import sys

def update_version(version):
    # Normalize version string (remove leading v if any)
    clean_version = version.strip().lstrip('v')
    
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    update_manager_path = os.path.join(project_root, "core", "update_manager.py")
    
    if not os.path.exists(update_manager_path):
        print(f"Error: Could not find update_manager.py at {update_manager_path}")
        sys.exit(1)
        
    with open(update_manager_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Pattern to match LAUNCHER_VERSION = "..."
    pattern = r'(LAUNCHER_VERSION\s*=\s*")[^"]+(")'
    new_content, count = re.subn(pattern, r'\g<1>' + clean_version + r'\g<2>', content)
    
    if count == 0:
        print("Warning: LAUNCHER_VERSION pattern not found in update_manager.py. Let's try to append or locate manually.")
        # Try a simpler replace if custom formatting is used
        if 'LAUNCHER_VERSION =' in content:
            # Simple replacement
            lines = content.splitlines()
            for i, line in enumerate(lines):
                if line.strip().startswith("LAUNCHER_VERSION"):
                    lines[i] = f'LAUNCHER_VERSION = "{clean_version}"'
                    break
            new_content = "\n".join(lines) + "\n"
        else:
            print("Error: Could not find LAUNCHER_VERSION variable in update_manager.py")
            sys.exit(1)
            
    with open(update_manager_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(new_content)
        
    print(f"Updated core/update_manager.py to version {clean_version}")
    return clean_version

def generate_update_json(clean_version, changelog):
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    update_json_path = os.path.join(project_root, "update.json")
    
    # Format changelog to handle literal \n
    formatted_changelog = changelog.replace('\\n', '\n')
    
    data = {
        "version": clean_version,
        "changelog": formatted_changelog,
        "download_url": f"https://github.com/GianCarlozxc/AlienLauncher/releases/download/v{clean_version}/Alien.Launcher.exe"
    }
    
    with open(update_json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        
    print(f"Generated update.json for version {clean_version}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python prepare_release.py <version> <changelog>")
        sys.exit(1)
        
    version_arg = sys.argv[1]
    changelog_arg = " ".join(sys.argv[2:])
    
    clean_ver = update_version(version_arg)
    generate_update_json(clean_ver, changelog_arg)
