"""Generator and validator tests for build.py.

Covers: valid minimal lesson, determinism, stale detection, malformed JSON,
missing/unknown edge endpoints, duplicate edge ids, out-of-cast focus and
explicit edges, cluster/relabel/dir/style/shape validity, cast-size bounds,
memory-story mapping validation, HTML-sensitive and Unicode labels, and the
CLI's json/html modes. Validation must never raise on malformed data.
"""

import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import build  # noqa: E402


def minimal_lesson():
    return {
        "meta": {"title": "Test lesson"},
        "graph": {
            "nodes": {
                "a": {"label": "Alpha"},
                "b": {"label": "Beta"},
                "c": {"label": "Gamma"},
            },
            "edges": [
                {"from": "a", "to": "b", "label": "sends"},
                {"from": "b", "to": "c"},
            ],
        },
        "scenes": [
            {"id": "S1", "title": "Alpha feeds Beta", "nodes": ["a", "b", "c"]},
        ],
    }


MINIMAL_TEMPLATE = """<!doctype html>
<title>placeholder</title>
<script>/* LESSON_STATE */ const LESSON_STATE = {"revision": 0}; </script>
<script type="application/json" id="lesson-data">
{}
</script>
<main>
      <!-- SCENES:BEGIN -->
      <!-- SCENES:END -->
      <!-- ATLAS:BEGIN -->
      <!-- ATLAS:END -->
</main>
"""


def errors_of(data):
    errors, _ = build.validate(data)
    return errors


def assert_error(testcase, data, fragment):
    errors = errors_of(data)
    testcase.assertTrue(
        any(fragment in e for e in errors),
        f"expected an error containing {fragment!r}, got: {errors}",
    )


def run_cli(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = build.run(argv)
    return code, buf.getvalue()


class ValidateBasics(unittest.TestCase):
    def test_minimal_lesson_is_clean(self):
        errors, warnings = build.validate(minimal_lesson())
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_never_raises_on_garbage(self):
        for garbage in (None, [], "x", 7,
                        {"graph": "nope", "scenes": "nope"},
                        {"meta": {}, "graph": {"nodes": "x", "edges": "y"},
                         "scenes": [None, 3, {"id": "S1"}]}):
            errors, _ = build.validate(garbage)
            self.assertTrue(errors)

    def test_missing_meta_title(self):
        data = minimal_lesson()
        data["meta"] = {}
        assert_error(self, data, "meta")


class ValidateEdges(unittest.TestCase):
    def test_missing_endpoint(self):
        data = minimal_lesson()
        data["graph"]["edges"].append({"to": "b"})
        assert_error(self, data, "missing 'from'")

    def test_unknown_endpoint(self):
        data = minimal_lesson()
        data["graph"]["edges"].append({"from": "nope", "to": "b"})
        assert_error(self, data, "unknown node 'nope'")

    def test_malformed_edge_is_reported_not_raised(self):
        data = minimal_lesson()
        data["graph"]["edges"].append("not an edge")
        assert_error(self, data, "must be an object")

    def test_duplicate_edge_ids(self):
        data = minimal_lesson()
        data["graph"]["edges"].append({"from": "a", "to": "b", "label": "again"})
        assert_error(self, data, "duplicate edge id")

    def test_parallel_edges_with_explicit_ids_are_fine(self):
        data = minimal_lesson()
        data["graph"]["edges"] = [
            {"id": "ab1", "from": "a", "to": "b"},
            {"id": "ab2", "from": "a", "to": "b"},
        ]
        self.assertEqual(errors_of(data), [])

    def test_bad_style(self):
        data = minimal_lesson()
        data["graph"]["edges"][0]["style"] = "wavy"
        assert_error(self, data, "style must be one of")


class ValidateViews(unittest.TestCase):
    def test_focus_outside_cast(self):
        data = minimal_lesson()
        data["scenes"][0]["focus"] = ["zz"]
        assert_error(self, data, "focus 'zz' not in nodes")

    def test_explicit_edge_endpoint_outside_cast(self):
        data = minimal_lesson()
        data["scenes"][0]["nodes"] = ["a", "b"]
        data["scenes"][0]["edges"] = ["b__c"]
        assert_error(self, data, "endpoint outside nodes")

    def test_unknown_explicit_edge(self):
        data = minimal_lesson()
        data["scenes"][0]["edges"] = ["nope__nada"]
        assert_error(self, data, "unknown edge id")

    def test_cluster_member_outside_cast(self):
        data = minimal_lesson()
        data["scenes"][0]["clusters"] = {"Grp": ["a", "zz"]}
        assert_error(self, data, "member 'zz' not in nodes")

    def test_node_in_two_clusters(self):
        data = minimal_lesson()
        data["scenes"][0]["clusters"] = {"G1": ["a"], "G2": ["a", "b"]}
        assert_error(self, data, "more than one cluster")

    def test_relabel_key_outside_cast(self):
        data = minimal_lesson()
        data["scenes"][0]["relabel"] = {"zz": "New"}
        assert_error(self, data, "relabel key 'zz' not in nodes")

    def test_bad_dir(self):
        data = minimal_lesson()
        data["scenes"][0]["dir"] = "UP"
        assert_error(self, data, "dir must be one of")

    def test_bad_shape(self):
        data = minimal_lesson()
        data["graph"]["nodes"]["a"]["shape"] = "blob"
        assert_error(self, data, "shape must be one of")

    def test_scene_cast_hard_bounds(self):
        data = minimal_lesson()
        data["scenes"][0]["nodes"] = ["a"]
        assert_error(self, data, "hard bounds 2-9")
        many = {f"n{i}": {"label": str(i)} for i in range(12)}
        data = minimal_lesson()
        data["graph"]["nodes"].update(many)
        data["scenes"][0]["nodes"] = list(many)
        assert_error(self, data, "hard bounds 2-9")

    def test_scene_sweet_spot_is_warning_only(self):
        data = minimal_lesson()
        data["scenes"][0]["nodes"] = ["a", "b"]
        errors, warnings = build.validate(data)
        self.assertEqual(errors, [])
        self.assertTrue(any("sweet spot" in w for w in warnings))

    def test_level_allows_big_casts(self):
        data = minimal_lesson()
        many = {f"n{i}": {"label": str(i)} for i in range(20)}
        data["graph"]["nodes"].update(many)
        data["levels"] = [{"id": "L1", "title": "Map",
                           "nodes": ["a", "b", "c"] + list(many)}]
        errors, warnings = build.validate(data)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_syntax_escape_hatch(self):
        data = minimal_lesson()
        data["scenes"][0] = {"id": "S1", "title": "Raw",
                             "syntax": "sequenceDiagram\n  A->>B: hi"}
        errors, warnings = build.validate(data)
        self.assertEqual(errors, [])
        data["scenes"][0]["nodes"] = ["a"]
        _, warnings = build.validate(data)
        self.assertTrue(any("ignored when syntax" in w for w in warnings))
        data["scenes"][0]["syntax"] = "   "
        assert_error(self, data, "syntax must be a non-empty string")


class ValidateQuestions(unittest.TestCase):
    def question_lesson(self):
        data = minimal_lesson()
        data["questions"] = {
            "alpha_feeds_beta_v1": {
                "kind": "prediction",
                "prompt": "What does Alpha send Beta?",
                "concepts": ["sample:flow", "plain_concept"],
                "rubric": {
                    "expectedConcepts": ["a message"],
                    "misconceptions": ["Beta polls Alpha"],
                    "expectedElements": ["a", "a__b"],
                },
                "answer": "A message over the a__b edge.",
                "version": 1,
            }
        }
        data["scenes"][0]["question"] = "alpha_feeds_beta_v1"
        return data

    def test_valid_registry_and_reference_is_clean(self):
        errors, warnings = build.validate(self.question_lesson())
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_v3_literal_string_question_still_valid(self):
        data = minimal_lesson()
        data["scenes"][0]["question"] = "What happens when Beta throws?"
        errors, warnings = build.validate(data)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_inline_object_question_is_valid(self):
        data = minimal_lesson()
        data["scenes"][0]["question"] = {"kind": "freeRecall",
                                         "prompt": "Reconstruct the flow."}
        errors, warnings = build.validate(data)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_registry_id_pattern(self):
        data = self.question_lesson()
        data["questions"]["bad id!"] = {"prompt": "x"}
        assert_error(self, data, "id not [a-zA-Z0-9_]+")

    def test_prompt_required(self):
        data = self.question_lesson()
        del data["questions"]["alpha_feeds_beta_v1"]["prompt"]
        assert_error(self, data, "prompt required")

    def test_bad_kind(self):
        data = self.question_lesson()
        data["questions"]["alpha_feeds_beta_v1"]["kind"] = "multipleChoice"
        assert_error(self, data, "kind must be one of")

    def test_bad_concept_id(self):
        data = self.question_lesson()
        data["questions"]["alpha_feeds_beta_v1"]["concepts"] = ["la:has space"]
        assert_error(self, data, "concept id not")

    def test_bad_version(self):
        data = self.question_lesson()
        data["questions"]["alpha_feeds_beta_v1"]["version"] = "1"
        assert_error(self, data, "version must be an integer")

    def test_expected_elements_checked_against_graph(self):
        data = self.question_lesson()
        data["questions"]["alpha_feeds_beta_v1"]["rubric"]["expectedElements"] = ["zz"]
        assert_error(self, data, "expectedElements id 'zz'")

    def test_expected_elements_accept_edge_ids(self):
        data = self.question_lesson()
        data["questions"]["alpha_feeds_beta_v1"]["rubric"]["expectedElements"] = ["b__c"]
        self.assertEqual(errors_of(data), [])

    def test_rubric_lists_must_be_strings(self):
        data = self.question_lesson()
        data["questions"]["alpha_feeds_beta_v1"]["rubric"]["misconceptions"] = [7]
        assert_error(self, data, "rubric.misconceptions must be a list of strings")

    def test_unreferenced_registry_question_warns(self):
        data = self.question_lesson()
        data["scenes"][0].pop("question")
        _, warnings = build.validate(data)
        self.assertTrue(any("never referenced" in w for w in warnings))

    def test_idlike_literal_with_registry_warns(self):
        data = self.question_lesson()
        data["scenes"][0]["question"] = "alpha_feeds_beta_v2"
        _, warnings = build.validate(data)
        self.assertTrue(any("matches no entry" in w for w in warnings))

    def test_consecutive_scene_questions_warn(self):
        data = minimal_lesson()
        data["scenes"].append({"id": "S2", "title": "Beta stores",
                               "nodes": ["b", "c", "a"], "question": "Q2?"})
        data["scenes"][0]["question"] = "Q1?"
        _, warnings = build.validate(data)
        self.assertTrue(any("consecutive scene questions" in w for w in warnings))

    def test_story_recall_does_not_count_as_consecutive(self):
        data = minimal_lesson()
        data["scenes"][0]["question"] = "Q1?"
        data["scenes"].append({
            "id": "S2", "title": "The tale", "kind": "memoryStory",
            "storyNodes": {"hero": {"label": "Hero"}},
            "mapping": [{"story": "Hero", "technical": "Alpha",
                         "storyNode": "hero", "technicalNodes": ["a"]}],
            "recallQuestions": ["Who is the hero?"],
        })
        _, warnings = build.validate(data)
        self.assertFalse(any("consecutive" in w for w in warnings))


class ValidatePrereq(unittest.TestCase):
    def prereq_lesson(self):
        data = minimal_lesson()
        data["questions"] = {
            "flow_probe_v1": {"kind": "cuedRecall",
                              "prompt": "What does the a->b edge carry?"},
        }
        data["scenes"] = [
            {"id": "S1", "title": "Alpha feeds Beta", "nodes": ["a", "b", "c"],
             "prereqProbe": {"question": "flow_probe_v1",
                             "detourTo": "P1", "returnTo": "S1"}},
            {"id": "S2", "title": "Beta stores", "nodes": ["a", "b", "c"]},
            {"id": "P1", "kind": "prereq", "title": "Edges carry messages",
             "nodes": ["a", "b", "c"]},
        ]
        return data

    def test_valid_prereq_lesson_is_clean(self):
        errors, warnings = build.validate(self.prereq_lesson())
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_probe_question_required_and_must_be_registry_id(self):
        data = self.prereq_lesson()
        del data["scenes"][0]["prereqProbe"]["question"]
        assert_error(self, data, "prereqProbe.question required")
        data = self.prereq_lesson()
        data["scenes"][0]["prereqProbe"]["question"] = "nope_v1"
        assert_error(self, data, "not a questions registry id")

    def test_probe_inline_question_object_is_valid(self):
        data = self.prereq_lesson()
        data["scenes"][0]["prereqProbe"]["question"] = {
            "kind": "cuedRecall", "prompt": "Inline probe?"}
        self.assertEqual(errors_of(data), [])

    def test_detour_to_required_and_must_be_prereq(self):
        data = self.prereq_lesson()
        del data["scenes"][0]["prereqProbe"]["detourTo"]
        assert_error(self, data, "detourTo required")
        data = self.prereq_lesson()
        data["scenes"][0]["prereqProbe"]["detourTo"] = "S9"
        assert_error(self, data, "not a scene id")
        data = self.prereq_lesson()
        data["scenes"][0]["prereqProbe"]["detourTo"] = "S2"
        assert_error(self, data, 'must be a kind:"prereq" scene')

    def test_return_and_pass_must_be_non_prereq_scenes(self):
        data = self.prereq_lesson()
        data["scenes"][0]["prereqProbe"]["returnTo"] = "P1"
        assert_error(self, data, "must not be a prereq scene")
        data = self.prereq_lesson()
        data["scenes"][0]["prereqProbe"]["passTo"] = "S9"
        assert_error(self, data, "prereqProbe.passTo 'S9' is not a scene id")

    def test_probe_on_prereq_scene_is_an_error(self):
        data = self.prereq_lesson()
        data["scenes"][2]["prereqProbe"] = {"question": "flow_probe_v1",
                                            "detourTo": "P1"}
        assert_error(self, data, "detours must not recurse")

    def test_orphan_prereq_scene_warns(self):
        data = self.prereq_lesson()
        del data["scenes"][0]["prereqProbe"]
        _, warnings = build.validate(data)
        self.assertTrue(any("not referenced by any prereqProbe" in w
                            for w in warnings))

    def test_question_plus_probe_warns(self):
        data = self.prereq_lesson()
        data["scenes"][0]["question"] = "Also a question?"
        _, warnings = build.validate(data)
        self.assertTrue(any("both question and prereqProbe" in w
                            for w in warnings))

    def test_all_prereq_scenes_is_an_error(self):
        data = minimal_lesson()
        data["scenes"] = [{"id": "P1", "kind": "prereq", "title": "Only",
                           "nodes": ["a", "b", "c"]}]
        assert_error(self, data, "at least one non-prereq scene")

    def test_prereq_scene_does_not_make_questions_consecutive(self):
        data = self.prereq_lesson()
        data["scenes"][2]["question"] = "Prereq check?"
        data["scenes"][0]["question"] = None
        _, warnings = build.validate(data)
        self.assertFalse(any("consecutive" in w for w in warnings))

    def test_initial_state_detour(self):
        data = self.prereq_lesson()
        data["initialState"] = {"revision": 1, "scene": "P1",
                                "detour": {"returnTo": "S1"}}
        self.assertEqual(errors_of(data), [])
        data["initialState"]["detour"] = {"returnTo": "S9"}
        assert_error(self, data, "detour.returnTo 'S9' is not a scene id")
        data["initialState"]["detour"] = {"returnTo": "P1"}
        assert_error(self, data, "detour.returnTo 'P1' must not be a prereq")
        data["initialState"]["detour"] = "S1"
        assert_error(self, data, "detour: must be an object")


class CompatGoldens(unittest.TestCase):
    """v4 must not change what v3 lessons validate to or materialize as."""

    GOLDEN_SCENES = (
        "<!-- SCENES:BEGIN generated by build.py from lesson-data; do not hand-edit -->\n"
        '      <section class="diag scene" data-scene="S1">\n'
        '<pre class="mermaid">\n'
        "flowchart LR\n"
        '  a["Alpha"]\n'
        '  b["Beta"]\n'
        '  c["Gamma"]\n'
        '  a -->|"sends"| b\n'
        "  b --> c\n"
        "</pre>\n"
        "      </section>\n"
        "      <!-- SCENES:END -->"
    )

    def test_v3_fixture_validates_clean(self):
        errors, warnings = build.validate(minimal_lesson())
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_v3_fixture_scenes_block_is_byte_identical(self):
        self.assertEqual(build.scenes_block(minimal_lesson()), self.GOLDEN_SCENES)


class ValidateStory(unittest.TestCase):
    def story_lesson(self):
        data = minimal_lesson()
        data["scenes"].append({
            "id": "S2", "title": "The tale", "kind": "memoryStory",
            "storyNodes": {
                "hero": {"label": "Hero"},
                "sword": {"label": "Sword"},
            },
            "storyEdges": [{"from": "hero", "to": "sword", "label": "wields"}],
            "mapping": [
                {"story": "Hero", "technical": "Alpha",
                 "storyNode": "hero", "technicalNodes": ["a"]},
                {"story": "Sword", "technical": "Beta",
                 "storyNode": "sword", "technicalNodes": ["b"]},
            ],
            "recallQuestions": [
                {"prompt": "What is the sword?", "answer": "Beta", "refs": ["b"]},
            ],
            "literalScene": "S1",
        })
        return data

    def test_valid_story_is_clean(self):
        errors, warnings = build.validate(self.story_lesson())
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_unmapped_story_node_fails_strict_mode(self):
        data = self.story_lesson()
        data["scenes"][1]["mapping"].pop()
        assert_error(self, data, "story nodes without a mapping")

    def test_free_text_mapping_warns(self):
        data = self.story_lesson()
        data["scenes"][1]["mapping"] = [{"story": "Hero", "technical": "Alpha"}]
        errors, warnings = build.validate(data)
        self.assertEqual(errors, [])
        self.assertTrue(any("free text only" in w for w in warnings))

    def test_unknown_mapping_ids(self):
        data = self.story_lesson()
        data["scenes"][1]["mapping"][0]["technicalNodes"] = ["zz"]
        assert_error(self, data, "technicalNodes id 'zz' unknown")

    def test_recall_question_refs_checked(self):
        data = self.story_lesson()
        data["scenes"][1]["recallQuestions"][0]["refs"] = ["zz"]
        assert_error(self, data, "refs id 'zz' unknown")

    def test_story_edge_unknown_node(self):
        data = self.story_lesson()
        data["scenes"][1]["storyEdges"].append({"from": "hero", "to": "zz"})
        assert_error(self, data, "unknown story node 'zz'")

    def test_unknown_literal_scene(self):
        data = self.story_lesson()
        data["scenes"][1]["literalScene"] = "S9"
        assert_error(self, data, "literalScene 'S9'")


class ValidateInitialState(unittest.TestCase):
    def test_revision_required(self):
        data = minimal_lesson()
        data["initialState"] = {"mode": "guided"}
        assert_error(self, data, "revision: required integer")

    def test_bad_mode_scene_level_focus(self):
        data = minimal_lesson()
        data["initialState"] = {"revision": 1, "mode": "cinema"}
        assert_error(self, data, "mode: must be one of")
        data["initialState"] = {"revision": 1, "scene": "S9"}
        assert_error(self, data, "'S9' is not a scene id")
        data["initialState"] = {"revision": 1, "level": "L9"}
        assert_error(self, data, "'L9' is not a level id")
        data["initialState"] = {"revision": 1, "focus": ["zz"]}
        assert_error(self, data, "focus id 'zz' unknown")


class Labels(unittest.TestCase):
    def test_mlabel_escapes_html(self):
        self.assertEqual(build.mlabel('<b>&"x"'), "&lt;b&gt;&amp;'x'")

    def test_mlabel_flattens_newlines(self):
        self.assertEqual(build.mlabel("one \n  two"), "one two")

    def test_mlabel_preserves_unicode(self):
        self.assertEqual(build.mlabel("café → naïve"), "café → naïve")

    def test_json_for_script_escapes_script_close(self):
        out = build.json_for_script({"x": "</script>"})
        self.assertNotIn("</script>", out)
        self.assertIn("<\\/script>", out)

    def test_derived_edge_id_never_raises(self):
        self.assertEqual(build.derived_edge_id(None, 3), "<edge 3>")
        self.assertEqual(build.derived_edge_id({"from": "a"}, 0), "<edge 0>")
        self.assertEqual(build.derived_edge_id({"id": "x"}, 0), "x")
        self.assertEqual(build.derived_edge_id({"from": "a", "to": "b"}, 0), "a__b")

    def test_html_sensitive_label_materializes_escaped(self):
        data = minimal_lesson()
        data["graph"]["nodes"]["a"]["label"] = '<script>"pwn"</script>'
        mer = build.view_mermaid(data["scenes"][0], data["graph"])
        self.assertNotIn("<script>", mer)
        self.assertIn("&lt;script&gt;'pwn'&lt;/script&gt;", mer)


class Materialization(unittest.TestCase):
    def test_implicit_edges_are_cast_scoped(self):
        data = minimal_lesson()
        data["scenes"][0]["nodes"] = ["a", "b"]
        mer = build.view_mermaid(data["scenes"][0], data["graph"])
        self.assertIn('a -->|"sends"| b', mer)
        self.assertNotIn("b --> c", mer)

    def test_explicit_edge_selection(self):
        data = minimal_lesson()
        data["scenes"][0]["edges"] = ["b__c"]
        mer = build.view_mermaid(data["scenes"][0], data["graph"])
        self.assertIn("b --> c", mer)
        self.assertNotIn("sends", mer)

    def test_clusters_relabel_shapes_styles(self):
        data = minimal_lesson()
        sc = data["scenes"][0]
        sc["clusters"] = {"Grp": ["a", "b"]}
        sc["relabel"] = {"a": "Alpha Prime"}
        data["graph"]["nodes"]["b"]["shape"] = "decision"
        data["graph"]["nodes"]["c"]["shape"] = "round"
        data["graph"]["edges"][1]["style"] = "dashed"
        mer = build.view_mermaid(sc, data["graph"])
        self.assertIn('subgraph view_c0 ["Grp"]', mer)
        self.assertIn('a["Alpha Prime"]', mer)
        self.assertIn('b{"Beta"}', mer)
        self.assertIn('c(["Gamma"])', mer)
        self.assertIn("b -.-> c", mer)

    def test_view_mermaid_is_deterministic(self):
        data = minimal_lesson()
        a = build.view_mermaid(data["scenes"][0], data["graph"])
        b = build.view_mermaid(copy.deepcopy(data["scenes"][0]),
                               copy.deepcopy(data["graph"]))
        self.assertEqual(a, b)

    def test_render_html_fills_all_zones(self):
        data = minimal_lesson()
        out = build.render_html(MINIMAL_TEMPLATE, data)
        self.assertIn("<title>Test lesson</title>", out)
        self.assertIn('"scene": "S1"'.replace('": "', '":"'), out.replace('": "', '":"'))
        self.assertIn('data-scene="S1"', out)
        self.assertIn("SCENES:BEGIN generated by build.py", out)
        self.assertIn("ATLAS:BEGIN generated by build.py", out)

    def test_render_html_missing_zone_is_build_error(self):
        broken = MINIMAL_TEMPLATE.replace("<!-- SCENES:BEGIN -->", "")
        with self.assertRaises(build.BuildError):
            build.render_html(broken, minimal_lesson())


class CliModes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / "template.html").write_text(MINIMAL_TEMPLATE, encoding="utf-8")
        (self.dir / "lesson.json").write_text(
            json.dumps(minimal_lesson()), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def build_json(self):
        return run_cli([str(self.dir / "lesson.json"),
                        "--template", str(self.dir / "template.html"),
                        "--output", str(self.dir / "lesson.html")])

    def test_json_mode_builds_deterministically(self):
        code, _ = self.build_json()
        self.assertEqual(code, 0)
        first = (self.dir / "lesson.html").read_text(encoding="utf-8")
        code, _ = self.build_json()
        self.assertEqual(code, 0)
        self.assertEqual(first, (self.dir / "lesson.html").read_text(encoding="utf-8"))

    def test_json_mode_copies_vendored_mermaid(self):
        (self.dir / "mermaid.min.js").write_text("// stub", encoding="utf-8")
        out_dir = self.dir / "out"
        out_dir.mkdir()
        code, _ = run_cli([str(self.dir / "lesson.json"),
                           "--template", str(self.dir / "template.html"),
                           "--output", str(out_dir / "lesson.html")])
        self.assertEqual(code, 0)
        self.assertEqual((out_dir / "mermaid.min.js").read_text(encoding="utf-8"),
                         "// stub")

    def test_check_detects_stale_and_fresh(self):
        self.build_json()
        code, out = run_cli([str(self.dir / "lesson.json"),
                             "--template", str(self.dir / "template.html"),
                             "--output", str(self.dir / "lesson.html"), "--check"])
        self.assertEqual(code, 0)
        self.assertIn("up to date", out)
        page = self.dir / "lesson.html"
        page.write_text(page.read_text(encoding="utf-8")
                        .replace("Alpha feeds Beta", "Tampered"), encoding="utf-8")
        code, out = run_cli([str(self.dir / "lesson.json"),
                             "--template", str(self.dir / "template.html"),
                             "--output", str(self.dir / "lesson.html"), "--check"])
        self.assertEqual(code, 1)
        self.assertIn("STALE", out)

    def test_html_mode_rematerializes_and_checks(self):
        self.build_json()
        page = self.dir / "lesson.html"
        code, _ = run_cli([str(page), "--check"])
        self.assertEqual(code, 0)
        tampered = page.read_text(encoding="utf-8").replace(
            'a -->|"sends"| b', 'a -->|"hacked"| b')
        page.write_text(tampered, encoding="utf-8")
        code, out = run_cli([str(page), "--check"])
        self.assertEqual(code, 1)
        self.assertIn("STALE", out)
        code, _ = run_cli([str(page)])
        self.assertEqual(code, 0)
        self.assertIn('a -->|"sends"| b', page.read_text(encoding="utf-8"))

    def test_malformed_json_source_reports_no_traceback(self):
        (self.dir / "bad.json").write_text("{not json", encoding="utf-8")
        code, out = run_cli([str(self.dir / "bad.json"),
                             "--template", str(self.dir / "template.html"),
                             "--output", str(self.dir / "x.html")])
        self.assertEqual(code, 2)
        self.assertIn("ERROR", out)

    def test_invalid_lesson_writes_nothing(self):
        data = minimal_lesson()
        data["scenes"][0]["focus"] = ["zz"]
        (self.dir / "lesson.json").write_text(json.dumps(data), encoding="utf-8")
        code, out = self.build_json()
        self.assertEqual(code, 1)
        self.assertIn("nothing written", out)
        self.assertFalse((self.dir / "lesson.html").exists())

    def test_unicode_survives_round_trip(self):
        data = minimal_lesson()
        data["graph"]["nodes"]["a"]["label"] = "café → naïve"
        (self.dir / "lesson.json").write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8")
        code, _ = self.build_json()
        self.assertEqual(code, 0)
        out = (self.dir / "lesson.html").read_text(encoding="utf-8")
        self.assertIn('a["café → naïve"]', out)


if __name__ == "__main__":
    unittest.main()
