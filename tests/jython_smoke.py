# -*- coding: utf-8 -*-
"""Smoke test run under Jython 2.7 (the interpreter OpenPnP really uses):

    java -jar jython-standalone-2.7.3.jar tests/jython_smoke.py

pytest cannot run on Jython, and str/unicode mixing only fails there, so this
plain-assert script covers the paths that handle accented text.
"""
from __future__ import print_function
from __future__ import unicode_literals

import io
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from LumenPnP.core import fab_job

PNP = {"placeable": "machine", "openpnp_package": "R_0603", "height_mm": 0.45, "tape_type": "white",
       "tape_width_mm": 8, "tape_pitch_mm": 4, "nozzle_tips": ["N045"], "verified": True}


def job():
    return {
        "format": "lumen-fab-job", "version": 1, "created": "2026-10-02T11:30:00+02:00",
        "board": {"name": "Carte été", "thickness_mm": 1.6, "origin": "aux_origin"},
        "fiducials": [],
        "placements": [
            {"ref": "R1", "cmp_id": "CMP_R", "value": "10kΩ", "x": 1, "y": 2, "rotation": 90, "side": "top", "mode": "machine"},
            {"ref": "J1", "cmp_id": "CMP_J", "value": "USB", "x": 5, "y": 2, "rotation": 0, "side": "top", "mode": "hand"},
        ],
        "parts": {"CMP_R": {"name": "R10kΩ", "pnp": PNP}},
    }


def write(folder, data, name):
    path = os.path.join(folder, name)
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False))
    return path


def check_gui_compiles():
    """The Swing GUI cannot run outside OpenPnP, but a syntax error must be caught here."""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "LumenPnP", "gui", "lumen_gui.py")
    with io.open(path, "r", encoding="utf-8") as f:
        compile(f.read().encode("utf-8"), path, "exec")


def main():
    check_gui_compiles()
    folder = tempfile.mkdtemp(prefix="fabjobs_")
    try:
        # A good job with accented text loads, plans and archives.
        good = write(folder, job(), "a.fabjob.json")
        plan = fab_job.plan_import(fab_job.load_job(good))
        assert plan.board_name == "Carte été", repr(plan.board_name)
        assert [r["action"] for r in plan.rows] == ["Ignore", "Import"], plan.rows
        assert plan.parts["CMP_R"]["name"] == "R10kΩ"
        assert any("fiducial" in w for w in plan.warnings)
        assert (", ".join(plan.hand) + " à la main") == "J1 à la main"

        # Every invalid case raises JobError (never UnicodeDecodeError) with readable text.
        for mutate in (lambda j: j["placements"].append(dict(j["placements"][0])),
                       lambda j: j["placements"][0].update(x="abc"),
                       lambda j: j["placements"][0].update(mode="auto", ref=""),
                       lambda j: j.update(version=9)):
            bad = job()
            mutate(bad)
            path = write(folder, bad, "bad.fabjob.json")
            try:
                fab_job.load_job(path)
            except fab_job.JobError as e:
                assert isinstance(e.text, type("")) and e.text, repr(e.text)
                ("Job refusé (" + path + ") : " + e.text)  # what the GUI logs
            else:
                raise AssertionError("invalid job accepted")
            fab_job.archive_job(path, ok=False)

        broken = os.path.join(folder, "broken.fabjob.json")
        with io.open(broken, "w", encoding="utf-8") as f:
            f.write("{pas du json é")
        try:
            fab_job.load_job(broken)
        except fab_job.JobError as e:
            assert "JSON invalide" in e.text
        fab_job.archive_job(broken, ok=False)

        # Watcher + archive.
        watcher = fab_job.JobWatcher(folder)
        assert fab_job.list_pending_jobs(folder) == [good]
        watcher.poll()
        assert watcher.poll() == [good]
        moved = fab_job.archive_job(good)
        assert os.path.exists(moved) and not os.path.exists(good)
        assert ("Job archivé : " + moved).startswith("Job archivé")
        assert fab_job.list_pending_jobs(folder) == []
        print("jython smoke OK on", sys.version.split()[0] if sys.version else "?")
    finally:
        shutil.rmtree(folder, ignore_errors=True)


main()
