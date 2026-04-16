const form = document.getElementById("patient-search-form");
const input = document.getElementById("patient-name");
const feedback = document.getElementById("search-feedback");
const results = document.getElementById("patient-results");

function renderPatients(patients) {
  results.innerHTML = "";

  if (!patients.length) {
    feedback.textContent = "No matching patients found.";
    return;
  }

  feedback.textContent = `Found ${patients.length} patient(s). Select one to continue triage.`;

  patients.forEach((patient) => {
    const li = document.createElement("li");
    li.className = "result-item";
    li.innerHTML = `
      <div>
        <h3>${patient.name}</h3>
        <p>ID: ${patient.id}</p>
        <p>${patient.gender} | DOB ${patient.birth_date}</p>
      </div>
      <a class="link-button" href="/triage/${patient.id}">Select</a>
    `;
    results.appendChild(li);
  });
}

form?.addEventListener("submit", async (event) => {
  event.preventDefault();

  const name = input.value.trim();
  if (name.length < 2) {
    feedback.textContent = "Please enter at least 2 characters.";
    return;
  }

  feedback.textContent = "Searching FHIR server...";
  results.innerHTML = "";

  try {
    const response = await fetch(`/api/search-patients?name=${encodeURIComponent(name)}`);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Search failed");
    }

    renderPatients(data.patients || []);
  } catch (error) {
    feedback.textContent = `Error: ${error.message}`;
  }
});
