const waitingRoom = document.getElementById("waiting-room");
const roomEls = Array.from(document.querySelectorAll(".room"));
const historyForm = document.getElementById("history-search-form");
const historySearchInput = document.getElementById("history-search-input");
const historyFeedback = document.getElementById("history-search-feedback");
const historyResults = document.getElementById("history-search-results");

function currentQueueOrder() {
  return Array.from(waitingRoom.querySelectorAll(".patient-card")).map((card) => card.dataset.queueId);
}

async function persistQueueOrder() {
  try {
    await fetch("/api/queue/reorder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ordered_ids: currentQueueOrder() }),
    });
  } catch (error) {
    console.error("Could not persist queue order", error);
  }
}

if (waitingRoom && window.Sortable) {
  new Sortable(waitingRoom, {
    animation: 150,
    ghostClass: "drag-ghost",
    onEnd: () => {
      persistQueueOrder();
    },
  });
}

let draggingCard = null;

waitingRoom?.addEventListener("dragstart", (event) => {
  const card = event.target.closest(".patient-card");
  if (!card) {
    return;
  }

  draggingCard = card;
  card.classList.add("dragging");
});

waitingRoom?.addEventListener("dragend", (event) => {
  const card = event.target.closest(".patient-card");
  if (card) {
    card.classList.remove("dragging");
  }
  draggingCard = null;
});

roomEls.forEach((room) => {
  room.addEventListener("dragover", (event) => {
    const empty = room.querySelector(".room-empty");
    if (!empty) {
      return;
    }

    event.preventDefault();
    room.classList.add("drop-target");
  });

  room.addEventListener("dragleave", () => {
    room.classList.remove("drop-target");
  });

  room.addEventListener("drop", async (event) => {
    room.classList.remove("drop-target");
    if (!draggingCard) {
      return;
    }

    const empty = room.querySelector(".room-empty");
    if (!empty) {
      return;
    }

    event.preventDefault();

    const roomId = room.dataset.roomId;
    const queueId = draggingCard.dataset.queueId;

    try {
      const response = await fetch("/api/rooms/assign", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ queue_id: queueId, room_id: roomId }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Could not assign room");
      }
      window.location.reload();
    } catch (error) {
      alert(error.message);
    }
  });
});

Array.from(document.querySelectorAll(".discharge-button")).forEach((button) => {
  button.addEventListener("click", async () => {
    const roomId = button.dataset.roomId;
    try {
      const response = await fetch("/api/rooms/discharge", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ room_id: roomId }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Could not discharge");
      }
      window.location.reload();
    } catch (error) {
      alert(error.message);
    }
  });
});

function renderHistorySearchResults(patients) {
  historyResults.innerHTML = "";

  if (!patients.length) {
    historyFeedback.textContent = "No matching patients found.";
    return;
  }

  historyFeedback.textContent = `Found ${patients.length} patient(s). Select one to view history.`;

  patients.forEach((patient) => {
    const li = document.createElement("li");
    li.className = "result-item";
    li.innerHTML = `
      <div>
        <h3>${patient.name}</h3>
        <p>ID: ${patient.id}</p>
        <p>${patient.gender} | DOB ${patient.birth_date}</p>
      </div>
      <a class="link-button history-load-link" href="/patient/${encodeURIComponent(patient.id)}">View History</a>
    `;
    historyResults.appendChild(li);
  });
}

historyForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = historySearchInput.value.trim();

  if (query.length < 2) {
    historyFeedback.textContent = "Please enter at least 2 characters.";
    return;
  }

  historyFeedback.textContent = "Searching FHIR server...";
  historyResults.innerHTML = "";

  try {
    const response = await fetch(`/api/search-patients?name=${encodeURIComponent(query)}`);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Search failed");
    }

    renderHistorySearchResults(data.patients || []);
  } catch (error) {
    historyFeedback.textContent = `Error: ${error.message}`;
  }
});
