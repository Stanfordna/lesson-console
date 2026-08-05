# Lesson data schema

A lesson is one JSON document. `build.py` validates it exhaustively (every
error is reported by name; nothing is written until the data is clean) and
materializes the diagram views into the HTML page.

```
{
  "meta":         { ... },        required
  "graph":        { ... },        required — the single source of truth
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
| `question` | Optional comprehension question. Displayed by the page; *asked in chat* by the driving assistant. |
| `misconception` | Optional "an expert would assume X; here X is false" callout. |
| `transition` | Optional one-line bridge to the next scene. |
| `kind` | `scene` (default), `overview`, `recap`, `memoryStory`. |
| `syntax` | Raw-Mermaid escape hatch: supply a complete diagram (`sequenceDiagram`, `stateDiagram-v2`, …) instead of a graph view. `nodes`/`edges`/`clusters`/`relabel` are ignored; click-binding is best-effort. |

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

## Builder CLI

```bash
# full generation from a JSON source
python3 build.py lesson.json --template template.html --output lesson.html

# refresh generated blocks inside an existing page (after editing its JSON)
python3 build.py lesson.html [more.html ...]

# CI: fail if generated blocks are stale, write nothing
python3 build.py lesson.html --check
python3 build.py lesson.json --template template.html --output lesson.html --check
```

Output is deterministic (same input → byte-identical output) and written
atomically. In JSON mode the builder copies the vendored `mermaid.min.js`
beside the output if it isn't already there.
