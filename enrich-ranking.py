#!/usr/bin/env python3
"""
Enrich PureScript package ranking with GitHub owner info and boosted scores.
"""

import json
import os
import sys

REGISTRY_INDEX = "/Users/afc/work/afc-work/registry-index"
RANKING_FILE = "/Users/afc/work/afc-work/purescript-ecosystem-guide/package-ranking.json"


def registry_path(name: str) -> str:
    """Compute the registry-index path for a package name using Cargo convention."""
    n = len(name)
    if n == 1:
        return os.path.join(REGISTRY_INDEX, "1", name)
    elif n == 2:
        return os.path.join(REGISTRY_INDEX, "2", name)
    elif n == 3:
        return os.path.join(REGISTRY_INDEX, "3", name[0], name)
    else:
        return os.path.join(REGISTRY_INDEX, name[0:2], name[2:4], name)


def get_owner(name: str) -> str | None:
    """Read the last line of the JSONL manifest and extract githubOwner."""
    path = registry_path(name)
    if not os.path.isfile(path):
        return None
    try:
        # Read last non-empty line
        with open(path, "r") as f:
            lines = f.readlines()
        for line in reversed(lines):
            line = line.strip()
            if line:
                manifest = json.loads(line)
                loc = manifest.get("location", {})
                return loc.get("githubOwner")
        return None
    except Exception as e:
        print(f"  Warning: failed to read manifest for {name}: {e}", file=sys.stderr)
        return None


# Author boosts
AUTHOR_BOOSTS = {
    "garyb": 15,
    "natefaubion": 15,
    "thomashoneyman": 10,
    "paf31": 10,
    "hdgarrood": 8,
    "JordanMartinez": 8,
    "purescript": 5,
    "purescript-contrib": 5,
    "purescript-node": 5,
    "purescript-web": 5,
}

# Function boosts (important packages regardless of owner)
FUNCTION_BOOST_PACKAGES = {
    "halogen", "spec", "httpurple", "codec-argonaut", "codec", "affjax",
    "routing-duplex", "react-basic-hooks", "react-basic-dom", "deku",
    "optparse", "postgresql", "node-sqlite3", "debug", "simple-json",
    "yoga-json", "js-promise-aff", "web-fetch", "quickcheck",
    "profunctor-lenses", "language-cst-parser", "tidy", "dotenv",
    "validation", "argonaut", "halogen-hooks",
}


def main():
    # Load existing ranking
    with open(RANKING_FILE, "r") as f:
        data = json.load(f)

    packages = data["packages"]
    print(f"Loaded {len(packages)} packages from ranking")

    # Enrich with owner
    missing_owners = []
    for pkg in packages:
        owner = get_owner(pkg["name"])
        pkg["owner"] = owner if owner else "unknown"
        if not owner:
            missing_owners.append(pkg["name"])

    if missing_owners:
        print(f"\nWarning: {len(missing_owners)} packages with no owner found:")
        for name in missing_owners[:20]:
            print(f"  - {name}")
        if len(missing_owners) > 20:
            print(f"  ... and {len(missing_owners) - 20} more")

    # Build case-insensitive author boost lookup
    author_boosts_lower = {k.lower(): v for k, v in AUTHOR_BOOSTS.items()}

    # Compute boosted scores
    for pkg in packages:
        rdeps = pkg["reverse_dep_count"]
        author_boost = author_boosts_lower.get(pkg["owner"].lower(), 0)
        function_boost = 20 if pkg["name"] in FUNCTION_BOOST_PACKAGES else 0
        pkg["boosted_score"] = rdeps + author_boost + function_boost

    # Record original rank for comparison
    for i, pkg in enumerate(packages):
        pkg["_original_rank"] = i + 1

    # Sort by boosted score descending
    packages.sort(key=lambda p: p["boosted_score"], reverse=True)

    # Record new rank
    for i, pkg in enumerate(packages):
        pkg["_new_rank"] = i + 1

    # --- Print top 120 ---
    print("\n" + "=" * 100)
    print("TOP 120 PACKAGES BY BOOSTED SCORE")
    print("=" * 100)
    print(f"{'Rank':>4}  {'Name':<40} {'Owner':<25} {'RDeps':>5} {'Boost':>5} {'Score':>5}")
    print("-" * 100)
    for i, pkg in enumerate(packages[:120]):
        rdeps = pkg["reverse_dep_count"]
        boost = pkg["boosted_score"] - rdeps
        print(f"{i+1:>4}  {pkg['name']:<40} {pkg['owner']:<25} {rdeps:>5} {'+' + str(boost) if boost else '':>5} {pkg['boosted_score']:>5}")

    # --- Owner stats ---
    print("\n" + "=" * 80)
    print("TOP 30 OWNERS BY PACKAGE COUNT")
    print("=" * 80)
    owner_counts = {}
    for pkg in packages:
        owner = pkg["owner"]
        owner_counts[owner] = owner_counts.get(owner, 0) + 1
    sorted_owners = sorted(owner_counts.items(), key=lambda x: x[1], reverse=True)
    print(f"{'Owner':<35} {'Count':>5}")
    print("-" * 42)
    for owner, count in sorted_owners[:30]:
        print(f"{owner:<35} {count:>5}")

    # --- Biggest rank movers ---
    print("\n" + "=" * 80)
    print("BIGGEST RANK IMPROVEMENTS (moved up 10+ positions)")
    print("=" * 80)
    movers = []
    for pkg in packages:
        delta = pkg["_original_rank"] - pkg["_new_rank"]
        if delta >= 10:
            movers.append((pkg, delta))
    movers.sort(key=lambda x: x[1], reverse=True)
    print(f"{'Name':<40} {'Owner':<25} {'Old':>4} {'New':>4} {'Delta':>6} {'RDeps':>5} {'Score':>5}")
    print("-" * 95)
    for pkg, delta in movers:
        print(f"{pkg['name']:<40} {pkg['owner']:<25} {pkg['_original_rank']:>4} {pkg['_new_rank']:>4} {'+' + str(delta):>6} {pkg['reverse_dep_count']:>5} {pkg['boosted_score']:>5}")

    # Clean up temp fields and write output
    for pkg in packages:
        del pkg["_original_rank"]
        del pkg["_new_rank"]

    with open(RANKING_FILE, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    print(f"\nWrote enriched ranking to {RANKING_FILE}")


if __name__ == "__main__":
    main()
