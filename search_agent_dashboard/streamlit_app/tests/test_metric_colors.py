"""One policy must drive numbers, charts, and the HTML table payloads."""

import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd

import app

DATA = Path(__file__).resolve().parents[1] / "data"


def load(name):
    return json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))


class MetricColorTests(unittest.TestCase):
    def test_every_threshold_has_ordered_inclusive_boundaries(self):
        for key, rule in app.METRIC_THRESHOLDS.items():
            with self.subTest(metric=key):
                good, warn = rule["good"], rule["warn"]
                self.assertIn(rule["unit"], {"ratio", "seconds", "USD", "/min", "count"})
                self.assertEqual(app.metric_level(key, good), "good")
                self.assertEqual(app.metric_level(key, warn), "warn")
                if rule["direction"] == "higher":
                    self.assertGreater(good, warn)
                    self.assertEqual(app.metric_level(key, good - .000001), "warn")
                    self.assertEqual(app.metric_level(key, warn - .000001), "bad")
                else:
                    self.assertLess(good, warn)
                    self.assertEqual(app.metric_level(key, good + .000001), "warn")
                    self.assertEqual(app.metric_level(key, warn + .000001), "bad")

    def test_invalid_values_do_not_look_healthy(self):
        for key in app.METRIC_THRESHOLDS:
            for value in (None, float("nan"), float("inf"), -1):
                with self.subTest(metric=key, value=value):
                    self.assertEqual(app.metric_cell(key, value)["level"], "neutral")
                    self.assertEqual(app.metric_cell(key, value)["text"], "—")
        self.assertEqual(app.metric_level("faithfulness", 1.01), "neutral")
        self.assertEqual(app.metric_text("faithfulness", 1.01), "—")
        with self.assertRaises(KeyError):
            app.metric_cell("unconfigured_metric", .80)

    def test_metric_specific_directions_and_units(self):
        cases = [("null_rate", .77, "bad"), ("schema_validity", .91, "warn"),
                 ("faithfulness", .88, "warn"), ("chunk_score", .82, "good"),
                 ("retry_rate", .09, "warn"), ("no_answer_rate", .06, "bad"),
                 ("latency_seconds", 4.2, "warn"), ("trace_cost", .018, "good"),
                 ("throughput_per_minute", 38, "good")]
        for key, value, expected in cases:
            self.assertEqual(app.metric_level(key, value), expected)
        self.assertEqual(app.metric_text("trace_cost", .018), "$0.018")
        self.assertEqual(app.metric_text("retry_rate", .09), "9%")
        self.assertEqual(app.metric_text("latency_seconds", 4.2), "4.2s")

    def test_context_and_categories_have_explicit_levels(self):
        for key in app.NEUTRAL_METRICS:
            self.assertEqual(app.metric_level(key, 99999), "neutral")
        self.assertEqual(app.category_cell("ERROR")["level"], "bad")
        self.assertEqual(app.category_cell("WARNING")["level"], "warn")
        self.assertEqual(app.category_cell("n/a")["level"], "neutral")

    def test_json_metrics_have_registered_keys(self):
        overview = load("overview")
        for kpi in overview["kpis"]:
            app.metric_cell(kpi["key"], kpi["score"])
            for detail in kpi["detail_metrics"]:
                app.metric_cell(detail["key"], detail["value"])
        for item in overview["ops_metrics"]:
            cell = app.metric_cell(item["key"], item["numeric_value"])
            self.assertEqual(cell["text"], item["value"])
            for detail in item.get("detail_metrics", []):
                app.metric_cell(detail["key"], detail["value"])
        for profile in load("profiles"):
            for metric in profile["metrics"]:
                app.metric_cell(metric["key"], metric["value"])

    def test_chart_colors_and_bands_match_number_thresholds(self):
        for key in ("generation_quality", "retrieval_performance", "knowledge_base_quality", "null_rate"):
            rule = app.METRIC_THRESHOLDS[key]
            values = [0, rule["warn"], rule["good"], 1]
            df = pd.DataFrame({"day": pd.date_range("2026-11-01", periods=4), key: values})
            fig = app.build_metric_trend_chart(df, [], key, key)
            self.assertEqual(list(fig.data[0].marker.color),
                             [app.METRIC_COLORS[app.metric_level(key, value)] for value in values])
            bands = [s for s in fig.layout.shapes if s.type == "rect"]
            self.assertEqual(len(bands), 3)
            for band in bands:
                level = app.metric_level(key, (band.y0 + band.y1) / 2)
                self.assertEqual(band.fillcolor, app.METRIC_COLORS[level])

    def test_changing_config_updates_both_cells_and_charts(self):
        rule = {**app.METRIC_THRESHOLDS["faithfulness"], "good": .80, "warn": .60}
        with patch.dict(app.METRIC_THRESHOLDS, faithfulness=rule):
            df = pd.DataFrame({"day": ["2026-11-01"], "faithfulness": [.82]})
            self.assertEqual(app.metric_cell("faithfulness", .82)["level"], "good")
            fig = app.build_metric_trend_chart(df, [], "faithfulness", "Faithfulness")
            self.assertEqual(fig.data[0].marker.color[0], app.METRIC_COLORS["good"])
            self.assertIn("80%", app.metric_hint("faithfulness"))

    def test_span_payload_uses_same_policy_without_mutating_data(self):
        for trace in load("traces"):
            original = copy.deepcopy(trace)
            display = app.decorate_trace(trace)
            self.assertEqual(trace, original)
            self.assertEqual(display["faithfulness_metric"], app.metric_cell("faithfulness", trace["faithfulness"]))
            for span in display["spans"]:
                root = span["parent_id"] is None
                metrics = span["display_metrics"]
                self.assertEqual(metrics["cost"], app.metric_cell("trace_cost" if root else "span_cost", span["cost"]))
                self.assertEqual(metrics["duration"]["level"], app.metric_level(
                    "latency_seconds" if root else "span_latency_seconds", span["duration_ms"] / 1000))
                self.assertEqual(metrics["status"], app.category_cell(span["status"]))


if __name__ == "__main__":
    unittest.main()