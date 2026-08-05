# Authoring guide: the pedagogy is the product

The schema tells you what's *valid*; this guide tells you what *teaches*.
The rules below are distilled from instructional-design research (cognitive
load theory, Mayer's multimedia principles, retrieval practice, worked
examples, expertise reversal) and from iterating on real lessons. Treat them
as binding as the schema.

## The scene discipline

A scene is the unit of teaching:

> **claim → one small diagram → a few lines of why → optional question**

1. **One claim per scene, never two.** If describing a scene needs "and",
   split it. *(segmenting)*
2. **The title IS a claim, not a topic label.** "Resolved ≠ succeeded", not
   "The update promise". The title asserts what the diagram proves.
   *(signaling)*
3. **3-7 nodes per scene; 4-5 is the sweet spot.** Working memory is spent on
   the new material, not on holding diagram clutter. The validator warns
   outside 3-7. *(intrinsic load)*
4. **Labels live on the diagram** — on nodes and edges, never in a separate
   legend the eye must shuttle to. *(spatial contiguity / split attention)*
5. **The annotation adds only what the diagram cannot show**: the why, the
   risk, the deviation from the standard pattern. If a fact is fully carried
   by the picture, its text budget is zero. 30-80 words. *(coherence,
   redundancy)*
6. **Prefer one concrete worked example over the abstract rule.** "An
   attacker steals `?code=Splxl…` — to redeem it they need the secret AND the
   verifier" beats "the code is protected by multiple factors." *(worked
   examples)*
7. **Keep the visual grammar constant.** Same kind of thing → same shape,
   lesson-wide. Decision diamonds for gates, dashed edges for async/degraded
   paths. *(schema reuse)*
8. **Prefer left-to-right layouts**; go top-down only when the flow is
   genuinely deep or branchy.

## Sequencing a lesson

9. **5-9 scenes.** Past nine, split into a second lesson rather than pushing
   through fatigue.
10. **Whole → part → whole.** Open with an overview scene framing the entire
    story; descend into parts; resurface every 2-3 detail scenes; end on a
    recap that reassembles the parts around the takeaway. *(whole-part-whole)*
11. **Order scenes by data/control flow**, never by file layout or
    alphabetical anything. The sequence should match the causal model you
    want in the learner's head.
12. **Use `transition`** when the jump between scenes needs a conceptual
    bridge ("Assume the push lands somewhere. Next problem: the id it needs
    may not exist yet.").

## Questions (retrieval practice, used sparingly)

Ask only where prediction or recall genuinely strengthens the model:

- right after the **overview**, as a prediction ("which box never sees a
  token?");
- right after a **non-obvious mechanism** — the spot where the expert's
  prior model is wrong;
- at a **branch** ("what happens when the input is X?") before revealing it;
- immediately before a **return to the overview** (consolidation);
- at the **final synthesis**.

**Never two scenes in a row.** Omit questions on setup scenes, and never ask
something whose answer is a label currently on screen — for an expert
audience that reads as condescension and adds load without benefit.
*(expertise reversal)*

The page **displays** the question; the driving assistant **asks** it in
chat, in its own words, and discusses the answer there. Learners never copy
questions between surfaces.

## Teaching experts

Your learner is an expert in general, a novice only in this system.

13. **Teach only the delta.** Every scene isolates the difference between
    "what an expert would assume" and "what this system actually does".
    Never re-teach HTTP, OAuth basics, git, or generic patterns they already
    hold. *(expertise reversal)*
14. **Use `misconception` for the trap**: "an expert would assume X; here X
    is false." These fields are often the highest-value line in the lesson.
15. **Diagram + restatement of the same fact underperforms the diagram
    alone** for high-prior-knowledge learners. Don't narrate the picture.
    *(redundancy)*

## Memory stories (optional capstone)

For subjects with a stable multi-actor cast (protocols, auctions, pipelines
with fixed roles), one final `memoryStory` scene can retell the finished
lesson as a vivid narrative. The mechanism is distinctiveness (von Restorff)
plus dual coding (verbal structure + concrete imagery); the danger is
Mayer's *seductive details* — amusing decoration that steals attention
without encoding anything.

Guardrails, enforced by the validator where possible:

- **Complete 1:1 mapping.** Every story element resolves to a real
  component (`storyNode` → `technicalNodes`). No decorative flourishes.
- **Preserve causal order, ownership, and trust boundaries.** If component A
  can't see B's secret, the story analog can't either.
- **One story per lesson, at the end**, after the accurate model is taught —
  never a different metaphor per scene.
- **Make the images vivid, exaggerated, comic.** Ordinary images don't
  stick; distinctiveness is earned at the image level, never at the expense
  of mapping fidelity.
- **Recall questions are dual-keyed**: asked in story terms, answered in
  system terms (or vice versa) — they test the mapping, not plot recall.
- Skip stories for one-off investigations and single-function dives; with no
  stable cast they collapse into forced whimsy.

Honest evidence note: the ingredients (dual coding, von Restorff,
seductive-details harm) are well-replicated; the specific claim that a
complete mapping keeps a story on the helpful side of the line is a
plausible synthesis, not a tested result. Watch whether your stories
actually survive a week.

## PR-review lessons

A pull request is a lesson subject like any other. Teach the **content**:

- what behavior changes;
- how the changed execution path works;
- which assumptions and invariants matter;
- where the risky scrutiny points are;
- what the diff does *not* cover;
- what a reviewer should retain after closing it.

Organize by conceptual scenes, never by files or diff hunks. A proven arc:
*what-this-PR-claims* (overview) → per-concern change flow → *the thing
nobody mentioned* → *withhold approval until…* (recap). Source links can
point at exact hunks. Status, CI, and queue position are not lesson
material.

## Subject-shape templates

- **Subsystem**: the whole pipeline (overview) → one scene per gate/stage →
  failure/blind-spot scenes → "what survives" recap.
- **Investigation**: symptom → instrumentation → each ruled-out theory (one
  scene, named) → root cause → the transferable lesson.
- **Protocol/integration**: actors and channels (overview) → each exchange →
  credential lifetimes → failure modes → recap (+ a memory story; protocols
  are the best-fit subject).
