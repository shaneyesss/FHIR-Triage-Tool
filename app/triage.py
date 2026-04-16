from __future__ import annotations

from typing import Any

HIGH_RISK_CONDITIONS = {
    "stroke": 20,
    "cerebrovascular": 20,
    "myocardial infarction": 20,
    "coronary artery disease": 18,
    "heart failure": 18,
    "arrhythmia": 15,
    "atrial fibrillation": 12,
    "pulmonary embolism": 20,
    "copd": 10,
    "diabetes": 8,
    "sepsis": 20,
    "chronic kidney disease": 10,
}

HIGH_RISK_COMPLAINTS = {
    "chest pain": 25,
    "shortness of breath": 20,
    "difficulty breathing": 20,
    "weakness": 10,
    "slurred speech": 25,
    "facial droop": 25,
    "confusion": 12,
    "severe headache": 12,
    "syncope": 18,
    "abdominal pain": 10,
    "fever": 8,
    "trauma": 15,
}

CHIEF_COMPLAINT_PROFILES = {
    "chest_pain": {"label": "Chest Pain", "base_points": 28},
    "stroke_symptoms": {"label": "Stroke Symptoms", "base_points": 30},
    "shortness_breath": {"label": "Shortness of Breath", "base_points": 24},
    "abdominal_pain": {"label": "Abdominal Pain", "base_points": 14},
    "fever_infection": {"label": "Fever / Infection", "base_points": 12},
    "trauma": {"label": "Trauma / Injury", "base_points": 18},
    "allergic_reaction": {"label": "Allergic Reaction", "base_points": 20},
    "mental_health": {"label": "Mental Health Crisis", "base_points": 16},
    "pregnancy_complication": {"label": "Pregnancy Complication", "base_points": 20},
    "other": {"label": "Other", "base_points": 8},
}


def _normalize(text: str) -> str:
    return text.strip().lower()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _extract_temperature_f(vitals: dict[str, Any]) -> float:
    temp_f = _safe_float(vitals.get("temperature_f"), default=0.0)
    if temp_f:
        return temp_f

    # Backward compatibility if older records still carry Celsius.
    temp_c = _safe_float(vitals.get("temperature_c"), default=0.0)
    if temp_c:
        return (temp_c * 9.0 / 5.0) + 32.0

    return 0.0


def get_chief_complaint_options() -> list[dict[str, str]]:
    return [
        {"code": code, "label": profile["label"]}
        for code, profile in CHIEF_COMPLAINT_PROFILES.items()
    ]


def calculate_triage_score(
    chief_complaint: str,
    medical_history: list[str],
    vitals: dict[str, Any],
    complaint_code: str | None = None,
) -> dict[str, Any]:
    score = 0
    reasons: list[str] = []

    complaint = _normalize(chief_complaint)
    selected_profile = CHIEF_COMPLAINT_PROFILES.get(complaint_code or "")

    if selected_profile:
        base_points = int(selected_profile["base_points"])
        score += base_points
        reasons.append(
            f"Chief complaint selected: {selected_profile['label']} (+{base_points})"
        )
    else:
        for keyword, points in HIGH_RISK_COMPLAINTS.items():
            if keyword in complaint:
                score += points
                reasons.append(f"High-risk chief complaint: {keyword} (+{points})")

    history_blob = " ".join(_normalize(item) for item in medical_history)
    for keyword, points in HIGH_RISK_CONDITIONS.items():
        if keyword in history_blob:
            score += points
            reasons.append(f"History includes {keyword} (+{points})")

    hr = _safe_float(vitals.get("heart_rate"))
    sbp = _safe_float(vitals.get("systolic_bp"))
    temp_f = _extract_temperature_f(vitals)
    rr = _safe_float(vitals.get("respiratory_rate"))
    spo2 = _safe_float(vitals.get("spo2"))
    pain = _safe_float(vitals.get("pain_score"))

    if complaint_code == "chest_pain" and hr > 110:
        score += 8
        reasons.append("Chest pain with tachycardia (+8)")
    elif complaint_code == "stroke_symptoms" and sbp >= 180:
        score += 10
        reasons.append("Stroke symptoms with severe hypertension (+10)")
    elif complaint_code == "shortness_breath" and spo2 and spo2 < 92:
        score += 15
        reasons.append("Shortness of breath with low oxygen (+15)")
    elif complaint_code == "fever_infection" and temp_f >= 101.0 and hr > 110:
        score += 10
        reasons.append("Possible sepsis pattern (+10)")
    elif complaint_code == "trauma" and sbp < 100:
        score += 15
        reasons.append("Trauma with low blood pressure (+15)")
    elif complaint_code == "allergic_reaction" and spo2 and spo2 < 94:
        score += 12
        reasons.append("Allergic reaction with respiratory compromise (+12)")

    if hr > 130 or hr < 40:
        score += 20
        reasons.append("Critical heart rate (+20)")
    elif hr > 110:
        score += 10
        reasons.append("Abnormal heart rate (+10)")

    if sbp < 90 or sbp > 200:
        score += 20
        reasons.append("Critical systolic blood pressure (+20)")
    elif sbp < 100 or sbp > 180:
        score += 10
        reasons.append("Abnormal systolic blood pressure (+10)")

    if temp_f >= 103.1 or (temp_f and temp_f <= 95.0):
        score += 12
        reasons.append("Dangerous temperature (+12)")
    elif temp_f >= 101.0:
        score += 6
        reasons.append("Fever (+6)")

    if rr >= 30 or rr <= 8:
        score += 15
        reasons.append("Critical respiratory rate (+15)")
    elif rr >= 24:
        score += 8
        reasons.append("Elevated respiratory rate (+8)")

    if spo2 and spo2 < 90:
        score += 20
        reasons.append("Hypoxemia (+20)")
    elif spo2 and spo2 < 94:
        score += 10
        reasons.append("Low oxygen saturation (+10)")

    if pain >= 8:
        score += 10
        reasons.append("Severe pain (+10)")
    elif pain >= 5:
        score += 5
        reasons.append("Moderate pain (+5)")

    final_score = min(int(score), 100)

    if final_score >= 70:
        level = "ESI-1 (Immediate)"
    elif final_score >= 50:
        level = "ESI-2 (Emergent)"
    elif final_score >= 30:
        level = "ESI-3 (Urgent)"
    elif final_score >= 15:
        level = "ESI-4 (Less Urgent)"
    else:
        level = "ESI-5 (Non-Urgent)"

    return {
        "score": final_score,
        "level": level,
        "reasons": reasons,
    }
