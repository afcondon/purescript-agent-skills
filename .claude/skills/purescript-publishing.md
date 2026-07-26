# PureScript Publishing Skill

You are publishing a package to the PureScript registry, or preparing one
to be published. This skill covers naming, the preconditions `spago
publish` enforces, the publish itself, and what consumers need afterwards.

Companion to `/purescript-tooling`, which covers package sets, workspaces
and `extraPackages` — the things you configure *before* any of this
matters.

---

## Publication is permanent

A published version cannot be unpublished. Names cannot be reused. Before
running `spago publish`, everything below should already be settled,
because all of it is free to change up to that moment and expensive after.

---

## Naming

The registry namespace is **flat and shared**, and it drops the
`purescript-` prefix: repo `purescript-foo` publishes as `foo`.

Check availability — 404 means free:

```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  "https://raw.githubusercontent.com/purescript/registry/main/metadata/<name>.json"
```

Two questions worth asking out loud before committing to a name:

**Is the prefix description or branding?** If a library's dependencies
don't include the project it's named after, the project name is branding,
and on a shared registry it buries the word people actually search for.
`hylograph-halogen-ui` became `halogen-widgets` for exactly this reason:
nothing in it depended on any `hylograph-*` package. Ecosystem convention
is `<host-library>-<thing>` — `halogen-select`, `halogen-store`,
`halogen-formless` are all third-party and none prefix with an org name.

**Do the module names agree?** Modules are what consumers type every day.
`halogen-store` exports `Halogen.Store.*`; community packages using the
host library's namespace is established practice. Renaming modules after
publication is a breaking change; before it, it's a `sed`.

Rename the **GitHub repo before publishing** — the registry records
`githubOwner`/`githubRepo` in the manifest, and GitHub redirects the old
URL, so doing it first costs nothing.

---

## Preconditions

`spago.yaml` needs a `publish` block:

```yaml
package:
  name: halogen-widgets
  description: ...
  publish:
    version: 0.2.0
    license: MIT
    location:
      githubOwner: afcondon
      githubRepo: purescript-halogen-widgets
```

And the repo needs:

- to be **public**, with a LICENSE file matching the declared license
- a **clean working tree**
- the release **commit pushed**
- a **git tag** matching `publish.version` exactly (`v0.2.0` for `0.2.0`),
  **also pushed**

Moving a tag is acceptable *only* before the version is published — if a
fix lands after tagging, delete and recreate rather than burning a version
number:

```bash
git push origin :refs/tags/v0.2.0   # delete remote
git tag -d v0.2.0 && git tag v0.2.0 # recreate at HEAD
git push origin v0.2.0
```

### Dependencies need ranges

Every dependency needs a version range, not a bare name:

```yaml
  dependencies:
    - aff: ">=7.1.0 <8.0.0"
    - halogen: ">=7.0.0 <8.0.0"
```

**`spago install` adds bare names — it does not add ranges.** After
running it, add the bounds by hand or publishing will reject the package.

---

## `spago publish` is stricter than `spago build`

This is the step that most often fails first, and it fails on something
`spago build` is perfectly happy with: **undeclared transitive
dependencies**. A module importing `Data.String` while `strings` arrives
only via `halogen` compiles fine and will not publish.

```
✘ Found unused and/or undeclared transitive dependencies:
  dom-indexed  from `Halogen.Widgets.Slider`
  strings      from `Halogen.Widgets.Select`
```

Fix, then add ranges to what it wrote:

```bash
spago install -p <pkg> dom-indexed strings
```

It also reports **unused** declared dependencies, which are worth removing
rather than silencing.

---

## Publishing

In a multi-package workspace, `-p` is required:

```bash
spago publish -p <package-name>
```

### Spago misreports success

On success spago prints something that reads like a failure:

```
✘ Registry did not like this and answered with status 201, got answer:
  {"jobId":"cdf15b0c-..."}
```

**201 is Created — this worked.** The registry accepted the job and queued
it. Do not retry on seeing this; poll the job instead:

```bash
curl -s "https://registry.purescript.org/api/v1/jobs/<jobId>" \
  | python3 -c "import json,sys; j=json.load(sys.stdin); \
      print(j.get('success')); [print(' ', l.get('level'), l.get('message','')[:150]) \
      for l in (j.get('logs') or [])[-8:]]"
```

`success: true`, followed by `Enqueuing matrix job: compiler 0.15.x`
lines, means it's done — the matrix builds are Pursuit documentation and
compiler-compatibility metadata, not gates on the publish.

To wait rather than poll by hand:

```bash
until curl -s ".../jobs/<jobId>" | grep -q '"finishedAt":"'; do sleep 5; done
```

The registry generates a `purs.json` manifest from `spago.yaml`
automatically; no need to write one.

---

## Consuming it afterwards

A published package **not in your package set** goes in `extraPackages`
with an explicit version — the same shape as any other pinned extra:

```yaml
workspace:
  packageSet:
    registry: 77.13.1
  extraPackages:
    halogen-widgets: "0.2.0"
```

### The local index cache lags

Immediately after publishing, a consumer build fails with:

```
✘ The following packages do not exist in the package index:
  - halogen-widgets
```

That is a stale local cache, not a failed publish. Refresh it:

```bash
git -C ~/Library/Caches/spago-nodejs/registry-index pull
```

Then delete `spago.lock` and rebuild. Confirm it resolved from the
registry rather than a leftover local copy:

```bash
ls -d .spago/p/<name>-*        # expect <name>-<version>
grep '"<name>"' spago.lock     # expect the pinned version
```

---

## Why bother — the path-dependency trap

A `path:` extraPackage pointing at an absolute local directory means
**only one machine can build the repo**. This is easy to miss because it
doesn't break the things you look at:

- a **GitHub Pages** site with `build_type: legacy` serves committed files
  and never compiles anything, so a published static site keeps working
  indefinitely;
- your own machine keeps building.

What it breaks is every contributor and any CI. Check for stragglers with:

```bash
grep -rn "path:" spago.yaml */spago.yaml
```

---

## Checklist

1. Name settled — availability checked, prefix justified, modules agree
2. GitHub repo renamed if it's going to be
3. Public repo, LICENSE present and matching
4. `publish:` block with version, license, location
5. Every dependency carries a version range
6. Clean tree, commit pushed, tag pushed and matching the version
7. `spago publish -p <pkg>` — expect the transitive-dependency complaint
8. **201 means success** — poll the job for `success: true`
9. Consumers: `extraPackages: { name: "x.y.z" }`, pull the index cache,
   drop `spago.lock`, rebuild
10. Confirm no `path:` dependencies remain
