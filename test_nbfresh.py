import json
import tempfile
import unittest
from pathlib import Path

import nbfresh


def notebook(source="x = 1", output="1"):
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "cells": [
            {"cell_type": "markdown", "id": "m", "metadata": {}, "source": ["# Demo"]},
            {
                "cell_type": "code",
                "id": "c1",
                "metadata": {},
                "execution_count": 1,
                "source": [source],
                "outputs": [{"name": "stdout", "output_type": "stream", "text": [output]}],
            },
        ],
        "metadata": {},
    }


class WitnessTests(unittest.TestCase):
    def test_same_notebook_is_fresh(self):
        manifest = nbfresh.make_manifest(notebook())
        report = nbfresh.check(notebook(), manifest)
        self.assertTrue(report["ok"])
        self.assertEqual(report["cells"][0]["status"], "fresh_under_manifest")

    def test_source_change_fails_closed(self):
        report = nbfresh.check(notebook("x = 2"), nbfresh.make_manifest(notebook()))
        self.assertFalse(report["ok"])
        self.assertEqual(report["cells"][0]["status"], "source_changed")

    def test_missing_output_is_distinct(self):
        current = notebook()
        current["cells"][1]["outputs"] = []
        report = nbfresh.check(current, nbfresh.make_manifest(notebook()))
        self.assertEqual(report["cells"][0]["status"], "missing_output")

    def test_manifest_is_deterministic(self):
        self.assertEqual(nbfresh.make_manifest(notebook()), nbfresh.make_manifest(notebook()))

    def test_cli_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nb = root / "demo.ipynb"
            mf = root / "demo.nbfresh.json"
            nb.write_text(json.dumps(notebook()), encoding="utf-8")
            self.assertEqual(nbfresh.command_record(type("Args", (), {"notebook": str(nb), "manifest": str(mf)})()), 0)
            self.assertEqual(nbfresh.command_check(type("Args", (), {"notebook": str(nb), "manifest": str(mf)})()), 0)


if __name__ == "__main__":
    unittest.main()
