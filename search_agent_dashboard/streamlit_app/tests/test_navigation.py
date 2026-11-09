import json
import math
from pathlib import Path
import unittest

import navigation

DATA = Path(__file__).resolve().parents[1] / "data"


def load(name):
    return json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))


class NavigationTests(unittest.TestCase):
    def setUp(self):
        self.state = {}
        navigation.initialize(self.state, ["A", "B", "C"])

    def validate(self, language="All"):
        navigation.validate(self.state, load("customers"), load("batches"), load("documents"), load("traces"), language)

    def test_initial_state_does_not_auto_drill(self):
        self.validate()
        self.assertEqual(self.state["selected_profile_id"], "A")
        self.assertIsNone(self.state["selected_customer_id"])
        self.assertIsNone(self.state["selected_batch_id"])

    def test_overview_can_open_another_profiles_batch(self):
        navigation.navigate(self.state, "Profiles", profile_id="C", customer_id="cust_c1", batch_id="B-14")
        self.validate()
        self.assertEqual(self.state["active_tab"], "Profiles")
        self.assertEqual(self.state["selected_profile_id"], "C")
        self.assertEqual(self.state["selected_batch_id"], "B-14")
        self.assertIsNone(self.state["selected_document_id"])

    def test_selection_survives_unrelated_reruns(self):
        navigation.navigate(self.state, "Profiles", profile_id="A", customer_id="cust_a1", batch_id="B-2", document_id="D-2002")
        self.validate()
        self.validate()
        self.assertEqual(self.state["selected_document_id"], "D-2002")

    def test_breadcrumb_clears_only_descendants(self):
        navigation.navigate(self.state, "Profiles", profile_id="A", customer_id="cust_a1", batch_id="B-2", document_id="D-2001")
        navigation.navigate(self.state, "Profiles", profile_id="A", customer_id="cust_a1")
        self.assertEqual(self.state["selected_customer_id"], "cust_a1")
        self.assertIsNone(self.state["selected_batch_id"])
        self.assertIsNone(self.state["selected_document_id"])

    def test_profile_change_clears_old_drilldown(self):
        navigation.navigate(self.state, "Profiles", profile_id="A", customer_id="cust_a1", batch_id="B-2")
        navigation.navigate(self.state, "Profiles", profile_id="B")
        self.validate()
        self.assertEqual(self.state["selected_profile_id"], "B")
        self.assertIsNone(self.state["selected_customer_id"])

    def test_language_change_clears_hidden_batch(self):
        navigation.navigate(self.state, "Profiles", profile_id="A", customer_id="cust_a1", batch_id="B-2", document_id="D-2001")
        self.validate("German")
        self.assertEqual(self.state["selected_customer_id"], "cust_a1")
        self.assertIsNone(self.state["selected_batch_id"])
        self.assertIsNone(self.state["selected_document_id"])

    def test_mixed_batch_survives_hidden_document(self):
        navigation.navigate(self.state, "Profiles", profile_id="A", customer_id="cust_a1", batch_id="B-3", document_id="D-3001")
        self.validate("German")
        self.assertEqual(self.state["selected_batch_id"], "B-3")
        self.assertIsNone(self.state["selected_document_id"])

    def test_trace_change_resets_span_state(self):
        navigation.navigate(self.state, "Traces", trace_id="t-9f21")
        self.state["selected_span_id"] = "vector_search"
        self.state["collapsed_span_ids"] = ["search"]
        navigation.navigate(self.state, "Traces", trace_id="t-9f20")
        self.assertEqual(self.state["selected_trace_id"], "t-9f20")
        self.assertIsNone(self.state["selected_span_id"])
        self.assertEqual(self.state["collapsed_span_ids"], [])

    def test_language_filter_clears_hidden_trace(self):
        navigation.navigate(self.state, "Traces", trace_id="t-9f21")
        self.validate("German")
        self.assertIsNone(self.state["selected_trace_id"])


class SpanDataTests(unittest.TestCase):
    def test_span_trees_have_valid_parents_and_consistent_costs(self):
        for trace in load("traces"):
            with self.subTest(trace=trace["id"]):
                spans = trace["spans"]
                lookup = {s["id"]: s for s in spans}
                self.assertEqual(len(spans), len(lookup))
                roots = [s for s in spans if s["parent_id"] is None]
                self.assertEqual(len(roots), 1)
                self.assertTrue(math.isclose(roots[0]["cost"], trace["cost"]))
                self.assertTrue(math.isclose(sum(s["self_cost"] for s in spans), trace["cost"]))
                self.assertEqual(roots[0]["duration_ms"], float(trace["latency"].rstrip("s")) * 1000)
                for span in spans:
                    seen = set()
                    current = span
                    while current["parent_id"] is not None:
                        self.assertNotIn(current["id"], seen)
                        seen.add(current["id"])
                        current = lookup[current["parent_id"]]
                    self.assertIn("input", span)
                    self.assertIn("output", span)

    def test_retrieval_spans_link_to_existing_documents(self):
        documents = {d["id"]: d for d in load("documents")}
        for trace in load("traces"):
            for span in trace["spans"]:
                attributes = span["attributes"]
                if "document_id" in attributes:
                    self.assertEqual(documents[attributes["document_id"]]["batch_id"], attributes["batch_id"])


if __name__ == "__main__":
    unittest.main()