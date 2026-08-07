# Lesson Console — AI authoring guide

This file instructs an AI assistant working in this repository (or using it
as a tool to teach) how to author, build, and drive lessons.

## What this is

A scene-based visual teacher. One JSON document per lesson; `build.py`
validates it and materializes static Mermaid diagrams into a self-contained
HTML page; a learner steps through claim-titled scenes while a chat assistant
drives the page and discusses each scene's question. Read
[README.md](README.md) first, then [docs/schema.md](docs/schema.md) and
[docs/authoring-guide.md](docs/authoring-guide.md).

## Non-negotiables

1. **Verify before you teach.** Author lessons from the actual code, spec, or
   diff — never from memory of "how systems like this usually work". Every
   node's `src` should point at real evidence (file + line, or a spec URL).
   A wrong lesson is worse than no lesson.
2. **The pedagogy rules in [docs/authoring-guide.md](docs/authoring-guide.md)
   are binding**, not advisory: one claim per scene, 3-7 node casts, claim
   titles, 30-80 word annotations, questions per the placement checklist and
   never on consecutive scenes, teach-the-delta for expert learners.
3. **Ask before building a console.** Sequential scenes directly in chat
   (Mermaid fences) are the cheaper default for explanations. Offer the
   console when the subject warrants it (standing reference, multi-level
   zoom, live investigation, too big for chat scroll) and let the user
   choose. Never present a built lesson as the answer to a question nobody
   asked you to build a lesson for.
4. **Never bypass the builder.** Don't hand-edit generated Mermaid blocks in
   a lesson HTML file; edit the JSON (or the authored blocks) and rebuild.
   `--check` must pass before committing.
5. **Keep lesson content out of this repo** unless it is a deliberately
   public example. Real lessons about private codebases live wherever the
   user keeps them, not here.

## Authoring workflow

```bash
# 1. start from the example
cp -r examples/oauth-authorization-code examples/<new>    # or work outside the repo

# 2. edit lesson.json: graph first, then scenes, then levels
# 3. build (validates everything; writes nothing on error)
python3 build.py path/to/lesson.json --template template.html --output path/to/lesson.html

# 4. serve beside the chat and eyeball every scene
python3 -m http.server 8766
```

Authoring order that works: declare the full `graph` (nodes with `label`,
`kind`, `summary`, `detail`, `src`; edges with labels) → write the scene
*sequence* as claims only → fill casts/focus/annotations scene by scene →
add atlas `levels` → optionally a `memoryStory` capstone → build and read
every scene at presentation width.

Common validator errors and what they mean:

- `edge references unknown node` — typo in `from`/`to`, or you renamed a node
  and missed an edge.
- `scene cast size N outside 2-9` — the scene is trying to do too much;
  split it.
- `focus id not in cast` / `explicit edge endpoint not in cast` — the view
  references something it doesn't show.
- `story node X unmapped` — every `storyNodes` entry must appear in exactly
  one `mapping[].storyNode`; a story element with no technical counterpart is
  decoration, which the design forbids.

## Driving a lesson from chat

The page tail contains one line:

```html
<script id="lesson-state">window.LESSON_STATE = {"mode":"guided","scene":"S1","level":null,"focus":[],"note":null,"pulse":false,"revision":1};</script>
```

- **To move the learner**: edit the line (scene/mode/level/focus/note) and
  **increment `revision`**. The page polls and applies within ~2s, showing
  `note` as a banner.
- **Any edit without a revision bump reloads but does not move the learner.**
  Use this freely for typo fixes and later-scene authoring while someone is
  mid-lesson.
- **Ask each scene's question in chat, in your own words**, and discuss the
  answer there. The page only displays the question text. Never ask the
  learner to copy anything between the page and the chat.
- Pace by the learner's replies. Do not pre-advance scenes; move when the
  conversation moves.
- `focus` is for ad-hoc "the thing we're discussing right now" highlights on
  top of the scene's own focus; it survives reloads until you clear it.
  It accepts **edge ids** too (`"focus": ["authz__token"]`) — use that to
  trace a traversal while discussing it.

## Grading, detours, drills, and relearning (v4)

The page never takes input; **every answer arrives in chat and you grade it
there**, against the question's `rubric`:

- Listen for each `expectedConcepts` entry, name any `misconceptions` you
  hear (they are the highest-value corrections), and treat
  `expectedElements` as diagram parts the answer should have touched.
  Grade the *reasoning*, not the wording. Verdicts: pass / partial / fail.
- **Prereq probes**: when a scene has a `prereqProbe`, ask it before
  teaching the scene. You decide pass or detour from the answer — a detour
  is corequisite support, never a gate. To detour:
  `{"scene": "<detourTo>", "detour": {"returnTo": "<scene>"}, …}` +
  revision bump. Return the same way (or the learner clicks ↩). Offer the
  detour even after a pass if the learner wants it; keep detours scoped to
  the one concept needed now.
- **Occlusion drills**: set `"occlude": true` (or a list of node/edge ids)
  with a revision bump, ask the learner to reconstruct the hidden labels in
  chat, grade, then clear. Clicking a node reveals it (self-check); scene
  changes clear occlusion automatically.
- **Entry deep links**: `lesson.html?scene=S4` opens at S4 (applies once) —
  use it when a review session needs one scene of one lesson.

**The relearning bank is the to-do list of durable memory.** State lives in
`relearning.json` beside the learner's `lessons.json` manifest (never in the
page; see [docs/schema.md](docs/schema.md) for both schemas — key by
questionId+version, lesson/scene are just presentation metadata):

- After grading any bank-worthy question, append the attempt to its item's
  `history`, update `result`/`lastAttempt`/`observedMisconceptions`, and
  reschedule `nextDue`: gap ≈20% of the desired retention interval — first
  pass +2 days, each later pass ×2-2.5; partial/fail → re-ask to criterion
  now, then next day.
- Retire an item after 2 consecutive session-separated passes; resurrect
  for exam sweeps. If a question's `version` bumps, keep history but reset
  scheduling.
- A review session: read due items (`nextDue <= today`, not retired),
  interleave concepts across lessons, open each via its deep link, ask in
  chat (mix kinds — recall, application, transfer), grade, reschedule.
  Withhold explanations until after the attempt.
- Validate after editing: `python3 build.py --manifest lessons.json`.
- Never add streaks, points, badges, or engagement metrics.

## Repo conventions

- `build.py` is Python 3.9+, standard library only — keep it that way.
- `template.html` is the single shell; every lesson is generated from it.
  Shell changes must preserve the invariants listed in
  [docs/design-decisions.md](docs/design-decisions.md) (no `display:none` on
  parked diagrams; explicit `[hidden]` rules; fit guards; overflow-safe
  centering; visible error notices).
- Tests: `python3 -m unittest discover tests`. Browser behavior has a manual
  checklist at [tests/browser-smoke.md](tests/browser-smoke.md) — run it
  after any template change.
- The example lesson (`examples/oauth-authorization-code/`) is a
  reference implementation of the authoring rules. If a schema change
  touches it, rebuild it and keep `--check` green.
- `mermaid.min.js` is vendored (see
  [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)); upgrade deliberately and
  re-run the browser smoke checklist when you do.
