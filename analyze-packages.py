#!/usr/bin/env python3
"""
Analyze PureScript packages from the package-ranking.json:
1. Author analysis for specific owners/orgs
2. JS-wrapper vs pure-PS classification
3. Cross-reference with already-covered packages in the ecosystem skill
"""

import json
import re
import subprocess
import sys
from pathlib import Path

BASE = Path("/Users/afc/work/afc-work/purescript-ecosystem-guide")
RANKING_FILE = BASE / "package-ranking.json"
SKILL_FILE = BASE / ".claude/skills/purescript-ecosystem.md"
OUTPUT_FILE = BASE / "package-analysis.json"


def load_packages():
    with open(RANKING_FILE) as f:
        data = json.load(f)
    return data["packages"]


def load_covered_packages():
    """Extract package names from #### headers in the ecosystem skill file."""
    covered = set()
    with open(SKILL_FILE) as f:
        for line in f:
            m = re.match(r"^#### (\S+)", line)
            if m:
                covered.add(m.group(1))
    return covered


def author_analysis(packages):
    """Group packages by specific authors/orgs."""

    # Define author queries: key -> list of (field, value) pairs to match (case insensitive)
    author_queries = {
        "JordanMartinez": [
            ("owner", "jordanmartinez"),
        ],
        "artemis-prime": [
            ("owner", "artemis-prime"),
            ("owner", "artemissystem"),
        ],
        "purefunctor": [
            ("owner", "purefunctor"),
        ],
        "rowtype-yoga": [
            ("owner", "rowtype-yoga"),
        ],
        "purescript (org)": [
            ("org", "purescript"),
        ],
        "purescript-contrib (org)": [
            ("org", "purescript-contrib"),
        ],
    }

    results = {}
    for author_key, matchers in author_queries.items():
        matched = []
        for pkg in packages:
            pkg_owner = (pkg.get("owner") or "").lower()
            pkg_org = (pkg.get("org") or "").lower()
            for field, value in matchers:
                if field == "owner" and pkg_owner == value.lower():
                    matched.append(pkg)
                    break
                elif field == "org" and pkg_org == value.lower():
                    matched.append(pkg)
                    break
        # Sort by boosted_score descending
        matched.sort(key=lambda p: p.get("boosted_score", 0), reverse=True)
        results[author_key] = [
            {
                "name": p["name"],
                "rdeps": p["reverse_dep_count"],
                "score": p.get("boosted_score", 0),
                "desc": p.get("description", ""),
            }
            for p in matched
        ]

    return results


def classify_packages(packages):
    """Classify packages as js-wrapper or pure-ps based on heuristics."""

    # Name prefixes that suggest JS wrapper
    js_wrapper_prefixes = [
        "node-", "web-", "js-", "react-", "halogen-",
    ]

    # Orgs that are primarily JS wrapper publishers
    js_wrapper_orgs = {
        "purescript-web", "purescript-node", "purescript-react",
        "purescript-halogen",
    }

    # Package names containing these substrings suggest JS wrapper
    js_wrapper_name_substrings = [
        "express", "fetch", "sqlite", "postgresql", "xterm", "blessed",
        "ink", "dom", "html", "canvas", "websocket", "xhr",
        "indexeddb", "webgl", "webrtc", "navigator", "console",
        "clipboard", "notification", "serviceworker", "worker",
        "crypto", "gamepad", "geolocation", "midi", "speech",
        "vibration", "battery", "bluetooth", "usb",
    ]

    # Dependencies that suggest JS wrapper nature
    js_wrapper_deps = {
        "web-dom", "web-html", "web-events", "web-file",
        "web-storage", "web-xhr", "web-fetch", "web-canvas",
        "web-clipboard", "web-socket", "web-workers",
        "node-buffer", "node-streams", "node-fs", "node-http",
        "node-path", "node-process", "node-child-process",
        "node-event-emitter", "node-net", "node-os", "node-readline",
        "node-url",
        "react-basic", "react-basic-hooks", "react-basic-dom",
    }

    # Specific known JS wrapper packages
    known_js_wrappers = {
        "random", "console", "now", "unsafe-coerce", "debug",
        "refs", "st", "effect",  # These have FFI but are core
        # Actually, let's be more conservative - these core packages
        # have FFI but are foundational, not "wrappers"
    }

    # Core packages that have FFI but shouldn't be classified as "wrappers"
    # They're foundational PureScript packages
    core_with_ffi = {
        "prelude", "effect", "console", "random", "now", "refs", "st",
        "unsafe-coerce", "debug", "aff", "exceptions", "arrays",
        "strings", "integers", "numbers", "math", "functions",
        "nullable", "foreign", "foreign-object", "datetime",
        "js-date", "js-timers", "js-uri",
    }

    js_wrappers = []
    pure_ps = []

    for pkg in packages:
        name = pkg["name"]
        org = (pkg.get("org") or "").lower()
        deps = set(pkg.get("dependencies", []))
        is_js_wrapper = False

        # Check org
        if org in js_wrapper_orgs:
            is_js_wrapper = True

        # Check name prefix
        if not is_js_wrapper:
            for prefix in js_wrapper_prefixes:
                if name.startswith(prefix):
                    is_js_wrapper = True
                    break

        # Check name substrings
        if not is_js_wrapper:
            name_lower = name.lower()
            for substr in js_wrapper_name_substrings:
                if substr in name_lower:
                    is_js_wrapper = True
                    break

        # Check if many dependencies are JS wrapper deps
        if not is_js_wrapper:
            js_dep_count = len(deps & js_wrapper_deps)
            if js_dep_count >= 2:
                is_js_wrapper = True

        # Override: core packages with FFI are NOT classified as wrappers
        if name in core_with_ffi:
            is_js_wrapper = False

        if is_js_wrapper:
            js_wrappers.append(name)
        else:
            pure_ps.append(name)

    return js_wrappers, pure_ps


def main():
    packages = load_packages()
    covered = load_covered_packages()

    # Part 1: Author analysis
    by_author = author_analysis(packages)

    # Part 2: Classification
    js_wrappers, pure_ps = classify_packages(packages)

    # Output JSON
    output = {
        "by_author": by_author,
        "classification": {
            "js_wrapper": sorted(js_wrappers),
            "pure_ps": sorted(pure_ps),
        },
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    # Print summary
    print("=" * 70)
    print("PACKAGE ANALYSIS SUMMARY")
    print("=" * 70)

    print(f"\nTotal packages: {len(packages)}")
    print(f"JS-wrapper packages: {len(js_wrappers)}")
    print(f"Pure-PS packages: {len(pure_ps)}")
    print(f"Already covered in skill: {len(covered)}")

    print("\n" + "=" * 70)
    print("AUTHOR ANALYSIS")
    print("=" * 70)

    for author, pkgs in by_author.items():
        print(f"\n--- {author} ({len(pkgs)} packages) ---")
        if not pkgs:
            print("  (no packages found)")
            continue
        for p in pkgs:
            in_skill = "COVERED" if p["name"] in covered else "NOT COVERED"
            print(f"  {p['name']:40s}  rdeps={p['rdeps']:3d}  score={p['score']:5.0f}  [{in_skill}]")
            if p["desc"]:
                print(f"    {p['desc'][:80]}")

    print("\n" + "=" * 70)
    print("UNCOVERED PACKAGES BY AUTHOR")
    print("=" * 70)

    for author, pkgs in by_author.items():
        uncovered = [p for p in pkgs if p["name"] not in covered]
        if uncovered:
            print(f"\n--- {author}: {len(uncovered)} uncovered ---")
            for p in uncovered:
                print(f"  {p['name']:40s}  rdeps={p['rdeps']:3d}  score={p['score']:5.0f}")
                if p["desc"]:
                    print(f"    {p['desc'][:80]}")

    print("\n" + "=" * 70)
    print("JS-WRAPPER PACKAGES (sorted by rdeps)")
    print("=" * 70)

    # Get full package info for js_wrappers
    pkg_by_name = {p["name"]: p for p in packages}
    js_wrapper_details = sorted(
        [(name, pkg_by_name[name]) for name in js_wrappers],
        key=lambda x: x[1]["reverse_dep_count"],
        reverse=True,
    )
    for name, pkg in js_wrapper_details[:40]:
        in_skill = "COVERED" if name in covered else "NOT COVERED"
        print(f"  {name:40s}  rdeps={pkg['reverse_dep_count']:3d}  [{in_skill}]")

    if len(js_wrapper_details) > 40:
        print(f"  ... and {len(js_wrapper_details) - 40} more")

    print("\n" + "=" * 70)
    print("HIGH-VALUE UNCOVERED PURE-PS PACKAGES (rdeps >= 5)")
    print("=" * 70)

    uncovered_pure = [
        (name, pkg_by_name[name])
        for name in pure_ps
        if name not in covered and pkg_by_name[name]["reverse_dep_count"] >= 5
    ]
    uncovered_pure.sort(key=lambda x: x[1]["reverse_dep_count"], reverse=True)
    for name, pkg in uncovered_pure:
        print(f"  {name:40s}  rdeps={pkg['reverse_dep_count']:3d}  score={pkg.get('boosted_score', 0):5.0f}  cat={pkg.get('category', '?')}")
        if pkg.get("description"):
            print(f"    {pkg['description'][:80]}")


if __name__ == "__main__":
    main()
