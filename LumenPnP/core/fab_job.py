# -*- coding: utf-8 -*-
"""Reads Fab jobs written by the KiCad "Fab" button (kicad_library_manager).

Pure Python, no OpenPnP import, written to run on both Jython 2.7 (inside
OpenPnP) and Python 3 (pytest): no f-strings, no type hints, no nonlocal.
The job format is described in kicad_library_manager/docs/fab_job_format.md.

Nothing here moves the machine or touches the OpenPnP configuration: it turns a
job file into plain data (rows for the import table, parts to create, a list of
parts to place by hand) that the GUI then applies.
"""
import io
import json
import os
import re
import shutil

JOB_FORMAT = "lumen-fab-job"
SUPPORTED_VERSION = 1
JOB_SUFFIX = ".fabjob.json"
PROCESSED_DIR = "processed"
FAILED_DIR = "failed"

MODES = ("machine", "hand", "skip")
SIDES = ("top", "bottom")


class JobError(Exception):
    """The job file cannot be used; the message says why (shown to the user)."""


def _is_text(value):
    try:
        return isinstance(value, basestring)  # noqa: F821  (Jython 2.7)
    except NameError:
        return isinstance(value, str)


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def read_json(path):
    try:
        with io.open(path, "r", encoding="utf-8") as f:
            return json.loads(f.read())
    except IOError as e:
        raise JobError("Lecture impossible : %s" % e)
    except ValueError as e:
        raise JobError("Fichier JSON invalide : %s" % e)


def validate_job(job):
    """Returns a list of problems that make the job unusable (empty = usable)."""
    if not isinstance(job, dict):
        return ["Le job n'est pas un objet JSON"]
    errors = []
    if job.get("format") != JOB_FORMAT:
        errors.append("Format inconnu : %r (attendu %s)" % (job.get("format"), JOB_FORMAT))
    version = job.get("version")
    if version != SUPPORTED_VERSION or isinstance(version, bool):
        errors.append("Version %r non gérée (ce plugin lit la version %d)" % (version, SUPPORTED_VERSION))
    if not isinstance(job.get("board"), dict):
        errors.append("Bloc 'board' manquant")
    placements = job.get("placements")
    if not isinstance(placements, list):
        errors.append("Liste 'placements' manquante")
        return errors
    seen = set()
    for index, p in enumerate(placements):
        label = "placements[%d]" % index
        if not isinstance(p, dict):
            errors.append(label + " : pas un objet")
            continue
        ref = p.get("ref")
        if not _is_text(ref) or not ref.strip():
            errors.append(label + " : référence manquante")
        else:
            label = "%s (%s)" % (label, ref)
            if ref in seen:
                errors.append(label + " : référence en double")
            seen.add(ref)
        if _number(p.get("x")) is None or _number(p.get("y")) is None:
            errors.append(label + " : coordonnées x/y invalides")
        if p.get("mode") not in MODES:
            errors.append(label + " : mode %r inconnu" % (p.get("mode"),))
        if p.get("side") not in SIDES:
            errors.append(label + " : face %r inconnue" % (p.get("side"),))
        if _number(p.get("rotation", 0)) is None:
            errors.append(label + " : rotation invalide")
    return errors


def load_job(path):
    """Reads and validates a job file; raises JobError with every problem found."""
    job = read_json(path)
    errors = validate_job(job)
    if errors:
        raise JobError("Job inutilisable :\n- " + "\n- ".join(errors))
    return job


def _clean(value):
    return value.strip() if _is_text(value) else ""


def _natural_key(ref):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", ref)]


class ImportPlan(object):
    """Everything the GUI needs to show and apply a job."""

    def __init__(self):
        self.board_name = ""
        self.thickness_mm = None
        self.origin = ""
        self.rows = []        # one dict per placement, shaped like the BOM/.pos importer's rows
        self.parts = {}       # cmp_id -> {name, package, height_mm, nozzle_tips, tape_type, ...}
        self.fiducials = []   # [{ref, x, y, side}] (informational, not created automatically)
        self.hand = []        # refs to place by hand
        self.warnings = []

    def machine_rows(self):
        return [r for r in self.rows if r["mode"] == "machine"]


def _part_info(cmp_id, entry, fallback_value):
    entry = entry if isinstance(entry, dict) else {}
    pnp = entry.get("pnp") if isinstance(entry.get("pnp"), dict) else {}
    height = _number(pnp.get("height_mm"))
    return {
        "cmp_id": cmp_id,
        "name": _clean(entry.get("name")) or fallback_value or cmp_id,
        "package": _clean(pnp.get("openpnp_package")) or cmp_id,
        "height_mm": height if height is not None and height > 0 else None,
        "nozzle_tips": [t for t in (pnp.get("nozzle_tips") or []) if _is_text(t)],
        "tape_type": _clean(pnp.get("tape_type")),
        "tape_width_mm": _number(pnp.get("tape_width_mm")),
        "tape_pitch_mm": _number(pnp.get("tape_pitch_mm")),
        "rotation_in_tape_deg": _number(pnp.get("rotation_in_tape_deg")) or 0.0,
        "verified": pnp.get("verified") is not False,
    }


def plan_import(job):
    """Turns a validated job into an ImportPlan.

    Only parts the Fab button marked ``machine`` get the action "Import". Parts to
    place by hand or skipped are listed but not imported, so the machine never
    picks something nobody confirmed. A part marked ``machine`` whose pnp block is
    missing or unverified (a hand-edited job) is downgraded to hand here as well.
    """
    plan = ImportPlan()
    board = job.get("board") or {}
    plan.board_name = _clean(board.get("name")) or "Imported Board"
    plan.thickness_mm = _number(board.get("thickness_mm"))
    plan.origin = _clean(board.get("origin"))
    if plan.origin == "page_origin":
        plan.warnings.append("Le job n'a pas de contour de carte : coordonnées relatives à la page KiCad.")

    parts = job.get("parts") if isinstance(job.get("parts"), dict) else {}
    for f in job.get("fiducials") or []:
        if isinstance(f, dict) and _number(f.get("x")) is not None and _number(f.get("y")) is not None:
            plan.fiducials.append({"ref": _clean(f.get("ref")), "x": _number(f.get("x")),
                                   "y": _number(f.get("y")), "side": _clean(f.get("side")) or "top"})
    if not plan.fiducials:
        plan.warnings.append("Le job ne contient aucun fiducial.")

    for p in sorted(job["placements"], key=lambda item: _natural_key(item["ref"])):
        cmp_id = _clean(p.get("cmp_id"))
        mode = p["mode"]
        status = "OK"
        if mode == "machine":
            info = plan.parts.get(cmp_id)
            if not cmp_id:
                mode, status = "hand", "MISSING_ID"
            else:
                if info is None:
                    info = _part_info(cmp_id, parts.get(cmp_id), _clean(p.get("value")))
                if not isinstance(parts.get(cmp_id), dict) or not isinstance(parts[cmp_id].get("pnp"), dict):
                    mode, status = "hand", "NO_PNP"
                elif not info["verified"]:
                    mode, status = "hand", "UNVERIFIED"
                elif info["height_mm"] is None:
                    mode, status = "hand", "NO_HEIGHT"
                elif p["side"] == "bottom":
                    mode, status = "hand", "BOTTOM_SIDE"
                else:
                    plan.parts[cmp_id] = info
        elif mode == "hand":
            status = "HAND"
        else:
            status = "SKIP"
        if mode == "hand":
            plan.hand.append(p["ref"])
        plan.rows.append({
            "ref": p["ref"],
            "cmp_id": cmp_id,
            "value": _clean(p.get("value")),
            "x": _number(p["x"]),
            "y": _number(p["y"]),
            "rot": _number(p.get("rotation", 0)) or 0.0,
            "side": p["side"],
            "mode": mode,
            "status": status,
            "action": "Import" if mode == "machine" else "Ignore",
        })
    return plan


def list_pending_jobs(job_dir):
    """Job files waiting in ``job_dir`` (not in processed/ or failed/), oldest first."""
    if not job_dir or not os.path.isdir(job_dir):
        return []
    found = []
    for name in os.listdir(job_dir):
        path = os.path.join(job_dir, name)
        if name.endswith(JOB_SUFFIX) and os.path.isfile(path):
            found.append((os.path.getmtime(path), name, path))
    found.sort()
    return [path for _, _, path in found]


def archive_job(path, ok=True):
    """Moves a job into processed/ (or failed/) next to it, never overwriting; returns the new path."""
    folder = os.path.join(os.path.dirname(path), PROCESSED_DIR if ok else FAILED_DIR)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    name = os.path.basename(path)
    target = os.path.join(folder, name)
    counter = 1
    while os.path.exists(target):
        target = os.path.join(folder, name[:-len(JOB_SUFFIX)] + "_%d%s" % (counter, JOB_SUFFIX))
        counter += 1
    shutil.move(path, target)
    return target


class JobWatcher(object):
    """Polls a folder and reports job files it has not announced yet.

    ``poll()`` is meant to be called from a timer thread; it never raises.
    A file is only announced once its size and modification time are the same
    for two polls in a row, so a job still being copied is not read half-written.
    """

    def __init__(self, job_dir):
        self.job_dir = job_dir
        self._seen = {}      # path -> (size, mtime) at the last poll
        self._announced = set()

    def set_dir(self, job_dir):
        self.job_dir = job_dir
        self._seen = {}
        self._announced = set()

    def poll(self):
        new = []
        try:
            current = {}
            for path in list_pending_jobs(self.job_dir):
                stat = os.stat(path)
                current[path] = (stat.st_size, stat.st_mtime)
            for path, signature in current.items():
                if path in self._announced:
                    continue
                if self._seen.get(path) == signature and signature[0] > 0:
                    self._announced.add(path)
                    new.append(path)
            self._seen = current
            self._announced &= set(current)
        except OSError:
            return []
        new.sort(key=lambda p: (os.path.getmtime(p) if os.path.exists(p) else 0, p))
        return new
