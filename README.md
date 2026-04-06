# PureScript Agent Skills

Three [Claude Code](https://claude.ai/claude-code) skills for AI-assisted PureScript development.

AI assistants generally infer PureScript from Haskell training data, which leads to suggesting packages that don't exist, idioms that don't apply, and missing the conventions that the PureScript community actually uses. These skills fix that.

## The Skills

### [`purescript.md`](.claude/skills/purescript.md) — Language Skill

PureScript language patterns, idioms, and pitfalls. Covers:

- Module structure (imports are top-level only, no qualified paths)
- Type system essentials (records, row polymorphism, ADTs, newtypes)
- Common conversions (`Data.Int.toNumber`, `Data.Number.fromString`, etc.)
- Effect and Aff (no `IO` in PureScript)
- Halogen component patterns
- Haskell-vs-PureScript differences (no `IO`, no `Text`, explicit `forall`)
- FFI patterns (`EffectFn`/`Fn`, uncurried wrappers, naming conventions)
- Common pitfalls with code examples

### [`purescript-ecosystem.md`](.claude/skills/purescript-ecosystem.md) — Ecosystem Guide

AI-to-AI reference for the PureScript package ecosystem. Covers:

- Decision trees: "I need X, which package do I use?"
- 146 package reviews organized by category (core, data types, JSON, web frameworks, HTTP, testing, Node.js, parsing, CLI, database, etc.)
- Ecosystem context: key organizations, authors, build tooling, `spago.yaml` config
- Package set and registry structure

### [`fp-police.md`](.claude/skills/fp-police.md) — Code Quality Auditor

Grep-based audit tool that catches functional programming violations:

- Unsafe operations (`unsafeCoerce`, `unsafePerformEffect`, `unsafePartial`)
- Code smells (`else pure unit`, `Show` used for serialization, string errors)
- FFI discipline (naming conventions, curried foreign imports, unsaturated `runFn`)
- Style and idiom violations
- Supports project-specific rules via `.claude/fp-police-rules.md`

## Installation

Copy the skills into your project's `.claude/skills/` directory:

```bash
mkdir -p .claude/skills
curl -sL https://raw.githubusercontent.com/afcondon/purescript-agent-skills/main/.claude/skills/purescript.md -o .claude/skills/purescript.md
curl -sL https://raw.githubusercontent.com/afcondon/purescript-agent-skills/main/.claude/skills/purescript-ecosystem.md -o .claude/skills/purescript-ecosystem.md
curl -sL https://raw.githubusercontent.com/afcondon/purescript-agent-skills/main/.claude/skills/fp-police.md -o .claude/skills/fp-police.md
```

Or to install for all projects under a parent directory:

```bash
mkdir -p ~/work/.claude/skills
# copy files there instead
```

Then in any Claude Code session:

```
/purescript              # Load language idioms and pitfalls
/purescript-ecosystem    # Load package guide and decision trees
/fp-police               # Run code quality audit
```

## Data Pipeline

The Python scripts and JSON files are included for completeness. They were used to build the ecosystem guide by analyzing the PureScript package registry:

- `build-ranking.py` — Parses registry manifests, builds reverse-dependency counts
- `enrich-ranking.py` — Adds GitHub owner data, applies author/function importance boosts
- `analyze-packages.py` — Classifies packages as JS-wrapper vs pure-PureScript, analyzes by author
- `package-ranking.json` — All 568 packages ranked by boosted importance score
- `package-analysis.json` — JS/pure classification and per-author breakdown
- `coverage-report.md` — Which packages are covered in the guide and which aren't

These can be re-run against newer package sets or with different models to update the guide. The package set used here is 71.0.0 (January 2026, compiler 0.15.15).

## License

MIT
