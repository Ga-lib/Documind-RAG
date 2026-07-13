const API_BASE = "";

const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const uploadBox = document.getElementById("uploadBox");
const fileInput = document.getElementById("fileInput");
const uploadStatus = document.getElementById("uploadStatus");
const docList = document.getElementById("docList");
const messages = document.getElementById("messages");
const askForm = document.getElementById("askForm");
const questionInput = document.getElementById("questionInput");
const askButton = document.getElementById("askButton");

async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error("not ok");
    statusDot.classList.add("online");
    statusDot.classList.remove("offline");
    statusText.textContent = "Online";
  } catch {
    statusDot.classList.add("offline");
    statusDot.classList.remove("online");
    statusText.textContent = "Offline";
  }
}

async function loadDocuments() {
  try {
    const res = await fetch(`${API_BASE}/documents`);
    const data = await res.json();

    docList.innerHTML = "";
    if (!data.documents || data.documents.length === 0) {
      docList.innerHTML = '<li class="doc-empty">No documents yet</li>';
      return;
    }

    data.documents.forEach((doc) => {
      const li = document.createElement("li");
      li.className = "doc-item";
      li.innerHTML = `
        <span class="doc-name" title="${doc.filename}">${doc.filename}</span>
        <button class="doc-delete" data-filename="${doc.filename}">&times;</button>
      `;
      docList.appendChild(li);
    });

    document.querySelectorAll(".doc-delete").forEach((btn) => {
      btn.addEventListener("click", () => deleteDocument(btn.dataset.filename));
    });
  } catch (err) {
    console.error("Failed to load documents:", err);
  }
}

async function deleteDocument(filename) {
  try {
    const res = await fetch(`${API_BASE}/documents/${encodeURIComponent(filename)}`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error("Delete failed");
    await loadDocuments();
  } catch (err) {
    console.error("Failed to delete document:", err);
  }
}

async function uploadFile(file) {
  if (!file.name.toLowerCase().endsWith(".pdf")) {
    uploadStatus.textContent = "Only PDF files are supported.";
    uploadStatus.className = "upload-status error";
    return;
  }

  uploadStatus.textContent = `Uploading ${file.name}...`;
  uploadStatus.className = "upload-status";

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch(`${API_BASE}/upload`, {
      method: "POST",
      body: formData,
    });
    const data = await res.json();

    if (!res.ok) {
      uploadStatus.textContent = data.detail || "Upload failed.";
      uploadStatus.className = "upload-status error";
      return;
    }

    uploadStatus.textContent = `Indexed ${data.chunks_created} chunks.`;
    uploadStatus.className = "upload-status success";
    await loadDocuments();
  } catch (err) {
    uploadStatus.textContent = "Upload failed. Is the server running?";
    uploadStatus.className = "upload-status error";
  }
}

uploadBox.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", () => {
  if (fileInput.files.length > 0) {
    uploadFile(fileInput.files[0]);
    fileInput.value = "";
  }
});

uploadBox.addEventListener("dragover", (e) => {
  e.preventDefault();
  uploadBox.classList.add("dragover");
});

uploadBox.addEventListener("dragleave", () => {
  uploadBox.classList.remove("dragover");
});

uploadBox.addEventListener("drop", (e) => {
  e.preventDefault();
  uploadBox.classList.remove("dragover");
  if (e.dataTransfer.files.length > 0) {
    uploadFile(e.dataTransfer.files[0]);
  }
});

function clearEmptyState() {
  const empty = messages.querySelector(".empty-state");
  if (empty) empty.remove();
}

function addQuestionBubble(question) {
  clearEmptyState();
  const div = document.createElement("div");
  div.className = "msg msg-question";
  div.textContent = question;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}

function addLoadingBubble() {
  const div = document.createElement("div");
  div.className = "msg msg-loading";
  div.id = "loadingBubble";
  div.textContent = "Thinking...";
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}

function removeLoadingBubble() {
  const el = document.getElementById("loadingBubble");
  if (el) el.remove();
}

function addAnswerBubble(answer, sources) {
  const div = document.createElement("div");
  div.className = "msg msg-answer";

  let sourcesHtml = "";
  if (sources && sources.length > 0) {
    sourcesHtml = `<div class="msg-sources">${sources
      .map(
        (s) =>
          `<div class="source-item"><b>Source ${s.source_number}</b> — ${s.filename} (chunk ${s.chunk_index})</div>`
      )
      .join("")}</div>`;
  }

  div.innerHTML = `<div>${answer}</div>${sourcesHtml}`;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}

askForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const question = questionInput.value.trim();
  if (!question) return;

  addQuestionBubble(question);
  questionInput.value = "";
  askButton.disabled = true;
  addLoadingBubble();

  try {
    const res = await fetch(`${API_BASE}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const data = await res.json();

    removeLoadingBubble();

    if (!res.ok) {
      addAnswerBubble(data.detail || "Something went wrong.", []);
    } else {
      addAnswerBubble(data.answer, data.sources);
    }
  } catch (err) {
    removeLoadingBubble();
    addAnswerBubble("Could not reach the server. Is it running?", []);
  } finally {
    askButton.disabled = false;
  }
});

checkHealth();
loadDocuments();
setInterval(checkHealth, 15000);