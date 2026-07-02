import os
import sys
import json
import zipfile
import tempfile
import subprocess
import re
import requests
import hashlib
from concurrent.futures import ThreadPoolExecutor

def get_forge_version_from_file(minecraft_version, recommended=True):
    try:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(base_path, "available_forge_versions.txt")
        if os.path.exists(file_path):
            suffix = "-recommended" if recommended else "-latest"
            target_key = f"{minecraft_version}{suffix}"
            fallback_key = f"{minecraft_version}-latest"
            best_val = None
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("-"):
                        parts = line.strip().lstrip("- ").split(":")
                        if len(parts) == 2:
                            key = parts[0].strip()
                            val = parts[1].strip()
                            if key == target_key:
                                return val
                            if key == fallback_key:
                                best_val = val
            if best_val:
                return best_val
    except Exception:
        pass
    return None

def resolve_forge_version(minecraft_version, recommended=True):
    try:
        res = requests.get("https://files.minecraftforge.net/net/minecraftforge/forge/promotions_slim.json", timeout=5)
        if res.status_code == 200:
            data = res.json()
            promos = data.get("promos", {})
            suffix = "recommended" if recommended else "latest"
            key = f"{minecraft_version}-{suffix}"
            if key in promos:
                return promos[key]
            key_latest = f"{minecraft_version}-latest"
            if key_latest in promos:
                return promos[key_latest]
    except Exception:
        pass
        
    val = get_forge_version_from_file(minecraft_version, recommended)
    if val:
        return val
    return None

def resolve_neoforge_version(minecraft_version):
    try:
        res = requests.get("https://maven.neoforged.net/releases/net/neoforged/neoforge/maven-metadata.xml", timeout=5)
        if res.status_code == 200:
            xml_text = res.text
            versions = re.findall(r"<version>([^<]+)</version>", xml_text)
            
            parts = minecraft_version.split('.')
            if len(parts) >= 2:
                major = parts[1]
                minor = parts[2] if len(parts) > 2 else "0"
                prefix = f"{major}.{minor}."
                matches = [v for v in versions if v.startswith(prefix)]
                if matches:
                    from functools import cmp_to_key
                    matches.sort(key=cmp_to_key(compare_versions), reverse=True)
                    return matches[0]
    except Exception:
        pass
        
    parts = minecraft_version.split('.')
    if len(parts) >= 2:
        major = parts[1]
        minor = parts[2] if len(parts) > 2 else "0"
        return f"{major}.{minor}.50"
    return "21.1.58"

def maven_to_path(coordinate):
    parts = coordinate.split(':')
    if len(parts) < 3:
        return coordinate
    group = parts[0].replace('.', '/')
    artifact = parts[1]
    version = parts[2]
    classifier = parts[3] if len(parts) > 3 else ""
    ext = "jar"
    
    if '@' in version:
        version, ext = version.split('@', 1)
    if '@' in classifier:
        classifier, ext = classifier.split('@', 1)
    
    filename = f"{artifact}-{version}"
    if classifier:
        filename += f"-{classifier}"
    filename += f".{ext}"
    
    return f"{group}/{artifact}/{version}/{filename}"

def get_jar_main_class(jar_path):
    try:
        with zipfile.ZipFile(jar_path, 'r') as z:
            manifest = z.read("META-INF/MANIFEST.MF").decode("utf-8", errors="ignore")
            for line in manifest.splitlines():
                if line.lower().startswith("main-class:"):
                    return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return None

def download_file(url, path, expected_sha1=None, status_callback=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if status_callback:
        status_callback(f"Downloading {os.path.basename(path)}...")
    
    response = requests.get(url, timeout=30, stream=True)
    response.raise_for_status()
    
    sha1 = hashlib.sha1()
    with open(path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                sha1.update(chunk)
                
    if expected_sha1 and sha1.hexdigest() != expected_sha1:
        raise ValueError(f"Hash mismatch for {path}: expected {expected_sha1}, got {sha1.hexdigest()}")

def download_file_sha256(url, path, expected_sha256=None, status_callback=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if status_callback:
        status_callback(f"Downloading {os.path.basename(path)}...")
    
    response = requests.get(url, timeout=30, stream=True)
    response.raise_for_status()
    
    sha256 = hashlib.sha256()
    with open(path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                sha256.update(chunk)
                
    if expected_sha256 and sha256.hexdigest() != expected_sha256:
        raise ValueError(f"Hash mismatch for {path}: expected {expected_sha256}, got {sha256.hexdigest()}")

def download_parallel(jobs, max_workers=10, status_callback=None):
    def worker(job):
        url, path, sha = job
        try:
            download_file(url, path, sha, status_callback=None)
            return True
        except Exception as e:
            if status_callback:
                status_callback(f"Failed to download {url}: {e}")
            return False

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(worker, jobs))
    return all(results)

def compare_versions(v1, v2):
    def parse_version(v):
        parts = v.split('-')
        main_part = parts[0]
        main_segments = [int(s) if s.isdigit() else 0 for s in main_part.split('.')]
        is_pre = len(parts) > 1
        pre_idents = parts[1].split('.') if is_pre else []
        return main_segments, is_pre, pre_idents

    seg1, is_pre1, idents1 = parse_version(v1)
    seg2, is_pre2, idents2 = parse_version(v2)

    # Compare main segments
    for s1, s2 in zip(seg1, seg2):
        if s1 != s2:
            return 1 if s1 > s2 else -1
    if len(seg1) != len(seg2):
        return 1 if len(seg1) > len(seg2) else -1

    # Compare pre-release status
    if is_pre1 and not is_pre2:
        return -1
    if not is_pre1 and is_pre2:
        return 1
    if not is_pre1 and not is_pre2:
        return 0

    # Compare pre-release identifiers
    for id1, id2 in zip(idents1, idents2):
        if id1.isdigit() and id2.isdigit():
            n1, n2 = int(id1), int(id2)
            if n1 != n2:
                return 1 if n1 > n2 else -1
        else:
            if id1 != id2:
                return 1 if id1 > id2 else -1
    if len(idents1) != len(idents2):
        return 1 if len(idents1) > len(idents2) else -1
    return 0

def install_fabric_or_quilt(game_version, mc_dir, is_quilt=False, status_callback=None):
    loader_type = "Quilt" if is_quilt else "Fabric"
    if status_callback:
        status_callback(f"Resolving {loader_type} versions for {game_version}...")
        
    meta_url = (
        f"https://meta.quiltmc.org/v3/versions/loader/{game_version}"
        if is_quilt
        else f"https://meta.fabricmc.net/v2/versions/loader/{game_version}"
    )
    
    res = requests.get(meta_url, timeout=10)
    res.raise_for_status()
    loaders_json = res.json()
    
    if not isinstance(loaders_json, list) or not loaders_json:
        raise ValueError(f"No {loader_type} loader versions found for {game_version}")
        
    # Select latest version
    stables = [item for item in loaders_json if item.get("loader", {}).get("stable") is True]
    candidates = stables if stables else loaders_json
    
    def sort_key(item):
        from functools import cmp_to_key
        return cmp_to_key(compare_versions)(item.get("loader", {}).get("version", ""))
        
    candidates.sort(key=sort_key, reverse=True)
    loader_version = candidates[0]["loader"]["version"]
    
    if status_callback:
        status_callback(f"Resolved {loader_type} version: {loader_version}")
        
    # Fetch launcher profile JSON
    profile_url = (
        f"https://meta.quiltmc.org/v3/versions/loader/{game_version}/{loader_version}/profile/json"
        if is_quilt
        else f"https://meta.fabricmc.net/v2/versions/loader/{game_version}/{loader_version}/profile/json"
    )
    
    profile_res = requests.get(profile_url, timeout=10)
    profile_res.raise_for_status()
    profile_json = profile_res.json()
    
    profile_id = profile_json["id"]
    profile_dir = os.path.join(mc_dir, "versions", profile_id)
    os.makedirs(profile_dir, exist_ok=True)
    
    with open(os.path.join(profile_dir, f"{profile_id}.json"), "w", encoding="utf-8") as f:
        json.dump(profile_json, f, indent=4)
        
    # Download libraries
    default_maven = "https://maven.quiltmc.org/repository/release/" if is_quilt else "https://maven.fabricmc.net/"
    download_jobs = []
    libraries_dir = os.path.join(mc_dir, "libraries")
    
    for lib in profile_json.get("libraries", []):
        name = lib["name"]
        base_url = lib.get("url", default_maven)
        maven_path = maven_to_path(name)
        
        url = base_url + maven_path if base_url.endswith('/') else f"{base_url}/{maven_path}"
        dest_path = os.path.join(libraries_dir, maven_path.replace('/', os.sep))
        sha1 = lib.get("sha1")
        
        download_jobs.append((url, dest_path, sha1))
        
    if status_callback:
        status_callback(f"Downloading {len(download_jobs)} {loader_type} libraries...")
    download_parallel(download_jobs, status_callback=status_callback)
    
    if status_callback:
        status_callback(f"{loader_type} installed successfully: {profile_id}")
    return True, profile_id

def install_forge(game_version, loader_version, mc_dir, java_path="java", status_callback=None):
    raw_version = f"{game_version}-{loader_version}"
    forge_version_id = f"{game_version}-forge-{loader_version}"
    
    if status_callback:
        status_callback(f"Downloading Forge installer for version {raw_version}...")
        
    forge_installer_url = f"https://maven.minecraftforge.net/net/minecraftforge/forge/{raw_version}/forge-{raw_version}-installer.jar"
    
    with tempfile.TemporaryDirectory(prefix="launcher-forge-") as temp_dir:
        installer_path = os.path.join(temp_dir, "installer.jar")
        download_file(forge_installer_url, installer_path, status_callback=status_callback)
        
        # Read installer ZIP
        with zipfile.ZipFile(installer_path, "r") as z:
            install_profile_text = z.read("install_profile.json").decode("utf-8")
            version_data = json.loads(install_profile_text)
            
            # Extract client json
            client_json = None
            try:
                client_json = json.loads(z.read("version.json").decode("utf-8"))
            except Exception:
                if "versionInfo" in version_data:
                    client_json = version_data["versionInfo"]
                    
            if not client_json:
                raise ValueError("Could not find client json in Forge installer")
                
            client_json["id"] = forge_version_id
            
            # Extract client.lzma
            lzma_path = os.path.join(temp_dir, "client.lzma")
            try:
                with open(lzma_path, "wb") as lz_file:
                    lz_file.write(z.read("data/client.lzma"))
            except Exception:
                pass
                
            # Extract forge libraries
            forge_lib_dir = os.path.join(mc_dir, "libraries", "net", "minecraftforge", "forge", raw_version)
            os.makedirs(forge_lib_dir, exist_ok=True)
            
            zip_candidates = [
                (f"maven/net/minecraftforge/forge/{raw_version}/forge-{raw_version}-universal.jar", f"forge-{raw_version}-universal.jar"),
                (f"forge-{raw_version}-universal.jar", f"forge-{raw_version}.jar"),
                (f"maven/net/minecraftforge/forge/{raw_version}/forge-{raw_version}.jar", f"forge-{raw_version}.jar")
            ]
            for zip_path, dest_name in zip_candidates:
                try:
                    with open(os.path.join(forge_lib_dir, dest_name), "wb") as out_file:
                        out_file.write(z.read(zip_path))
                    if status_callback:
                        status_callback(f"Extracted {dest_name}")
                except Exception:
                    pass

        # Write version json
        forge_version_dir = os.path.join(mc_dir, "versions", forge_version_id)
        os.makedirs(forge_version_dir, exist_ok=True)
        with open(os.path.join(forge_version_dir, f"{forge_version_id}.json"), "w", encoding="utf-8") as f:
            json.dump(client_json, f, indent=4)
            
        # Download installer libraries
        libraries_dir = os.path.join(mc_dir, "libraries")
        download_jobs = []
        for lib in version_data.get("libraries", []):
            name = lib["name"]
            maven_path = maven_to_path(name)
            dest_path = os.path.join(libraries_dir, maven_path.replace('/', os.sep))
            
            url = None
            if "downloads" in lib and "artifact" in lib["downloads"]:
                url = lib["downloads"]["artifact"].get("url")
            if not url:
                base_url = lib.get("url", "https://libraries.minecraft.net")
                url = f"{base_url.rstrip('/')}/{maven_path}"
                
            sha1 = lib.get("downloads", {}).get("artifact", {}).get("sha1") or lib.get("sha1")
            if url.startswith("http"):
                download_jobs.append((url, dest_path, sha1))
                
        if status_callback:
            status_callback(f"Downloading {len(download_jobs)} installer libraries...")
        download_parallel(download_jobs, status_callback=status_callback)
        
        # Download client libraries
        client_download_jobs = []
        for lib in client_json.get("libraries", []):
            name = lib["name"]
            maven_path = maven_to_path(name)
            dest_path = os.path.join(libraries_dir, maven_path.replace('/', os.sep))
            if os.path.exists(dest_path):
                continue
                
            url = None
            if "downloads" in lib and "artifact" in lib["downloads"]:
                url = lib["downloads"]["artifact"].get("url")
            if not url:
                base_url = lib.get("url", "https://libraries.minecraft.net")
                url = f"{base_url.rstrip('/')}/{maven_path}"
                
            sha1 = lib.get("downloads", {}).get("artifact", {}).get("sha1") or lib.get("sha1")
            if url.startswith("http"):
                client_download_jobs.append((url, dest_path, sha1))
                
        if status_callback:
            status_callback(f"Downloading {len(client_download_jobs)} client libraries...")
        download_parallel(client_download_jobs, status_callback=status_callback)
        
        # Run processors
        processors = version_data.get("processors", [])
        if processors:
            if status_callback:
                status_callback(f"Running {len(processors)} Forge post-processors...")
                
            minecraft_jar = os.path.join(mc_dir, "versions", game_version, f"{game_version}.jar")
            
            argument_vars = {
                "{MINECRAFT_JAR}": minecraft_jar,
                "{INSTALLER}": installer_path,
                "{BINPATCH}": lzma_path,
                "{SIDE}": "client"
            }
            
            root_path = os.path.join(temp_dir, "root")
            os.makedirs(root_path, exist_ok=True)
            argument_vars["{ROOT}"] = root_path
            
            # Read variables from "data" in install_profile.json
            for key, val in version_data.get("data", {}).items():
                if "client" in val:
                    client_val = val["client"]
                    if client_val.startswith('[') and client_val.endswith(']'):
                        lib_name = client_val[1:-1]
                        resolved = os.path.join(libraries_dir, maven_to_path(lib_name).replace('/', os.sep))
                    else:
                        resolved = client_val
                    argument_vars[f"{{{key}}}"] = resolved
                    
            for idx, proc in enumerate(processors):
                sides = proc.get("sides", [])
                if sides and "client" not in sides:
                    continue
                    
                proc_jar_coord = proc["jar"]
                proc_jar_path = os.path.join(libraries_dir, maven_to_path(proc_jar_coord).replace('/', os.sep))
                
                classpath_parts = []
                for coord in proc.get("classpath", []):
                    classpath_parts.append(os.path.join(libraries_dir, maven_to_path(coord).replace('/', os.sep)))
                classpath_parts.append(proc_jar_path)
                
                classpath = os.path.pathsep.join(classpath_parts)
                main_class = get_jar_main_class(proc_jar_path)
                if not main_class:
                    raise ValueError(f"Could not find Main-Class for processor: {proc_jar_coord}")
                    
                args = []
                for arg in proc.get("args", []):
                    resolved_arg = arg
                    for key, val in argument_vars.items():
                        resolved_arg = resolved_arg.replace(key, val)
                    if resolved_arg.startswith('[') and resolved_arg.endswith(']'):
                        lib_name = resolved_arg[1:-1]
                        resolved_arg = os.path.join(libraries_dir, maven_to_path(lib_name).replace('/', os.sep))
                    args.append(resolved_arg)
                    
                cmd = [java_path, "-cp", classpath, main_class] + args
                if status_callback:
                    status_callback(f"Running processor {idx+1}/{len(processors)}: {proc_jar_coord}...")
                    
                startupinfo = None
                if sys.platform == "win32":
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    
                res = subprocess.run(cmd, cwd=root_path, startupinfo=startupinfo, capture_output=True, text=True)
                if res.returncode != 0:
                    raise RuntimeError(f"Processor failed: {res.stderr}")
                    
        # Copy vanilla jar if missing
        forge_jar = os.path.join(forge_version_dir, f"{forge_version_id}.jar")
        if not os.path.exists(forge_jar):
            vanilla_jar = os.path.join(mc_dir, "versions", game_version, f"{game_version}.jar")
            if os.path.exists(vanilla_jar):
                import shutil
                shutil.copy(vanilla_jar, forge_jar)
                
        if status_callback:
            status_callback(f"Forge installed successfully: {forge_version_id}")
        return True, forge_version_id

def install_neoforge(loader_version, mc_dir, java_path="java", status_callback=None):
    # Determine minecraft version from loader_version e.g. 21.1.58 -> 1.21.1
    parts = loader_version.split('.')
    if len(parts) >= 2:
        minecraft_version = f"1.{parts[0]}"
        # If parts[1] is not zero, append it
        if parts[1] != "0":
            minecraft_version += f".{parts[1]}"
    else:
        minecraft_version = "1.21"
        
    neoforge_version_id = f"neoforge-{loader_version}"
    
    if status_callback:
        status_callback(f"Downloading NeoForge installer for version {loader_version}...")
        
    neoforge_installer_url = f"https://maven.neoforged.net/releases/net/neoforged/neoforge/{loader_version}/neoforge-{loader_version}-installer.jar"
    
    with tempfile.TemporaryDirectory(prefix="launcher-neoforge-") as temp_dir:
        installer_path = os.path.join(temp_dir, "installer.jar")
        download_file(neoforge_installer_url, installer_path, status_callback=status_callback)
        
        # Ensure launcher_profiles.json exists
        profiles_path = os.path.join(mc_dir, "launcher_profiles.json")
        if not os.path.exists(profiles_path):
            with open(profiles_path, "w") as f:
                f.write('{"profiles":{}}')
                
        if status_callback:
            status_callback("Running NeoForge installer (this may take a few minutes)...")
            
        cmd = [java_path, "-jar", installer_path, "--install-client", mc_dir]
        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        res = subprocess.run(cmd, cwd=temp_dir, startupinfo=startupinfo, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"NeoForge installer failed: {res.stderr}")
            
        # Copy vanilla jar if missing
        neoforge_version_dir = os.path.join(mc_dir, "versions", neoforge_version_id)
        neoforge_jar = os.path.join(neoforge_version_dir, f"{neoforge_version_id}.jar")
        if not os.path.exists(neoforge_jar):
            vanilla_jar = os.path.join(mc_dir, "versions", minecraft_version, f"{minecraft_version}.jar")
            if os.path.exists(vanilla_jar):
                import shutil
                shutil.copy(vanilla_jar, neoforge_jar)
                
        if status_callback:
            status_callback(f"NeoForge installed successfully: {neoforge_version_id}")
        return True, neoforge_version_id

def install_paper(game_version, dest_dir, status_callback=None):
    if status_callback:
        status_callback(f"Fetching Paper builds for {game_version}...")
        
    builds_url = f"https://fill.papermc.io/v3/projects/paper/versions/{game_version}/builds"
    res = requests.get(builds_url, timeout=10)
    res.raise_for_status()
    builds_json = res.json()
    
    # Check if array or object
    builds_list = builds_json if isinstance(builds_json, list) else builds_json.get("builds", [])
    if not builds_list:
        raise ValueError(f"No Paper builds found for {game_version}")
        
    latest_build = max(builds_list, key=lambda b: b.get("id") or b.get("build") or 0)
    build_number = latest_build.get("id") or latest_build.get("build")
    
    downloads = latest_build.get("downloads", {})
    app_download = downloads.get("server:default") or downloads.get("application")
    if not app_download:
        raise ValueError("Paper build is missing download details")
        
    filename = app_download["name"]
    sha256 = app_download.get("checksums", {}).get("sha256") or app_download.get("sha256")
    
    jar_url = app_download.get("url") or f"https://api.papermc.io/v2/projects/paper/versions/{game_version}/builds/{build_number}/downloads/{filename}"
    
    os.makedirs(dest_dir, exist_ok=True)
    jar_path = os.path.join(dest_dir, "server.jar")
    
    if status_callback:
        status_callback(f"Downloading Paper server build {build_number}...")
    download_file_sha256(jar_url, jar_path, sha256, status_callback=status_callback)
    
    # Write eula.txt
    with open(os.path.join(dest_dir, "eula.txt"), "w") as f:
        f.write("eula=true\n")
        
    if status_callback:
        status_callback("Paper server installed successfully.")
    return True, jar_path
