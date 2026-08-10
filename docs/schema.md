# Lesson data schema

A lesson is one JSON document. `build.py` validates it exhaustively (every
error is reported by name; nothing is written until the data is clean) and
materializes the diagram views into the HTML page.

```
{
  "meta":         { ... },        required
  "graph":        { ... },        required — the single source of truth
  "questions":    { ... },        optional — reusable typed questions (v4)
  "scenes":       [ ... ],        required — the guided walkthrough
  "levels":       [ ... ],        optional — the reference atlas
  "initialState": { ... }         optional — the LESSON_STATE baked at build
}
```

All ids (`graph.nodes` keys, edge endpoints, scene/level/story-node ids)
match `[a-zA-Z0-9_]+`. Generated Mermaid node ids equal graph node ids —
the shell's click-binding depends on this.

## meta

| field | required | notes |
|---|---|---|
| `title` | yes | Page title and header. |
| `repo`, `commit` | no | Shown as a provenance tag (`repo @ abc1234`). |
| `githubBase` | no | Prefix for `src` path links. **Pin a commit SHA**, not a branch, so links stay stable: `https://github.com/org/repo/blob/<sha>/`. |

## graph

### nodes — `{ id: { ... } }`

| field | notes |
|---|---|
| `label` | Display name (used on diagrams and in the atlas tree). |
| `kind` | Free-text chip shown on the detail card (`service`, `credential`, …). |
| `group` | Key into `graph.groups`; groups the atlas tree. |
| `summary` | One line under the detail title. |
| `detail` | Markdown (headings `##`, bold, italics, `code`, fenced blocks, lists, absolute links). ~60-120 words. |
| `src` | Evidence list. Each entry is either `{ "path", "line"?, "endLine"? }` (linked via `githubBase`, `#L42-L58` style) or `{ "label", "url", "kind"? }` for specs/docs (http(s) only). |
| `related` | Optional semantic cross-links (node ids). Direct graph neighbors are derived automatically — only set this for relationships that are *not* edges. |
| `shape` | `box` (default), `decision` (diamond), `round`. |

### edges — `[ { ... } ]`

| field | notes |
|---|---|
| `from`, `to` | Required node ids. |
| `label` | Edge label. |
| `style` | `solid` (default) or `dashed`. |
| `id` | Defaults to `from__to`. **Parallel edges between the same pair need explicit distinct ids.** |

## questions — reusable typed questions

Questions have **identities independent of scenes**: scenes get split and
reordered, and moving a question must not erase its relearning history (see
the relearning-bank section of [authoring-guide.md](authoring-guide.md)).
Registry entries are keyed by id (`[a-zA-Z0-9_]+`, convention `name_v1`):

```json
"questions": {
  "dot_product_similarity_v1": {
    "kind": "prediction",
    "prompt": "Which vector should score higher, and why?",
    "concepts": ["la:dot_product", "llm:similarity"],
    "rubric": {
      "expectedConcepts": ["directional alignment", "magnitude"],
      "misconceptions": ["dot product is Euclidean distance"],
      "expectedElements": ["dot", "q__k"]
    },
    "answer": "…",
    "version": 1
  }
}
```

| field | notes |
|---|---|
| `prompt` | Required. The only part the page displays. |
| `kind` | `freeRecall` (default), `cuedRecall`, `prediction`, `pretest`, `discrimination`, `application`, `transfer`, `calculation`, `explanation`, `ordering`. Shown as a small chip. |
| `concepts` | Curriculum concept tags (`ns:name` or plain) — a separate namespace from graph node ids. Used by the cross-lesson manifest and relearning bank. |
| `rubric` | The chat-side grading contract; **never rendered**. `expectedConcepts` / `misconceptions` are free text; `expectedElements` are graph node/edge ids (validated) for diagram-recall questions. |
| `answer` | Optional model answer (chat-side reference; never rendered). |
| `version` | Integer, default 1. Bump when rewording changes what the question tests; the relearning bank archives history and reschedules. |

The learner always answers **in chat**; the page has no input widget by
design. The driving assistant asks the question in its own words and grades
the reasoning against the rubric.

## scenes — the guided walkthrough

Ordered. Each scene is a *view* over the graph:

| field | notes |
|---|---|
| `id` | Required, unique (`S1`…). |
| `title` | Required. ≤6-word **navigation label phrased as a claim** ("Resolved ≠ succeeded"). |
| `claim` | The full-sentence idea the scene proves. Shown bold above the annotation. |
| `nodes` | The cast. Hard bounds 2-9; the validator warns outside 3-7 (the teaching sweet spot). |
| `focus` | Subset of `nodes` (list). Orange ring. |
| `edges` | Optional explicit edge-id list. Omitted → every edge with both endpoints in the cast is included. Explicit edges must keep both endpoints inside the cast. |
| `clusters` | Optional subgraph grouping: `{ "Label": [ids] }` or `[ { "id", "label", "nodes" } ]`. A node may appear in at most one cluster. |
| `relabel` | Per-scene label overrides `{ id: "text" }` (e.g. adding lifetimes on a detail view). |
| `dir` | `LR` (default), `TD`, `RL`, `BT`. |
| `annotation` | Markdown, ~30-80 words. What the diagram cannot show. |
| `question` | Optional. A string that exactly matches a `questions` registry key is a **reference**; any other string is a **literal prompt** (v3 form); an inline object is an anonymous typed question. Displayed by the page; *asked in chat* by the driving assistant. |
| `misconception` | Optional "an expert would assume X; here X is false" callout. |
| `transition` | Optional one-line bridge to the next scene. |
| `kind` | `scene` (default), `overview`, `recap`, `memoryStory`, `prereq`. |
| `prereqProbe` | Optional corequisite checkpoint (see below). |
| `syntax` | Raw-Mermaid escape hatch: supply a complete diagram (`sequenceDiagram`, `stateDiagram-v2`, …) instead of a graph view. `nodes`/`edges`/`clusters`/`relabel` are ignored; click-binding is best-effort. |

### prereq scenes and probes (corequisite detours)

A `kind:"prereq"` scene is a normal view with a different place in the flow:
it is **excluded from the linear sequence** (not counted in "N of M",
unreachable via prev/next, absent from the jump list) and is shown only as a
**detour**. Convention: place prereq scenes at the end of `scenes`.

A scene that depends on possibly-decayed knowledge declares a probe:

```json
"prereqProbe": {
  "question": "dot_product_similarity_v1",   // registry id or inline object
  "detourTo": "P1",                          // a kind:"prereq" scene
  "returnTo": "S4",                          // optional; both default to the
  "passTo":   "S4"                           // probing scene
}
```

The page displays the probe as a "checkpoint"; the driving assistant asks it
in chat and **decides pass/detour from the answer**. A failed probe opens
support, never blocks; passing skips remembered material; the learner may
request the detour even after passing. Detours must not recurse: a prereq
scene cannot carry its own `prereqProbe` (validated).

To move the learner into a detour, the assistant sets both the scene and the
way back, then bumps `revision`:

```json
{ "mode": "guided", "scene": "P1", "detour": { "returnTo": "S4" }, … }
```

While detoured, the scene bar shows "↩ detour", progress freezes at the
return scene, and "next" returns to `returnTo`. The detour survives
incidental reloads (it is part of the learner's local position).

### memoryStory scenes (optional capstone)

One per lesson, last, only for subjects with a stable multi-actor cast.

| field | notes |
|---|---|
| `storyNodes` / `storyEdges` | An inline mini-graph of story entities (same node/edge fields). |
| `mapping` | The 1:1 table. Entries: `{ "story", "technical" }` display text plus `{ "storyNode", "technicalNodes"[], "technicalEdges"[] }` ids. When ids are present the validator enforces that **every story node maps exactly once** — no decorative flourishes. |
| `recallQuestions` | Strings, or dual-keyed objects `{ "prompt", "promptMode", "answer", "answerMode", "refs"[] }` — asked in story terms, answered in system terms. The page lists prompts; the dialogue happens in chat. |
| `literalScene` | Scene id the "show the literal diagram" toggle swaps to (usually the recap). |

## levels — the reference atlas

Same view fields as scenes (`nodes`, `edges`, `clusters`, `relabel`, `dir`,
`syntax`), with hard cast bounds of 2-30 and no sweet-spot warning. Levels are
materialized by `build.py` exactly like scenes — the atlas cannot drift from
the graph.

## initialState

Baked into the page's `LESSON_STATE` line at build time:

```json
{ "mode": "guided", "scene": "S1", "level": null, "focus": [],
  "note": null, "pulse": false, "revision": 1 }
```

- `revision` (required integer) gates authored moves: the page applies this
  state only when `revision` differs from the last revision it applied
  (stored in `sessionStorage`). Any other reload preserves the learner's
  local scene, mode, level, and zoom.
- `focus` is an ad-hoc highlight layered on top of the scene's own focus;
  it survives incidental reloads. `note` is a banner shown only when the
  revision changes (deliberately ephemeral).
- `mode` is `guided` or `atlas`; `level` selects the atlas level when moving
  the learner to a specific map.
- `detour` (optional) is `{ "returnTo": "<non-prereq scene id>" }` — set it
  together with `scene` pointing at a prereq scene (see the prereq section).
- `occlude` (optional): `true` blanks every node/edge label on the current
  scene (a recall drill — recall is graded in chat); a list of node/edge ids
  blanks just those. Clicking an occluded node reveals its label. Occlusion
  clears when the learner changes scene.
- `focus` accepts **edge ids** as well as node ids — highlight a traversal
  with `"focus": ["authz__token"]`.

## lessons.json — the cross-lesson manifest

Lives **beside the lesson files** (not in this repo). Names each lesson,
maps the curriculum concept layer, and anchors the relearning bank.

```json
{ "version": 1,
  "concepts": {
    "la:dot_product":       { "label": "Dot product" },
    "llm:attention_scores": { "label": "Attention scores",
                              "requires": ["la:dot_product"] } },
  "lessons": [
    { "id": "llm-fundamentals", "title": "Fundamentals of LLMs",
      "path": "lesson-llm.html",
      "provides": ["llm:attention_scores"],
      "requires": ["la:dot_product"] } ] }
```

- Lesson ids are `[a-zA-Z0-9_-]+` and unique; `path` is relative to the
  manifest. Scene ids never carry curriculum semantics — concepts do.
- Validate with `python3 build.py --manifest lessons.json`: structure,
  paths, concept references (warnings for unknown tags and unsatisfied
  `requires`), and **cross-lesson question-id uniqueness** (read from each
  lesson's embedded data block).

## relearning.json — the successive-relearning bank

Sits beside `lessons.json`; validated by the same `--manifest` run. The
scheduler is the **driving assistant** — there is deliberately no in-page
SRS, and no streaks, points, or badges. Identity follows the question, not
the scene: `questionId` (+ `questionVersion`) is the primary key; `lesson` /
`scene` are current presentation metadata, updated freely when scenes are
split or reordered.

```json
{ "version": 1, "items": [
  { "questionId": "dot_product_similarity_v1", "questionVersion": 1,
    "concepts": ["la:dot_product"],
    "lesson": "llm-fundamentals", "scene": "S4",
    "added": "2026-08-07", "lastAttempt": "2026-08-07",
    "result": "partial", "nextDue": "2026-08-09",
    "observedMisconceptions": ["confused dot product with distance"],
    "history": [ { "date": "2026-08-07", "result": "partial" } ],
    "retired": false } ] }
```

- `result` ∈ `pass` / `partial` / `fail`; dates are ISO (`YYYY-MM-DD`).
- Anonymous inline questions key as `<lessonId>/<sceneId>/<slot>` where slot
  is `q` (scene question), `probe` (prereqProbe), or `r<i>` (recallQuestions
  index). Prefer registry ids for anything bank-worthy.
- Lifecycle (the driving protocol lives in [CLAUDE.md](../CLAUDE.md)):
  record every graded attempt in `history`; schedule with a gap ≈20% of the
  desired retention interval (first pass → +2 days, then ×2-2.5; partial or
  fail → re-ask to criterion in-session, then next day); retire at 2
  consecutive session-separated passes; a `version` bump on the question
  resets scheduling (history kept) so the reworded question is relearned.
- It is a plain JSON file: inspect, reset, or back it up like any other
  file; ask the driving assistant for a due/decay summary.

## Builder CLI

```bash
# full generation from a JSON source
python3 build.py lesson.json --template template.html --output lesson.html

# refresh generated blocks inside an existing page (after editing its JSON)
python3 build.py lesson.html [more.html ...]

# CI: fail if generated blocks are stale, write nothing
python3 build.py lesson.html --check
python3 build.py lesson.json --template template.html --output lesson.html --check

# validate a cross-lesson manifest + relearning bank; writes nothing
python3 build.py --manifest path/to/lessons.json

# validate, then write the lessons index page beside the manifest
python3 build.py --manifest path/to/lessons.json --index
python3 build.py --manifest path/to/lessons.json --index --check
```

The index page (`index.html`) is the landing page for the lesson library:
what is **due for review** today, deep-linked straight to the scene
(`lesson.html?scene=S4`) and labelled with the question's actual wording,
followed by every lesson with its scene count and concept tags, and any
lesson file in the directory that the manifest doesn't list. Due-ness is
computed **in the page** from embedded bank data rather than baked in at
build time, so the file stays deterministic (`--check` safe) and the list is
still correct tomorrow without regenerating anything. Nothing is written if
validation fails.

Output is deterministic (same input → byte-identical output) and written
atomically. In JSON mode the builder copies the vendored `mermaid.min.js`
beside the output if it isn't already there.
