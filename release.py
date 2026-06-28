import os
import sys
import subprocess
import re

def run_git_command(args, check=True):
    try:
        result = subprocess.run(["git"] + args, capture_output=True, text=True, check=check)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Git command failed: git {' '.join(args)}")
        print(f"Error output: {e.stderr}")
        if check:
            sys.exit(1)
        return None

def check_git_status():
    # Check if inside git repo
    if not os.path.exists(".git"):
        print("Error: .git directory not found. This script must be run from the root of a Git repository.")
        sys.exit(1)
        
    # Check current branch
    branch = run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
    print(f"Current Git branch: {branch}")
    
    # Check remote URL
    remote_url = run_git_command(["remote", "get-url", "origin"], check=False)
    if not remote_url:
        print("Error: No remote named 'origin' is configured.")
        sys.exit(1)
    print(f"Remote origin URL: {remote_url}")

    # Check if working directory is clean
    status = run_git_command(["status", "--porcelain"])
    if status:
        print("\nWarning: You have uncommitted changes in your repository:")
        print(status)
        confirm = input("\nDo you want to proceed anyway? (y/N): ").strip().lower()
        if confirm != 'y':
            print("Aborted.")
            sys.exit(0)
        print("\nProceeding. Note: If uncommitted changes conflict with remote changes, git pull might fail.")
        
    # Sync with remote before releasing to prevent rejected pushes
    print("\nSyncing with remote repository (fetching latest changes)...")
    pull_result = subprocess.run(["git", "pull", "--rebase", "origin", branch], capture_output=True, text=True)
    if pull_result.returncode != 0:
        print(f"\nWarning: Could not automatically pull from remote origin/{branch}.")
        print(f"Details: {pull_result.stderr.strip()}")
        print("Continuing anyway. You may face issues when pushing if your local branch is out of sync.")
    else:
        print("Repository successfully synced with remote.")
        
    return branch

def get_input(prompt, validator=None):
    while True:
        value = input(prompt).strip()
        if not value:
            print("Value cannot be empty.")
            continue
        if validator and not validator(value):
            continue
        return value

def validate_version(ver):
    # Matches simple version patterns like 1.0.0, v1.0.0, 1.0.0-beta, etc.
    clean_ver = ver.lstrip('v')
    if not re.match(r'^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$', clean_ver):
        print("Invalid version format. Please use Semantic Versioning format (e.g. 1.0.0 or 1.0.0-beta).")
        return False
    return True

def main():
    print("=" * 60)
    print("                 Alien Launcher Releaser")
    print("=" * 60)
    
    branch = check_git_status()
    
    # Get version
    version = get_input("\nEnter version to release (e.g., 1.0.1): ", validate_version)
    clean_version = version.lstrip('v')
    
    # Get changelog
    print("\nEnter changelog (type 'DONE' on a new line when finished):")
    changelog_lines = []
    while True:
        line = input()
        if line.strip() == "DONE":
            break
        changelog_lines.append(line)
    
    changelog = "\n".join(changelog_lines).strip()
    if not changelog:
        changelog = f"Release v{clean_version}"
        print(f"No changelog entered, using default: '{changelog}'")
        
    print("\nPreparing release files...")
    
    # Import prepare_release functions to modify the files
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))
    try:
        import prepare_release
    except ImportError:
        # If import fails, run it as a subprocess
        subprocess.run([sys.executable, "scripts/prepare_release.py", clean_version, changelog], check=True)
    else:
        prepare_release.update_version(clean_version)
        prepare_release.generate_update_json(clean_version, changelog)

    # Show git diff
    print("\n" + "-" * 50)
    print("File differences to be committed:")
    print("-" * 50)
    diff = run_git_command(["diff", "core/update_manager.py", "update.json"])
    if diff:
        print(diff)
    else:
        print("No changes detected (the version and changelog may be identical to current files).")
    print("-" * 50)
    
    # Confirm release
    confirm = input(f"\nDo you want to commit, tag, and push version v{clean_version} to GitHub? (y/N): ").strip().lower()
    if confirm != 'y':
        # Revert changes if aborted? Let's ask.
        revert = input("Discard local changes to update_manager.py and update.json? (y/N): ").strip().lower()
        if revert == 'y':
            run_git_command(["checkout", "core/update_manager.py"])
            if os.path.exists("update.json"):
                # check if update.json was untracked
                is_tracked = run_git_command(["ls-files", "update.json"], check=False)
                if is_tracked:
                    run_git_command(["checkout", "update.json"])
                else:
                    os.remove("update.json")
            print("Local changes discarded.")
        print("Aborted.")
        sys.exit(0)
        
    # Commit changes
    print("\nCommitting changes...")
    run_git_command(["add", "core/update_manager.py", "update.json"])
    run_git_command(["commit", "-m", f"Release v{clean_version}"])
    
    # Tag release
    tag_name = f"v{clean_version}"
    print(f"Creating Git tag {tag_name}...")
    # Delete tag locally if it already exists to prevent duplicate tag errors
    run_git_command(["tag", "-d", tag_name], check=False)
    run_git_command(["tag", tag_name])
    
    # Push changes
    print(f"Pushing commit to branch '{branch}' and tag '{tag_name}' to GitHub...")
    run_git_command(["push", "origin", branch])
    run_git_command(["push", "origin", tag_name, "--force"]) # force-push tag if it existed
    
    print("\n" + "=" * 60)
    print("SUCCESS: Release changes pushed to GitHub!")
    print(f"Version: v{clean_version}")
    print("GitHub Actions will now trigger automatically to build and release the launcher.")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(0)
