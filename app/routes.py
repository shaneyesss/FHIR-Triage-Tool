from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
import requests

from .fhir_service import get_medical_history, get_patient, get_recent_visits, search_patients
from .state import state
from .triage import CHIEF_COMPLAINT_PROFILES, calculate_triage_score, get_chief_complaint_options

bp = Blueprint("main", __name__)


def _sort_waiting_room() -> None:
    state.waiting_room.sort(key=lambda item: item["triage"]["score"], reverse=True)


@bp.route("/")
def dashboard():
    _sort_waiting_room()
    return render_template(
        "dashboard.html",
        waiting_room=state.waiting_room,
        rooms=state.rooms,
    )


@bp.route("/patient-search")
def patient_search_page():
    return render_template("search.html")


@bp.route("/api/search-patients")
def search_patients_endpoint():
    name = request.args.get("name", "").strip()
    if len(name) < 2:
        return jsonify({"error": "Please enter at least 2 characters."}), 400

    try:
        patients = search_patients(name)
    except requests.RequestException as exc:
        return jsonify({"error": f"FHIR query failed: {exc}"}), 502

    return jsonify({"patients": patients})


@bp.route("/api/patient-history/<patient_id>")
def patient_history_endpoint(patient_id: str):
    try:
        patient = get_patient(patient_id)
        visits = get_recent_visits(patient_id, count=3)
        history = get_medical_history(patient_id)
    except requests.RequestException as exc:
        return jsonify({"error": f"FHIR query failed: {exc}"}), 502

    return jsonify(
        {
            "patient": patient,
            "recent_visits": visits,
            "medical_history": history,
        }
    )


@bp.route("/patient/<patient_id>")
def patient_info_page(patient_id: str):
    try:
        patient = get_patient(patient_id)
        visits = get_recent_visits(patient_id, count=3)
        history = get_medical_history(patient_id)
    except requests.RequestException as exc:
        return render_template("error.html", message=f"FHIR query failed: {exc}"), 502

    return render_template(
        "patient_info.html",
        patient=patient,
        visits=visits,
        history=history,
    )


@bp.route("/triage/<patient_id>", methods=["GET", "POST"])
def triage_page(patient_id: str):
    try:
        patient = get_patient(patient_id)
        visits = get_recent_visits(patient_id, count=3)
        history = get_medical_history(patient_id)
    except requests.RequestException as exc:
        return render_template("error.html", message=f"FHIR query failed: {exc}"), 502

    if request.method == "POST":
        chief_complaint_code = request.form.get("chief_complaint_code", "").strip()
        chief_complaint_details = request.form.get("chief_complaint_details", "").strip()

        selected_profile = CHIEF_COMPLAINT_PROFILES.get(chief_complaint_code)
        if selected_profile:
            if chief_complaint_code == "other" and not chief_complaint_details:
                return render_template(
                    "triage.html",
                    patient=patient,
                    visits=visits,
                    history=history,
                    complaint_options=get_chief_complaint_options(),
                    selected_complaint_code=chief_complaint_code,
                    chief_complaint_details=chief_complaint_details,
                    form_error="Please add details when selecting Other.",
                )

            chief_complaint = selected_profile["label"]
            if chief_complaint_details:
                chief_complaint = f"{chief_complaint}: {chief_complaint_details}"
        else:
            if not chief_complaint_details:
                return render_template(
                    "triage.html",
                    patient=patient,
                    visits=visits,
                    history=history,
                    complaint_options=get_chief_complaint_options(),
                    selected_complaint_code="other",
                    chief_complaint_details=chief_complaint_details,
                    form_error="Please add details when selecting Other.",
                )

            chief_complaint = chief_complaint_details
            chief_complaint_code = "other"

        vitals = {
            "heart_rate": request.form.get("heart_rate"),
            "systolic_bp": request.form.get("systolic_bp"),
            "diastolic_bp": request.form.get("diastolic_bp"),
            "temperature_f": request.form.get("temperature_f"),
            "respiratory_rate": request.form.get("respiratory_rate"),
            "spo2": request.form.get("spo2"),
            "pain_score": request.form.get("pain_score"),
        }

        triage = calculate_triage_score(
            chief_complaint,
            history,
            vitals,
            complaint_code=chief_complaint_code,
        )
        queue_item = {
            "queue_id": str(uuid4()),
            "patient": patient,
            "chief_complaint": chief_complaint,
            "chief_complaint_code": chief_complaint_code,
            "vitals": vitals,
            "triage": triage,
            "added_at": datetime.now(timezone.utc).isoformat(),
        }

        state.waiting_room.append(queue_item)
        _sort_waiting_room()

        return redirect(url_for("main.dashboard"))

    return render_template(
        "triage.html",
        patient=patient,
        visits=visits,
        history=history,
        complaint_options=get_chief_complaint_options(),
        selected_complaint_code="",
        chief_complaint_details="",
        form_error="",
    )


@bp.route("/api/queue/reorder", methods=["POST"])
def reorder_queue():
    payload = request.get_json(silent=True) or {}
    ordered_ids = payload.get("ordered_ids", [])

    if not isinstance(ordered_ids, list):
        return jsonify({"error": "ordered_ids must be a list"}), 400

    by_id = {item["queue_id"]: item for item in state.waiting_room}
    reordered = [by_id[item_id] for item_id in ordered_ids if item_id in by_id]

    # Keep any unlisted records at the end to avoid accidental drops.
    leftovers = [item for item in state.waiting_room if item["queue_id"] not in ordered_ids]
    state.waiting_room = reordered + leftovers

    return jsonify({"ok": True})


@bp.route("/api/rooms/assign", methods=["POST"])
def assign_to_room():
    payload = request.get_json(silent=True) or {}
    queue_id = payload.get("queue_id")
    room_id = payload.get("room_id")

    if not queue_id or not room_id:
        return jsonify({"error": "queue_id and room_id are required"}), 400

    if room_id not in state.rooms:
        return jsonify({"error": "Unknown room"}), 404

    if state.rooms[room_id] is not None:
        return jsonify({"error": "Room is occupied"}), 409

    for idx, item in enumerate(state.waiting_room):
        if item["queue_id"] == queue_id:
            state.rooms[room_id] = item
            state.waiting_room.pop(idx)
            return jsonify({"ok": True, "room": room_id})

    return jsonify({"error": "Patient not found in waiting room"}), 404


@bp.route("/api/rooms/discharge", methods=["POST"])
def discharge_room():
    payload = request.get_json(silent=True) or {}
    room_id = payload.get("room_id")

    if room_id not in state.rooms:
        return jsonify({"error": "Unknown room"}), 404

    state.rooms[room_id] = None
    return jsonify({"ok": True})
