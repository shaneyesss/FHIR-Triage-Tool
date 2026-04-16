# FHIR-Triage-Tool

Flask application for emergency department triage, backed by SMART on FHIR R4.

## What This App Does

1. Search patient by name (live query to `https://r4.smarthealthit.org`).
2. Select patient and open triage intake page.
3. Auto-load:
	 - Most recent 3 visits/admissions (`Encounter` resources)
	 - Medical history (`Condition` resources)
4. Nurse enters chief complaint + vital signs (temperature in Fahrenheit).
5. App calculates triage score based on:
	 - High-risk history (e.g., stroke, heart disease)
	 - Vital sign abnormalities
	 - High-risk chief complaint terms
6. Patient is added to waiting room queue.
7. Dashboard supports:
	 - Drag-and-drop queue ordering
	 - Drag patient card from waiting room into empty ED room
	 - Room view with patient details + discharge button

## Stack

- Python 3
- Flask
- Requests
- Vanilla JS + SortableJS (for drag-and-drop queue)

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open in browser:

```text
http://127.0.0.1:5000
```

## Project Structure

```text
app.py
app/
	__init__.py
	routes.py
	fhir_service.py
	triage.py
	state.py
templates/
	base.html
	dashboard.html
	search.html
	triage.html
	error.html
static/
	css/styles.css
	js/search.js
	js/dashboard.js
requirements.txt
```

## Notes

- State is in-memory (waiting room + ED rooms reset on restart).
- This is a teaching/demo app and not production hardened.
