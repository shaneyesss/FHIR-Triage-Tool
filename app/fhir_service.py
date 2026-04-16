from __future__ import annotations

from typing import Any

import requests

FHIR_BASE_URL = "https://r4.smarthealthit.org"
FHIR_TIMEOUT_SECONDS = 15


def _extract_patient_name(patient: dict[str, Any]) -> str:
    names = patient.get("name", [])
    if not names:
        return "Unknown"

    best = names[0]
    given = " ".join(best.get("given", []))
    family = best.get("family", "")
    full = " ".join(part for part in [given, family] if part).strip()
    return full or "Unknown"


def _extract_condition_text(entry: dict[str, Any]) -> str:
    resource = entry.get("resource", {})
    code = resource.get("code", {})
    if code.get("text"):
        return code["text"]

    coding = code.get("coding", [])
    if coding and coding[0].get("display"):
        return coding[0]["display"]

    return "Unspecified condition"


def search_patients(name: str) -> list[dict[str, str]]:
    response = requests.get(
        f"{FHIR_BASE_URL}/Patient",
        params={"name": name, "_count": 10},
        timeout=FHIR_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    bundle = response.json()

    results: list[dict[str, str]] = []
    for entry in bundle.get("entry", []):
        patient = entry.get("resource", {})
        patient_id = patient.get("id")
        if not patient_id:
            continue

        results.append(
            {
                "id": patient_id,
                "name": _extract_patient_name(patient),
                "gender": patient.get("gender", "unknown"),
                "birth_date": patient.get("birthDate", "unknown"),
            }
        )

    return results


def get_patient(patient_id: str) -> dict[str, Any]:
    response = requests.get(
        f"{FHIR_BASE_URL}/Patient/{patient_id}",
        timeout=FHIR_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    resource = response.json()
    return {
        "id": resource.get("id", patient_id),
        "name": _extract_patient_name(resource),
        "gender": resource.get("gender", "unknown"),
        "birth_date": resource.get("birthDate", "unknown"),
    }


def get_recent_visits(patient_id: str, count: int = 3) -> list[dict[str, str]]:
    response = requests.get(
        f"{FHIR_BASE_URL}/Encounter",
        params={"patient": patient_id, "_sort": "-date", "_count": count},
        timeout=FHIR_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    bundle = response.json()

    visits: list[dict[str, str]] = []
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        encounter_type = "Unknown"
        if resource.get("type"):
            text = resource["type"][0].get("text")
            coding = resource["type"][0].get("coding", [])
            encounter_type = text or (coding[0].get("display") if coding else "Unknown")

        period = resource.get("period", {})
        date_text = period.get("start") or resource.get("date") or "Unknown"

        visits.append(
            {
                "id": resource.get("id", "unknown"),
                "type": encounter_type,
                "date": date_text,
                "status": resource.get("status", "unknown"),
            }
        )

    return visits


def get_medical_history(patient_id: str) -> list[str]:
    params = {"patient": patient_id, "_count": 50, "_sort": "-recorded-date"}
    response = requests.get(
        f"{FHIR_BASE_URL}/Condition",
        params=params,
        timeout=FHIR_TIMEOUT_SECONDS,
    )

    # Some FHIR servers reject sort parameters; retry unsorted for compatibility.
    if response.status_code == 400:
        response = requests.get(
            f"{FHIR_BASE_URL}/Condition",
            params={"patient": patient_id, "_count": 50},
            timeout=FHIR_TIMEOUT_SECONDS,
        )

    response.raise_for_status()
    bundle = response.json()

    conditions = [_extract_condition_text(entry) for entry in bundle.get("entry", [])]
    unique: list[str] = []
    seen = set()
    for condition in conditions:
        key = condition.strip().lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(condition)

    return unique
