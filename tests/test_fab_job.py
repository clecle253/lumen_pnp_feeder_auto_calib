# -*- coding: utf-8 -*-
import copy
import json
import os
import re
import time

import pytest

from LumenPnP.core import fab_job
from LumenPnP.core.fab_job import JobError, JobWatcher, archive_job, list_pending_jobs, load_job, plan_import, validate_job

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PNP_R = {"placeable": "machine", "openpnp_package": "R_0603", "height_mm": 0.45, "tape_type": "white",
         "tape_width_mm": 8, "tape_pitch_mm": 4, "nozzle_tips": ["N045"], "verified": True}


def make_job():
    return {
        "format": "lumen-fab-job", "version": 1, "created": "2026-10-02T11:30:00+02:00",
        "board": {"name": "MyBoard", "thickness_mm": 1.6, "origin": "aux_origin"},
        "fiducials": [{"ref": "FID1", "x": 1, "y": 1, "side": "top"}],
        "placements": [
            {"ref": "R10", "cmp_id": "CMP_R", "value": "10k", "x": 10, "y": 10, "rotation": 90, "side": "top", "mode": "machine"},
            {"ref": "R2", "cmp_id": "CMP_R", "value": "10k", "x": 12, "y": 10, "rotation": 0, "side": "top", "mode": "machine"},
            {"ref": "J1", "cmp_id": "CMP_J", "value": "USB", "x": 1, "y": 5, "rotation": 0, "side": "top", "mode": "hand"},
            {"ref": "R3", "cmp_id": "CMP_R", "value": "10k", "x": 3, "y": 3, "rotation": 0, "side": "top", "mode": "skip"},
        ],
        "parts": {"CMP_R": {"name": "R10k", "description": "", "pnp": dict(PNP_R)},
                  "CMP_J": {"name": "USB-C", "description": "", "pnp": {"placeable": "hand"}}},
        "preflight": [],
    }


def write(tmp_path, job, name="b_20261002-113000.fabjob.json"):
    path = tmp_path / name
    path.write_text(json.dumps(job), encoding="utf-8")
    return str(path)


def test_valid_job_loads(tmp_path):
    assert load_job(write(tmp_path, make_job()))["board"]["name"] == "MyBoard"


@pytest.mark.parametrize("mutate,expected", [
    (lambda j: j.update(format="other"), "Format inconnu"),
    (lambda j: j.update(version=2), "Version 2"),
    (lambda j: j.update(version=True), "Version True"),
    (lambda j: j.pop("board"), "board"),
    (lambda j: j.pop("placements"), "placements"),
    (lambda j: j["placements"][0].update(mode="auto"), "mode 'auto'"),
    (lambda j: j["placements"][0].update(side="left"), "face 'left'"),
    (lambda j: j["placements"][0].update(x="abc"), "coordonnées"),
    (lambda j: j["placements"][0].update(x=float("nan")), "coordonnées"),
    (lambda j: j["placements"][0].update(rotation=None), "rotation"),
    (lambda j: j["placements"][0].update(ref=""), "référence manquante"),
    (lambda j: j["placements"].append(dict(j["placements"][0])), "en double"),
    (lambda j: j["placements"].append("oops"), "pas un objet"),
])
def test_invalid_jobs_are_rejected(tmp_path, mutate, expected):
    job = make_job()
    mutate(job)
    assert any(expected in e for e in validate_job(job))
    # NaN is not valid strict JSON but python writes it; the loader must still refuse it.
    with pytest.raises(JobError) as err:
        load_job(write(tmp_path, job))
    assert expected in str(err.value)


def test_unreadable_files(tmp_path):
    with pytest.raises(JobError):
        load_job(str(tmp_path / "missing.fabjob.json"))
    bad = tmp_path / "bad.fabjob.json"
    bad.write_text("{not json")
    with pytest.raises(JobError) as err:
        load_job(str(bad))
    assert "JSON invalide" in str(err.value)
    assert validate_job([]) == ["Le job n'est pas un objet JSON"]


def test_plan_import_modes_and_order():
    plan = plan_import(make_job())
    assert [r["ref"] for r in plan.rows] == ["J1", "R2", "R3", "R10"]  # natural order
    by_ref = {r["ref"]: r for r in plan.rows}
    assert (by_ref["R10"]["mode"], by_ref["R10"]["action"], by_ref["R10"]["status"]) == ("machine", "Import", "OK")
    assert (by_ref["J1"]["action"], by_ref["J1"]["status"]) == ("Ignore", "HAND")
    assert (by_ref["R3"]["action"], by_ref["R3"]["status"]) == ("Ignore", "SKIP")
    assert plan.hand == ["J1"]
    assert plan.board_name == "MyBoard" and plan.thickness_mm == 1.6
    assert plan.warnings == []
    assert sorted(plan.parts) == ["CMP_R"]
    part = plan.parts["CMP_R"]
    assert (part["name"], part["package"], part["height_mm"], part["nozzle_tips"]) == ("R10k", "R_0603", 0.45, ["N045"])
    assert [r["rot"] for r in plan.rows if r["ref"] == "R10"] == [90.0]
    assert len(plan.machine_rows()) == 2


@pytest.mark.parametrize("mutate,status", [
    (lambda j: j["parts"]["CMP_R"].update(pnp=None), "NO_PNP"),
    (lambda j: j["parts"].pop("CMP_R"), "NO_PNP"),
    (lambda j: j["parts"]["CMP_R"]["pnp"].update(verified=False), "UNVERIFIED"),
    (lambda j: j["parts"]["CMP_R"]["pnp"].update(height_mm=None), "NO_HEIGHT"),
    (lambda j: j["parts"]["CMP_R"]["pnp"].update(height_mm=0), "NO_HEIGHT"),
    (lambda j: [p.update(side="bottom") for p in j["placements"]], "BOTTOM_SIDE"),
    (lambda j: [p.update(cmp_id="") for p in j["placements"]], "MISSING_ID"),
])
def test_machine_parts_are_downgraded_to_hand_when_data_is_not_trustworthy(mutate, status):
    job = make_job()
    mutate(job)
    plan = plan_import(job)
    r10 = [r for r in plan.rows if r["ref"] == "R10"][0]
    assert (r10["mode"], r10["status"], r10["action"]) == ("hand", status, "Ignore")
    assert "R10" in plan.hand
    assert plan.machine_rows() == []
    assert plan.parts == {}


@pytest.mark.parametrize("value", [None, "true", "false", 0, 1, "yes"])
def test_only_an_explicit_true_counts_as_verified(value):
    job = make_job()
    job["parts"]["CMP_R"]["pnp"]["verified"] = value
    assert [r["status"] for r in plan_import(job).rows if r["ref"] == "R10"] == ["UNVERIFIED"]
    del job["parts"]["CMP_R"]["pnp"]["verified"]
    assert [r["status"] for r in plan_import(job).rows if r["ref"] == "R10"] == ["UNVERIFIED"]


def test_dnp_is_skipped_even_when_marked_machine():
    job = make_job()
    job["placements"][0]["dnp"] = True
    row = [r for r in plan_import(job).rows if r["ref"] == "R10"][0]
    assert (row["mode"], row["status"], row["action"]) == ("skip", "DNP", "Ignore")
    assert "R10" not in plan_import(job).hand


@pytest.mark.parametrize("field,value,status", [
    ("placeable", "hand", "NOT_PLACEABLE"),
    ("placeable", "skip", "NOT_PLACEABLE"),
    ("tape_type", "", "NO_TAPE"),
    ("tape_width_mm", None, "NO_TAPE"),
    ("tape_pitch_mm", 0, "NO_TAPE"),
    ("nozzle_tips", [], "NO_TAPE"),
])
def test_machine_requirements_from_the_format_doc_are_rechecked(field, value, status):
    job = make_job()
    job["parts"]["CMP_R"]["pnp"][field] = value
    row = [r for r in plan_import(job).rows if r["ref"] == "R10"][0]
    assert (row["mode"], row["status"], row["action"]) == ("hand", status, "Ignore")


def test_created_and_accented_text():
    job = make_job()
    job["board"]["name"] = "Carte été"
    job["placements"][0]["value"] = "10kΩ"
    plan = plan_import(job)
    assert plan.created == "2026-10-02T11:30:00+02:00"
    assert plan.board_name == "Carte été"
    job["placements"].append(dict(job["placements"][0]))
    with pytest.raises(JobError) as err:
        validate = fab_job.validate_job(job)
        assert any("double" in e for e in validate)
        raise JobError("\n".join(validate))
    assert "double" in err.value.text


def test_plan_warnings():
    job = make_job()
    job["fiducials"] = []
    job["board"]["origin"] = "page_origin"
    warnings = plan_import(job).warnings
    assert any("fiducial" in w for w in warnings)
    assert any("contour" in w for w in warnings)
    job2 = make_job()
    job2["fiducials"] = [{"ref": "F", "x": "bad", "y": 1}]
    assert plan_import(job2).fiducials == []


def test_plan_does_not_mutate_job():
    job = make_job()
    before = copy.deepcopy(job)
    plan_import(job)
    assert job == before


def test_list_and_archive(tmp_path):
    a = write(tmp_path, make_job(), "a.fabjob.json")
    b = write(tmp_path, make_job(), "b.fabjob.json")
    (tmp_path / "notes.txt").write_text("x")
    (tmp_path / "b.fabjob.json.part").write_text("partial")
    os.utime(a, (1000, 1000))
    os.utime(b, (2000, 2000))
    assert list_pending_jobs(str(tmp_path)) == [a, b]
    moved = archive_job(a)
    assert moved == os.path.join(str(tmp_path), "processed", "a.fabjob.json")
    assert list_pending_jobs(str(tmp_path)) == [b]
    again = write(tmp_path, make_job(), "a.fabjob.json")
    assert archive_job(again).endswith("a_1.fabjob.json")
    assert archive_job(b, ok=False) == os.path.join(str(tmp_path), "failed", "b.fabjob.json")
    assert list_pending_jobs(str(tmp_path / "missing")) == []
    assert list_pending_jobs("") == []


def test_watcher_waits_for_a_stable_file(tmp_path):
    watcher = JobWatcher(str(tmp_path))
    assert watcher.poll() == []
    path = write(tmp_path, make_job(), "a.fabjob.json")
    assert watcher.poll() == []              # first sighting: could still be copying
    with open(path, "a") as f:
        f.write(" ")                         # size changed -> still not stable
    assert watcher.poll() == []
    assert watcher.poll() == [path]          # unchanged between two polls
    assert watcher.poll() == []              # announced once only
    archive_job(path)
    assert watcher.poll() == []
    again = write(tmp_path, make_job(), "a.fabjob.json")  # same name comes back -> announced again
    watcher.poll()
    assert watcher.poll() == [again]


def test_watcher_ignores_empty_files_and_missing_folder(tmp_path):
    watcher = JobWatcher(str(tmp_path))
    (tmp_path / "e.fabjob.json").write_text("")
    watcher.poll()
    assert watcher.poll() == []
    assert JobWatcher(str(tmp_path / "nope")).poll() == []
    watcher.set_dir(str(tmp_path / "nope"))
    assert watcher.poll() == []


def test_module_is_jython_27_compatible_and_has_no_openpnp_import():
    import ast
    tree = ast.parse(open(os.path.join(REPO, "LumenPnP", "core", "fab_job.py"), encoding="utf-8").read())
    for node in ast.walk(tree):
        assert not isinstance(node, (ast.JoinedStr, ast.Nonlocal, ast.AnnAssign, ast.AsyncFunctionDef, ast.Await,
                                     ast.NamedExpr, ast.Starred)), "not valid in Jython 2.7: %s" % type(node).__name__
        if isinstance(node, ast.FunctionDef):
            args = node.args
            assert node.returns is None and not args.kwonlyargs and not args.posonlyargs
            assert all(a.annotation is None for a in args.args)
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names] + [getattr(node, "module", None) or ""]
            assert not any(n.split(".")[0] in ("org", "java", "javax") for n in names)
