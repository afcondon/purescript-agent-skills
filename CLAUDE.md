# PureScript Ecosystem Guide

## Goal

Create a concise, AI-to-AI reference of the PureScript package ecosystem. The primary audience is Claude (or other AI assistants) helping developers write PureScript. The guide should provide the practical knowledge that's missing from training data — which packages to reach for, cultural conventions, and "don't do this, do that" guidance.

## Why This Exists

PureScript is a niche language. Claude's PureScript knowledge is largely inferred from Haskell training data, which leads to:
- Suggesting Haskell idioms that don't apply (e.g., type class instances for JSON instead of codec values)
- Not knowing about key packages (e.g., `codec-argonaut`, `halogen`, `httpure`)
- Missing ecosystem conventions (e.g., `Aff` for async, `Effect` for sync, never `IO`)
- Not understanding the package split patterns (e.g., `affjax` vs `affjax-web` vs `affjax-node`)

## Data Sources

### Package set (current versions)
`/Users/afc/work/afc-work/CodeExplorer/minard/database/_registry-index/package-set-71.0.0.json`
- 568 packages with current version numbers
- Quick lookup for what's available

### Registry index (all versions, with manifests)
`/Users/afc/work/afc-work/registry-index/`
- 2-char prefix directory structure (e.g., `af/fj/affjax`)
- Each file contains JSONL: one JSON object per published version
- Includes: name, version, license, description, location (GitHub), dependencies
- 1282 total manifest files

### Package source code
For deeper review, fetch from GitHub using the location info in manifests.
Use `gh api` or clone repos as needed.

## Output Format

### Per-package review (for important packages)

```markdown
## package-name

**What:** One-sentence description
**When to use:** The trigger condition — when should an AI suggest this?
**Key exports:** 3-5 most important types/functions
**Instead of:** What NOT to do (the common mistake this prevents)
**Ecosystem role:** core | contrib | community | niche
**Status:** active | maintained | dormant | deprecated
**Note:** Any PureScript-specific convention that differs from Haskell
```

### Skill output

The final product should be a Claude Code skill (`.claude/skills/`) that can be loaded when working on PureScript projects. It should be concise enough to fit in context (~10-15K tokens for the essential packages) with pointers to detailed reviews for deeper dives.

## Approach

### Phase 1: Triage (which packages matter?)
1. Load the package set
2. Categorize by ecosystem role:
   - **Core** (purescript-* org): prelude, effect, aff, arrays, etc.
   - **Contrib** (purescript-contrib): argonaut, routing, etc.
   - **Web framework**: halogen, react, etc.
   - **Server**: httpure, express, etc.
   - **Testing**: spec, quickcheck, etc.
   - **Data**: codec, foreign, validation, etc.
3. Rank by importance (dependency count is a good proxy)
4. Focus the detailed review on the top ~80 packages

### Phase 2: Review
For each important package:
1. Read the manifest (description, deps)
2. Fetch and skim the source (key module, main types)
3. Write the review in the format above
4. Note any "gotchas" or conventions

### Phase 3: Skill creation
1. Compile reviews into a skill document
2. Organize by category (not alphabetically)
3. Include a "decision tree" section: "If you need X, use Y"
4. Test by asking Claude PureScript questions with the skill loaded

## Important Conventions to Capture

These are things Claude gets wrong that the guide should fix:

- **JSON**: Use `codec-argonaut` codec values, NOT type class instances (no `decodeJson`/`encodeJson` instances)
- **Async**: Use `Aff`, not `IO`. `launchAff_` to run from `Effect`.
- **Records**: PureScript records are structural (row types), not nominal. No `data` needed for simple product types.
- **Newtypes for domain concepts**, not type aliases
- **`when`/`unless`** not `if-then-pure unit`
- **`ado` notation** for independent applicative computations
- **`EffectFn`/`Fn`** for uncurried FFI, with `runFn` fully saturated
- **No `String` for closed alternatives** — use ADTs
- **`case _ of`** not equational pattern matching at the function level
