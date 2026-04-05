#!/usr/bin/env python3
"""
Build a reverse-dependency ranking of PureScript packages.

For each package in the package set, finds its manifest in the registry index,
extracts dependencies, and computes how many other packages depend on it.
"""

import json
import os
import sys
from pathlib import Path
from collections import defaultdict

REGISTRY_INDEX = Path("/Users/afc/work/afc-work/registry-index")
PACKAGE_SET = Path("/Users/afc/work/afc-work/CodeExplorer/minard/database/_registry-index/package-set-71.0.0.json")
OUTPUT = Path("/Users/afc/work/afc-work/purescript-ecosystem-guide/package-ranking.json")

# Org-to-category mapping
ORG_CATEGORIES = {
    "purescript": "core",
    "purescript-contrib": "contrib",
    "purescript-node": "node",
    "purescript-web": "web",
}


def manifest_path(name: str) -> Path:
    """Compute the registry-index path for a package name.

    Follows the Cargo-style 2-char prefix convention:
    - length 1: /1/{name}
    - length 2: /2/{name}
    - length 3: /3/{first-char}/{name}
    - length 4+: /{chars[0:2]}/{chars[2:4]}/{name}
    """
    n = len(name)
    if n == 1:
        return REGISTRY_INDEX / "1" / name
    elif n == 2:
        return REGISTRY_INDEX / "2" / name
    elif n == 3:
        return REGISTRY_INDEX / "3" / name[0] / name
    else:
        return REGISTRY_INDEX / name[0:2] / name[2:4] / name


def load_manifest(name: str, target_version: str):
    """Load the manifest for a specific package version from the JSONL registry file."""
    path = manifest_path(name)
    if not path.exists():
        print(f"  WARNING: manifest not found for {name} at {path}", file=sys.stderr)
        return None

    # Read all lines and find the matching version
    with open(path, "r") as f:
        best = None
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("version") == target_version:
                return obj
            # Keep the last entry as fallback (usually the latest)
            best = obj

    if best:
        print(f"  WARNING: version {target_version} not found for {name}, using {best.get('version')}", file=sys.stderr)
        return best

    return None


def main():
    # Load the package set
    with open(PACKAGE_SET) as f:
        package_set_data = json.load(f)

    packages = package_set_data["packages"]  # dict: name -> version
    print(f"Package set contains {len(packages)} packages")

    # Load all manifests
    manifests = {}
    missing = []
    for name, version in sorted(packages.items()):
        manifest = load_manifest(name, version)
        if manifest:
            manifests[name] = manifest
        else:
            missing.append(name)

    print(f"Loaded {len(manifests)} manifests, {len(missing)} missing")
    if missing:
        print(f"Missing: {', '.join(missing)}", file=sys.stderr)

    # Build forward dependencies (only packages in the set)
    package_names = set(packages.keys())
    forward_deps = {}  # name -> [dep_names in set]

    for name, manifest in manifests.items():
        deps_obj = manifest.get("dependencies", {})
        # deps_obj is a dict: dep_name -> version_range
        dep_names = [d for d in deps_obj.keys() if d in package_names]
        forward_deps[name] = dep_names

    # Build reverse dependency counts
    reverse_dep_count = defaultdict(int)
    for name, deps in forward_deps.items():
        for dep in deps:
            reverse_dep_count[dep] += 1

    # Build output
    results = []
    for name in sorted(packages.keys()):
        manifest = manifests.get(name)
        if not manifest:
            continue

        location = manifest.get("location", {})
        org = location.get("githubOwner", "unknown")
        category = ORG_CATEGORIES.get(org, "community")

        deps_obj = manifest.get("dependencies", {})
        dep_names = sorted(d for d in deps_obj.keys() if d in package_names)

        results.append({
            "name": name,
            "version": manifest.get("version", packages[name]),
            "description": manifest.get("description", ""),
            "org": org,
            "dependencies": dep_names,
            "reverse_dep_count": reverse_dep_count.get(name, 0),
            "category": category,
        })

    # Sort by reverse_dep_count descending
    results.sort(key=lambda x: (-x["reverse_dep_count"], x["name"]))

    output = {"packages": results}

    with open(OUTPUT, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nWrote {len(results)} packages to {OUTPUT}")
    print(f"\nTop 30 by reverse dependency count:")
    print(f"{'Rank':>4}  {'Package':<35} {'Rev Deps':>8}  {'Cat':<12} {'Org'}")
    print("-" * 95)
    for i, pkg in enumerate(results[:30], 1):
        print(f"{i:>4}  {pkg['name']:<35} {pkg['reverse_dep_count']:>8}  {pkg['category']:<12} {pkg['org']}")

    # Summary by category
    from collections import Counter
    cat_counts = Counter(p["category"] for p in results)
    print(f"\nPackages by category:")
    for cat, count in cat_counts.most_common():
        print(f"  {cat:<12} {count}")


if __name__ == "__main__":
    main()
