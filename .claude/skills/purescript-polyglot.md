# PureScript Polyglot Skill — choosing a backend, and designing the seam

You are deciding whether to compile PureScript to a runtime other than
JavaScript, or designing the FFI seam of a program that already does.

Companion to `/purescript-tooling` (spago, workspaces, FFI file layout) and
`/purescript-style` (how to write the code once you are there). This skill is
about the *choice* and the *shape of the boundary*, and it carries measured
constants so the estimate is arithmetic rather than vibes.

The backends: **Jurist** (`purejl`, Julia), **Pythia** (`purepy`, Python),
**Gnomon** (`psgo`, Go), **purerl** (Erlang/BEAM), plus a Lua backend.

---

## Start here: three reasons, and only one is a measurement

Ask in this order. The first two questions decide it; the third is the default
and it is the common case.

### 1 · Is the thing POSSIBLE on the JS backend at all?

If no — **go, and stop evaluating.** There is no ratio to compute because there
is no alternative implementation to form a ratio against. The seam tax is then
a design input, never a decision input.

| Runtime | The capability |
|---|---|
| **BEAM** (purerl) | soft-real-time scheduling, per-process preemption, supervision trees, hot code loading |
| **Julia** (Jurist) | symbolic computation / CAS / model transformation (`Symbolics.jl`, `ModelingToolkit.jl`); genuine shared-memory threading over 10⁴–10⁵ independent tasks |
| **Go** (Gnomon) | one static binary with no runtime to install on the target |

**Web Workers do not make JS a threading answer.** They are message-passing
with structured clone, not shared memory, so a sweep of 10⁴ independent
integrations is a *different program* on JS rather than a slower one.

### 2 · Is reaching a FOREIGN LIBRARY the point?

`pandapower`, `scipy`, `OrdinaryDiffEq`, `umap`, `compress/gzip`. If yes, this
is the frontier case and the seam tax **is** the decision. Do the arithmetic
below before writing anything.

### 3 · Neither?

**Stay on the JS backend** — and be careful how you justify it, because the
obvious supporting number does not support it.

*"Is my own code faster in PureScript-on-X than on JS?"* is **unmeasured**.
The perf canary compares each backend against itself; the seam lanes compare a
seam against a seam. Grid Explorer's metrics scenario at 4.55× looks like the
answer and is not — 83 % of it is *displaced compute*, PureScript walking a
30-node graph where the reference calls networkx, so the arms run different
algorithms.

What is safe to say is structural: V8 has two decades of JIT work behind it,
and these backends emit curried closures and `Effect` thunks, so **the burden
is on the claim that the move buys speed**. Say "unmeasured, and here is why I
would not expect it" — never quote a ratio you cannot source.

---

## The arithmetic, for case 2

Two properties of the design you are proposing:

- **W** — microseconds of library work bought **per crossing**
- **N** — `Number`s the PureScript core **folds** per crossing. Iterating, not
  passing: handing a foreign array straight to another foreign is nearly free.

```
tax  ≈  1  +  prop  +  ( fixed_µs  +  perNumber_ns × N / 1000 )  /  W
```

| | `fixed_µs` | `prop` | `perNumber_ns` | W for <5 % | W for <1 % |
|---|---:|---:|---:|---:|---:|
| **Gnomon** (Go) | 1.7 | 0.07 % | 25 | ~34 µs | ~170 µs |
| **Jurist** (Julia) | 6.6 | 0.33 % | 1.9 | ~130 µs | ~660 µs |
| **Pythia** (Python) | 8.0 | 0.17 % | 104 | ~160 µs | ~800 µs |

Measured 2026-08-02, M4 MBP; `perf-seam/run_seam.py` in each backend repo
regenerates them. Validated out of sample at both ends of the range: predicts
7.1 % for Grid Explorer (measured 8.1 %) and 0.34 % for the Stability Atlas
(measured 0.2 %). Neither was used to fit the constants.

**`perNumber` is structural.** It follows from how each backend represents
`Array Number` — unboxed `Vector{Float64}`, boxed `[]any`, `list` of Python
float objects — so it will not improve with a faster machine or a different
library.

### Reading the answer

| tax | what to do |
|---|---|
| **< 1.05** | ship it |
| **1.05 – 1.20** | the seam is too fine-grained. Fix the seam, not the runtime. |
| **> 1.20** | you are crossing per *row*. Restructure so a crossing buys a batch of library work |

**Diagnose granularity before blaming the runtime.** A crossing per dataframe
row fails on every backend; a crossing per solve passes on every backend.

---

## The seam rule, which outranks the arithmetic

> **The FFI seam contains only what cannot be expressed in PureScript — a call
> into the foreign library. Your own algorithm is not a foreign function.**

The tempting fix for a bad tax is to move the loop into the foreign file. That
makes the number beautiful and destroys the thing being demonstrated: the
program is now written in Python with a PureScript veneer. If you cannot get
the tax down without moving your algorithm across, **report the tax** — it is a
real finding about the design.

Concretely: `Grid.Contingency` calls pandapower 42 times because the N-1 loop
*is* the analysis and belongs in PureScript. That is the correct shape even
though a single batched call would measure better.

### Keep `core/` FFI-free

Not a style preference — it buys two things mechanically:

1. **A free JS parity column.** FFI-free modules compile under the stock JS
   backend, so the differential corpus can diff your own logic byte-for-byte
   against the JS reference. That is a far stronger claim than "it compiles."
2. **No bogus JS companion.** The worry that every `foreign import` demands a
   fake `.js` is a *symptom* of putting foreigns in core. A column that binds a
   backend-specific library sets `backend: { cmd: "true" }` in its
   `spago.yaml` — CoreFn is emitted, JS codegen is skipped, the backend runs
   over `output/` afterwards. No stub, and none needed.

Layout (`polyglot-template`):

```
core/                    pure source — the only place program logic lives
  src/*.purs             FFI-FREE: compiles under every backend
  src/Runtime.purs       a foreign DECLARATION at the seam
  src/Runtime.{py,jl,js} the foreign, CO-LOCATED with the .purs it implements
columns/<rt>/spago.yaml  the whole per-runtime recipe — no foreigns
```

A foreign outside the seam is then a **misplaced file**, which a one-line
`find` catches — a structural fact instead of a judgement call.

---

## Correctness traps specific to polyglot work

### Foreign-origin values are an untested population

The differential corpus proves meaning survives translation, but only for
values **PureScript itself constructed** — it deliberately contains no foreign
libraries. Values that *enter* from a library are a separate population, and a
real bug lived there: purepy's `show` printed `np.float64(3997569)` for
399.7569, silently, for anything returned by numpy, because numpy 2.x changed
scalar `repr`.

**Coerce at the seam.** A `Number` may arrive as `numpy.float64`,
`numpy.float32`, `Decimal`, `Float32`, `Rational` or `BigFloat` — all things
that *are* a double without *being* the runtime's canonical one. The runtimes
now coerce in the render path, but a seam that does `float(x)` / `Float64(x)`
on the way in is the durable fix.

Note the asymmetry, because it tells you where to look: **the dynamically-typed
backends share this hazard and the statically-typed one does not.** psgo
unwraps a boxed `Number` with `n.(float64)`, so a `float32` panics by name
rather than rendering approximately. The `any` box that costs Gnomon ~25 ns per
`Number` read is what buys the check.

### `nan > x` is TRUE in PureScript

`Ord Number` is `unsafeCompare`, so a NaN that gets into the core poisons
comparisons silently. Stop NaN at the seam.

### The payload rule is per-runtime

**Don't make PureScript ITERATE a big foreign array.** Passing one onward costs
almost nothing — the Embedding Explorer hands 250,000 vector elements from one
foreign straight into another and pays nearly nothing. Folding costs ~104 ns an
element on Pythia, ~25 on Gnomon, ~2 on Jurist. The rule is about the fold, not
the transport, and it is weaker than "don't return a big array".

---

### Core depends only on what every column's package set agrees on

A core that imports more than the Prelude meets **package-set skew**: each
column builds core against its own set, and the sets disagree. Measured on
purerl-tidal's engine (2026-10-01) between the purerl set (erl-0.15.3, the
newest) and the registry: `parsing` is 6 (`Text.Parsing.Parser`) against 11
(`Parsing`, another API); maths is `Math` against `Data.Number`;
`Data.Rational` is `Ratio Int` against a newtype over `BigInt`. One source
cannot import either side of any of them.

So core may depend on a package only where the API it uses is the same in
every column's set. Anything else, core owns (a small Parsec, its own
`Rational`) or takes across the seam. A registry package that is JS-only can
also be *ported* for the BEAM, as the purerl organisation's `-erl1` packages
are: `purerl-tidal/vendor/js-bigints` is upstream's `.purs` plus a
`BigInt.erl`, and each column's `extraPackages` picks its side.

On the BEAM, compile with erlc **one file at a time** and
`-disable-feature maybe_expr` (OTP 27 made `maybe` a keyword, and purerl's
`Data.Maybe` defines one). A batch stops at its first failure and leaves the
rest `undef` at run time. polyglot-template's `poly` erlang arm does both.

---

## Matching a reference implementation: reference-semantics modules

When a port must agree with a library in another language **to the bit**
(purerl-tidal with Haskell Tidal: same events, same random drops), some of
the reference's semantics differ from PureScript's standard libraries.
Haskell's `Int` wraps at 64 bits where PureScript's is 32 (JS) or unbounded
(BEAM); `round` is banker's; Parsec's `string` consumes what it matched.

**The rule (AC, 2026-10-01): a divergence from the standard libraries is
always flagged in the code.** It goes in a module named for the reference,
whose specification is "what the reference does": `Haskell.Int`,
`Haskell.Integer`, `Haskell.Rational`, `Haskell.Double`, `Haskell.Parsec` (in
`purerl-tidal/engine/core/src/Haskell/`), and some day perhaps `Julia.*` or
`Go.*`. Importing it *is* the flag. Never shadow `div`, `floor` or `Int`
silently, and give no instance whose laws differ from the reference's (no
`EuclideanRing` on `Haskell.Integer`: Euclidean `div` is not Haskell's).

- **Is it worth a module?** Only if the reference's own outputs show the
  difference. Error wording, speed and internal formatting are documented
  differences instead.
- **The representation sits at the seam; the algorithms stay PureScript.**
  `Haskell.Int` is a `JS.BigInt` brought back into 64 bits after every
  operation; `xorwise` is written in PureScript on top of it.
- **Held to the reference by an oracle**, never hand-written expectations: a
  case file the reference itself evaluates into a golden (`make oracle-prim`
  in purerl-tidal runs GHC, `Text.Parsec` and Tidal's own functions), checked
  in every column. It found two bugs in the Parsec port before PureScript
  ran.
- **Keep it standalone** (`src/Haskell` imports nothing from the port), so it
  can become its own package the day a second port needs it.

Part of a growing set of polyglot utilities (with the standard printer for
comparing outputs across backends), to be taken stock of together.
Background: `docs/kb/reference/reference-semantics.md`.

---

## When asked "should we use backend X for this?"

Answer in this shape, and do not skip the first line:

1. **Which of the three cases is it?** Capability, frontier, or neither. Name it.
2. **If capability:** say what is impossible on JS, concretely. Do not quote a
   tax — it cannot change the answer.
3. **If frontier:** estimate W and N from the proposed design, do the
   arithmetic, and give a number with the assumption stated.
4. **If neither:** say stay on JS, and give the 4.45× so the recommendation has
   evidence behind it rather than caution.

Reach for `docs/kb/reference/choosing-a-backend.md` for the flow-chart and the
worked examples, and `docs/kb/reference/seam-tax.md` for how the constants were
measured and what they do not claim.
