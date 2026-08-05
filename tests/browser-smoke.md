# Browser smoke checklist

Manual checks for template changes. Build the example and serve:

```bash
python3 build.py examples/oauth-authorization-code/lesson.json \
  --template template.html --output examples/oauth-authorization-code/lesson.html
python3 -m http.server 8766
# → http://localhost:8766/examples/oauth-authorization-code/lesson.html
```

Run the list top to bottom in a normal-width window, then repeat the starred
items in a narrow (~500px) window.

## Load and guided mode

- [ ] Page loads with scene 1 rendered and fitted; no console errors. *
- [ ] Nothing is auto-open: no menu, no modal, no sheet, no banner. *
- [ ] Prev is disabled on scene 1; Next advances; the counter updates.
- [ ] Scene diagrams are each laid out independently (small scene ≠ cropped
      big diagram).
- [ ] The scene-list dropdown jumps to any scene; Escape closes it.
- [ ] Focused nodes show the focus ring; annotation, claim, and question
      render below the diagram. *
- [ ] Arrow keys change scenes — but NOT while a dialog/menu is open, and not
      when a modifier key is held.

## Diagrams and details

- [ ] Clicking a node opens the detail sheet (summary, detail markdown,
      source links, related chips); clicking a related chip navigates.
- [ ] Zoom + / − / fit work; **zooming far in stays reachable — scroll to the
      diagram's left/top edge** (the v3 overflow regression).
- [ ] Resize the window: the active diagram refits; no garbage zoom persists
      after shrinking the pane very small and restoring. *

## Atlas mode

- [ ] Atlas opens with the level picker and node tree; levels switch and
      each renders.
- [ ] Tree click focuses/opens the node; detail modal is draggable and
      **clamps back on-screen** (drag it off every edge; also resize while
      it's near an edge).
- [ ] Back to guided returns to the same scene, scroll, and zoom.

## Memory story (last scene)

- [ ] Story diagram renders; the mapping table shows story ↔ technical rows.
- [ ] Recall prompts appear in their own block, not as the scene question.
- [ ] "Show the literal diagram" toggles to the recap scene and back.

## State driving

- [ ] Edit `LESSON_STATE` (change scene + note, **bump revision**): page
      moves within ~2s and shows the note banner once.
- [ ] Edit the file WITHOUT bumping revision: page reloads but stays on the
      learner's scene/mode/zoom.
- [ ] Reload the tab manually: position preserved; note banner does NOT
      reappear.
- [ ] Set `"focus": ["auth_code"]` with a revision bump: ad-hoc highlight
      appears; then reload without a bump: highlight survives.

## Degradation

- [ ] Temporarily corrupt one scene's Mermaid block by hand: that scene shows
      the clickable node-list fallback; other scenes are unaffected; node
      clicks still open details. (Rebuild afterwards.)
- [ ] Rename `mermaid.min.js` away and reload: every diagram degrades to the
      fallback; no blank stage; restore the file.
- [ ] Throw from the console (`setTimeout(() => { throw new Error("x") })`):
      a visible error notice appears — never a silent blank.

## Theming

- [ ] Toggle OS dark/light: both themes readable, focus ring visible in both. *
