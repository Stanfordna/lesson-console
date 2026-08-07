# Design decisions

Why this tool exists, how it got to its current shape, and what was tried and
rejected along the way. Written so a future maintainer (human or AI) doesn't
re-litigate settled questions without new evidence.

## The originating problem

The tool grew out of a concrete failure mode: an expert developer trying to
absorb unfamiliar technical material (a codebase subsystem, a colleague's PR,
an integration contract) through AI-generated explanations, and burning out on
them.

- **Walls of prose** produced "textbook fatigue" — ~10k words/day of
  explanation is not readable, and comprehension collapses long before that.
- **Chunked prose** (shorter sections, headers) failed more slowly, not
  differently.
- **Bespoke per-lesson HTML explainers** were slow to generate, typo-prone,
  and had layout bugs (fixed-width boxes truncating labels) that no one
  should debug per lesson.
- **One giant architecture diagram** shows everything and teaches nothing in
  particular: there is no sequence, no claim, no place for the eye to start.

The bet: a *standardized, declarative* lesson representation plus a
*pre-debugged, reusable* shell beats bespoke output on speed **and**
correctness — and instructional-design research (segmenting, signaling,
whole-part-whole) tells you what the representation should express.

## Version history

### v1 — the atlas

A multi-level zoomable map (context → containers → detail) with a node tree,
detail panels, and source links. One page, one master model, several Mermaid
diagrams pre-rendered per level.

What it proved: self-contained HTML + vendored Mermaid + declarative data
works; multi-level semantic zoom is genuinely useful as a *reference*.

What it got wrong: an atlas is not a lesson. Learners were handed the whole
map and left to teach themselves. Navigation (which level? which node next?)
became the learner's job — exactly the cognitive load the tool was supposed
to remove.

### v2 — walkthrough bolted onto the atlas

Added a "chunk" mode: a sequence of steps, each dimming/highlighting parts of
the master diagrams, with prev/next navigation. Mouse-first controls,
movable detail modal, collapsible map.

What it proved: sequencing works; prev/next as the single navigation axis is
right; questions belong in the flow.

What it got wrong: chunks were *views by subtraction* — a step dimmed 80% of
a big diagram instead of drawing a small one. The layout was still the master
layout, so a 4-node idea was spread across a 30-node canvas. Label overload
and eye travel stayed.

### v3 — scenes + atlas (current)

The inversion: the **guided sequence of small, independently-laid-out scenes
is the product**; the atlas is a secondary reference one click away. Each
scene declares its own cast (3-7 nodes) and gets its own Mermaid layout, so
every scene is as small and readable as a hand-drawn whiteboard sketch.
The data model was normalized to support this (see below). A revision-gated
state line made the page safely driveable from chat.

### v4 — questions, detours, occlusion, relearning (current)

Driven by a five-lane research review (2026-08) on what interactivity is
worth building for real coursework. The convergent finding: **the chat
free-recall loop was already the top-tier mechanism** (free recall g≈0.8 vs
recognition g≈0.32); v4's leverage is scheduling and question design, not
widgets. Drag-and-drop label banks were rejected outright (recognition-tier,
no controlled-study support). "Interactivity" in v4 means the learner
predicts, recalls, chooses, and gets adaptive feedback — the page still has
**no input widget**; chat asks, accepts, grades, and routes.

What shipped: a typed question registry with chat-side rubrics; corequisite
prereq probes with inline detour scenes (`detour.returnTo` state); label
occlusion (the honest form of the drag-drop instinct); runtime edge
addressability; `?scene=` deep links and relative lesson links; and a
cross-lesson manifest + external successive-relearning bank
(`lessons.json` / `relearning.json`, validated by `--manifest`).

## The v4 product boundary

The console does not try to teach everything. Its niche is **constructing
and refreshing mental models**; it hands the learner to a better medium for
everything else, with a *referral-with-a-claim* (what the external resource
teaches and why they're leaving).

| Learning need | Preferred surface |
|---|---|
| Build a system-level mental model | Lesson Console |
| Refresh definitions and causal relationships | Console + chat recall |
| Diagnose forgotten prerequisites | Probe + console detour |
| Develop geometric intuition | External visualization (3B1B, immersivemath) |
| Continuous parameter manipulation | Simulator/visualization tool |
| Practice derivations or proofs | Notebook/chat |
| Implement an algorithm | IDE |
| Complete many repetitions | Relearning bank cadence or Anki |
| Explore a large algorithm state space | Existing specialist tool (VisuAlgo) |
| Review source-anchored architecture | Console atlas |

## Settled decisions

### Questions have identities independent of scenes

Scenes get split, reordered, and rewritten; moving a question must not erase
its relearning history. Hence the top-level `questions` registry with stable
ids and versions; the bank keys on `questionId`+`questionVersion` and treats
lesson/scene as presentation metadata. Rubrics carry conceptual items
(`expectedConcepts`, `misconceptions`) so they work for math and transfer,
not only diagram recall (`expectedElements`).

### Relearning state lives beside the lessons, not in the page

sessionStorage is tab-scoped, evaporates on close, and is unreadable by the
assistant — it cannot do cross-lesson scheduling, which is the entire point
(successive relearning is worth ~a letter grade; Rawson & Dunlosky). The
scheduler is the driving assistant; `relearning.json` is a plain file the
learner can read, reset, and back up. Rejected: an in-page SRS engine, and
all engagement mechanics (streaks, points, badges — overjustification risk
for exactly this kind of learner).

### Teaching mode ≠ review mode

"Questions never consecutive" is a guided-teaching heuristic (the validator
warns), **not a global invariant**. memoryStory recall prompts and prereq
probes are separate mechanisms and never count against it. Review sessions
driven from the bank do the opposite on purpose: consecutive, interleaved
questions across lessons, explanations withheld until after the attempt.

### Math renders as disciplined Unicode, not a math engine

Notation bites (`Wᵏ`, `√d_k`, `Xᵀ`, shape maps like `[T×d] @ [d×T] → [T×T]`)
render as Unicode and code spans in labels, annotations, and prompts.
Stacked fractions, rendered matrices, and multi-line equations are out of
scope — refer out rather than distort the math to fit Mermaid labels. If a
real lesson proves this insufficient, evaluating a vendored CSP-safe
renderer is a deliberate follow-up, not a casual dependency.

### Do not build (settled by the v4 research; needs new evidence to reopen)

Drag-and-drop label banks; build-the-diagram-yourself modes (author-provided
beats learner-generated on transfer — Stull & Mayer); continuous-manipulation
math widgets; a state-space explorer; in-page drill banks; any in-page SRS;
streaks/points/badges. Deferred until real use demands it: a page→chat
`LESSON_REPORT` channel (nothing typed into the page is gradable until it
exists — which is why the page has no inputs), and a bounded frontier-ledger
stepper (`interaction: {kind: "frontierLedger"}` — ≤9-node cast, prediction
gated per reveal; build only if static prediction demonstrably falls short).

### Judge v4 by learning, not activity

Success is: the learner reconstructs the model tomorrow; solves a
differently-worded problem; spots an unlabeled application; explains why the
attractive wrong answer fails; returns weeks later and finds only what
decayed; a detour restores progress without forced review. Explicitly valid
outcome: static prediction + chat feedback beating a fancier widget. Never
measured: widget count, time-in-console, completion %, clicks, streaks.

### One normalized graph; scenes and levels are views

Nodes and edges are declared exactly once. A scene or atlas level is a
*selection* (cast + optional explicit edge list + optional clusters/relabels)
over that graph. Consequences:

- No fact is written twice, so scenes and the atlas cannot drift apart.
- The validator can check every reference (edge endpoints, focus ⊆ cast,
  cluster membership, story mappings) because everything is an id.
- Authoring cost per scene is a handful of ids, not a diagram.

Rejected: per-scene hand-written Mermaid (drift, duplication, no
validation) — retained only as an explicit `syntax` escape hatch for diagram
types the graph model can't express (sequence, state).

### Build-time materialization, not runtime generation

`build.py` compiles views into static `<pre class="mermaid">` blocks inside
the page. The page never constructs diagram text at runtime.

- The exact same artifact renders under a local static server and under a
  strict-CSP sandbox (where only a native Mermaid renderer exists) — one
  pipeline, no environment-specific code path for diagram *content*.
- Errors surface at build time with names, not at view time with a blank
  pane.
- Output is deterministic and diffable; `--check` gives CI staleness
  detection for free.

Rejected: generating Mermaid text in the browser from the JSON blob. It's
more elegant on paper (smaller file, one source visible), but it moves every
failure to runtime, forks behavior between environments, and makes the page
depend on the shell's generator being bug-free forever.

### Scene discipline is enforced, not suggested

The validator hard-fails casts outside 2-9 and warns outside 3-7. This was
deliberate: the entire reason v2 failed was that nothing *stopped* a step
from showing 30 nodes. Pedagogy that isn't enforced regresses to the mean
under authoring pressure. (The atlas gets looser bounds — 2-30 — because a
reference map has a different job.)

### Chat asks the questions; the page only displays them

The scene's question appears on the page for context, but the *dialogue*
happens in the chat that's driving the lesson. Copy-pasting questions between
surfaces was tried and immediately felt like homework. The page is the
projector; the conversation is the teacher.

### Revision-gated state

The page tail carries a one-line `LESSON_STATE` JSON. The driving assistant
moves the learner by editing that line and bumping `revision`; the live-reload
poller picks it up within ~2s. The gate exists because of a real failure:
*any* file edit (typo fix, authoring a later scene) reloads the page, and
without the gate every reload teleported the learner back to the authored
position. Rule: **authored moves happen only when `revision` changes**;
otherwise the learner's sessionStorage position wins. Ad-hoc `focus`
highlights survive incidental reloads; the `note` banner is deliberately
ephemeral (it's a message, not state).

Rejected: WebSocket/SSE push (needs a real server; the page must also work
served from any dumb static host), and URL-fragment driving (pollutes
history, fights the learner's own navigation).

### Local-first, artifact-second

The primary surface is `python3 -m http.server` plus a browser pane beside
the chat. A hosted-artifact variant of the same file works (that's why
everything is CSP-safe), but publish-to-view round trips measured 30-90s
versus ~2s for local reload. Latency is pedagogically fatal: a question
answered a minute after it was asked is a different, worse interaction.

### Guided mode is a lesson, not a dashboard

An early experiment rendered a "PR deck" — cards for open PRs with status,
size, and risk bullets. Rejected on first contact: review *status* is what
`gh pr list` is for. The console teaches *content* — what a PR changes, how
the new path works, where the risk lives. See the PR-lesson section of the
[authoring guide](authoring-guide.md).

### The console is opt-in, not the default explanation surface

Plain sequential scenes in chat (Mermaid fences, one claim per message) are
cheaper, faster, and adequate for most explanations. The console earns its
setup cost when the subject needs a standing reference beside the
conversation, multi-level zoom, live investigation of a running system, or
is simply too big for chat scroll. The intended workflow is that the
assistant *offers* the console and the learner chooses — building one
unasked is the tool equivalent of answering a question with a slide deck.

### Memory stories are a capstone, not a gimmick

The optional `memoryStory` scene retells the finished lesson as one vivid
narrative with a validator-enforced 1:1 mapping to real components. Design
constraints (one story, at the end, complete mapping, causal/trust structure
preserved, dual-keyed recall questions) exist to keep the mechanism on the
distinctiveness side of the line and away from Mayer's seductive-details
effect. The honest status of the evidence is stated in the authoring guide.

## Shell invariants (learned the hard way)

These look like implementation trivia; each one is a scar.

1. **Never `display:none` a parked Mermaid diagram.** Mermaid measures with
   `getBBox()`, which returns zeros inside `display:none` subtrees and
   corrupts the layout permanently. Parked scenes stay rendered but
   absolutely positioned off-flow.
2. **Every element with a CSS `display:` rule needs an explicit
   `[hidden] { display: none }` companion.** The `hidden` attribute loses to
   any specificity, and the bug it causes (a menu open on load, a phantom
   banner) looks like anything but CSS.
3. **Fit-to-pane must refuse degenerate measurements.** Side-pane browsers
   can collapse the viewport to ~32px while the driving tool holds it; a fit
   computed then persists a garbage zoom. Fits under 200px are discarded and
   retried; auto-fits are never persisted, only explicit user zooms.
4. **Oversized centered flex content is unreachable.** `justify-content:
   center` pushes an overflowing child's leading edge outside the scrollable
   area. The pattern that works: `flex-start` alignment + `width:
   max-content; min-width: 100%` + `margin: auto` on the child (auto margins
   collapse to zero instead of going negative).
5. **A global `error` listener must show a notice, never suppress.** A shell
   bug that blanks the stage silently is indistinguishable from a bad lesson.

## Measured economics (v3 vs v2, same subject)

- Authored JSON: 24.7KB (v3, graph + scenes + levels + story) vs 17.9KB
  (v2, blob + hand Mermaid) — the story capstone accounts for most of the
  delta; scenes-as-views are roughly cost-neutral against hand-written
  chunk definitions.
- Shell: 52.9KB (v3) vs 54.3KB (v2) — the rewrite got smaller while adding
  the atlas, fallbacks, and state gating.
- Authoring a scene ≈ a claim + ~6 ids + 60 words; the layout is free.

## Open questions

- Cross-lesson linking (a lesson referencing another lesson's node) is
  unimplemented; single-file lessons keep hosting trivial and may be the
  right permanent answer.
- The `syntax` escape hatch bypasses the graph model entirely; if sequence
  diagrams turn out to be common, a normalized message-sequence model would
  be worth designing.
- Delayed-recall value of memory stories is asserted by theory, not yet
  measured on real lessons. Collect anecdotes before building more machinery.
