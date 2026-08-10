# Lesson Console

A scene-based visual teacher for technical subjects: one self-contained HTML
page per lesson, walking a learner through a sequence of small, claim-titled
diagrams — with a full reference map one click away.

## Why this exists

The constraint on learning unfamiliar technical material is no longer access
to information; it is getting an accurate mental model into your head without
cognitive burnout. Walls of prose fail. Chunked prose fails more slowly.
A single giant architecture diagram fails differently — it shows everything
and teaches nothing in particular.

Lesson Console is built around a **scene discipline** borrowed from
instructional design (segmenting, signaling, whole-part-whole, retrieval
practice):

> **claim → one small diagram (3-7 nodes) → a few lines of why → optional
> question → next scene**

Each scene is an independently laid-out diagram showing only the cast that
proves its claim. The learner has exactly one navigation axis: previous /
next. Everything else — the full multi-level map, node details, zoom — is
secondary and stays out of the way until asked for.

## What a lesson looks like

Guided mode (the default):

```
┌────────────────────────────────────────────────────────┐
│ Lesson title                              Atlas   •••  │
├────────────────────────────────────────────────────────┤
│ ‹   2 of 8   The front channel is hostile           ›  │
├────────────────────────────────────────────────────────┤
│                                                        │
│              SMALL, AUTO-FITTED DIAGRAM                │
│              (click a node → bottom sheet)             │
│                                                        │
├────────────────────────────────────────────────────────┤
│ Everything passing through the browser is visible and  │
│ tamperable — the exact-match redirect URI is the       │
│ front channel's main defense.                          │
│ ? Why is intercepting the code useless to an attacker? │
└────────────────────────────────────────────────────────┘
```

**Atlas mode** (one click) is the full reference map: multiple semantic
levels (context → flow → detail), a collapsible node tree, zoom and pan, and
draggable detail cards with pinned source links. Entering and leaving the
atlas preserves your place in the lesson.

An optional **memory story** capstone retells the finished lesson as one
vivid narrative with a complete 1:1 mapping back to the real components
(OAuth as a nightclub: the dissolving wristband is the access token, the
coat-check ticket is the refresh token), plus a toggle back to the literal
diagram. Distinctive imagery is the recall mechanism; the mapping table keeps
it honest.

## Features

- **One normalized graph per lesson** — nodes and edges declared once in
  JSON; scenes *and* atlas levels are declarative views selecting subsets.
  No duplicated diagram text, no drift.
- **Materialized rendering** — `build.py` validates every reference and
  writes static Mermaid blocks into the page. A local server and a strict-CSP
  static host render through the identical pipeline; nothing is generated at
  runtime.
- **Self-contained output** — one HTML file (plus a vendored `mermaid.min.js`
  beside it for local use). Publish anywhere static; external requests are
  never needed, so it survives strict Content-Security-Policy sandboxes.
- **Driveable by a chat agent** — the file starts with a one-line
  `LESSON_STATE`. An AI (or a human) edits that line to move the lesson;
  the page live-reloads on localhost within ~2s. A `revision` counter gates
  authored moves: reloads without a revision bump never steal the learner's
  place, zoom, or mode.
- **Typed questions with grading rubrics** — a per-lesson `questions`
  registry (stable ids, kinds like `prediction`/`freeRecall`/`transfer`,
  concept tags, rubrics). The page displays the prompt; the learner answers
  **in chat**, where the driving assistant grades reasoning against the
  rubric. The page deliberately has no input widget.
- **Prerequisite probes and inline detours** — corequisite, never a gate: a
  scene checkpoint the assistant asks before continuing; a shaky answer
  detours to a `kind:"prereq"` scene outside the main sequence and returns
  exactly where the learner left off.
- **Label occlusion** — blank the labels on the scene the learner just
  studied (`occlude` state or the ••• menu) and have them reconstruct it in
  chat; clicking a node reveals it.
- **Edge addressability** — `focus` accepts edge ids, so chat can highlight
  a traversal, not just boxes.
- **Deep links and cross-lesson structure** — `lesson.html?scene=S4` entry
  links (applied once, never fighting the learner's navigation), relative
  lesson-to-lesson links, and a `lessons.json` manifest + `relearning.json`
  successive-relearning bank validated by `build.py --manifest`.
- **A library index** — `build.py --manifest lessons.json --index` generates
  the landing page for a lesson directory: what's due for review today
  (deep-linked to the exact scene), then every lesson with its concepts.
- **Mouse-first, keyboard-friendly** — prev/next buttons, jump list, click-
  to-open details (nothing ever auto-opens), Escape closes overlays, arrow
  keys work when no dialog is open.
- **Failure-tolerant** — a diagram that fails to render degrades to a
  clickable node list (the Mermaid source is kept for late recovery), and
  shell errors surface a visible notice instead of a silent blank page.

## Quickstart (five minutes)

```bash
git clone https://github.com/Stanfordna/lesson-console.git
cd lesson-console

# build the example lesson from its JSON source
python3 build.py examples/oauth-authorization-code/lesson.json \
  --template template.html \
  --output examples/oauth-authorization-code/lesson.html

# serve and open
python3 -m http.server 8766
# → http://localhost:8766/examples/oauth-authorization-code/lesson.html
```

Serving matters: `file://` URLs get no charset header and block the
live-reload poller. Any static file server works.

## Authoring a lesson

1. Copy `examples/oauth-authorization-code/lesson.json` as a starting point.
2. Declare your `graph` (nodes with labels, summaries, details, source
   references; edges with labels). Declare each node **once**.
3. Write `scenes`: an ordered sequence of views over the graph, each with a
   claim, a 3-7 node cast, a focus, and a short annotation. See
   [docs/authoring-guide.md](docs/authoring-guide.md) for the pedagogy rules —
   they matter more than the schema.
4. Define atlas `levels` the same way (bigger casts allowed).
5. Build. The validator reports every broken reference by name; nothing is
   written until the data is clean. `--check` supports CI.

Full schema reference: [docs/schema.md](docs/schema.md).
Design history and rejected alternatives:
[docs/design-decisions.md](docs/design-decisions.md).

## Driving a lesson from chat (AI-assisted teaching)

The intended workflow with an AI assistant (see [CLAUDE.md](CLAUDE.md)):

1. The assistant verifies the subject matter (reads the actual code/spec),
   authors `lesson.json`, builds, and serves it beside the chat.
2. As the conversation advances, the assistant edits the one-line
   `LESSON_STATE` — `{"mode":"guided","scene":"S4","focus":[],"note":"…",
   "pulse":true,"revision":7}` — and **bumps `revision`**. The page reloads
   and moves to the authored position, showing the note banner.
3. The assistant asks the scene's question in chat, in its own words,
   and grades the answer there against the question's rubric.
   The page displays the question; the dialogue happens in chat.
4. Edits that don't bump `revision` (typo fixes, later-scene authoring)
   reload the page but leave the learner exactly where they were.
5. Probes, detours (`"detour": {"returnTo": …}`), occlusion drills
   (`"occlude": true`), and the relearning cadence are described in
   [CLAUDE.md](CLAUDE.md) and [docs/schema.md](docs/schema.md).

## Browser and runtime support

- Output pages: current Chrome/Edge/Firefox/Safari (ES5-flavored JS, no
  framework, no build step at runtime).
- `build.py`: Python 3.9+, standard library only.
- Vendored [Mermaid](https://mermaid.js.org/) v11 (UMD) renders diagrams
  locally; environments with their own Mermaid renderer (e.g. artifact
  sandboxes) are detected and the vendored copy stands down per-diagram.

## Development

```bash
python3 -m unittest discover tests        # generator + validator tests
python3 build.py template.html --check    # template self-test (determinism)
```

Manual browser checks live in [tests/browser-smoke.md](tests/browser-smoke.md).
CI runs the unit tests plus staleness checks on the template and the example.

## Limitations

- The normalized graph materializes **flowcharts**. Scenes may supply a raw
  Mermaid block (`"syntax": "sequenceDiagram\n..."`) as an escape hatch for
  sequence/state/ER diagrams; node click-binding is best-effort there.
- Lessons are single files by design; cross-lesson structure lives in an
  optional `lessons.json` manifest beside them (relative links + `?scene=`
  deep links hop between pages).
- The revision-gated state model is deliberately simple: one authored
  position, one local position. It does not merge concurrent edits.

## License

[MIT](LICENSE). Vendored third-party code is listed in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
