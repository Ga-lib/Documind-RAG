const API_BASE = "";

const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const uploadBox = document.getElementById("uploadBox");
const fileInput = document.getElementById("fileInput");
const uploadStatus = document.getElementById("uploadStatus");
const docList = document.getElementById("docList");
const docFilter = document.getElementById("docFilter");
const messages = document.getElementById("messages");
const askForm = document.getElementById("askForm");
const questionInput = document.getElementById("questionInput");
const askButton = document.getElementById("askButton");

async function apiFetch(url, options = {}) {
  const headers = new Headers(options.headers || {});
  let key = sessionStorage.getItem("documind_api_key") || "";
  if (key) headers.set("X-API-Key", key);
  let response = await fetch(url, { ...options, headers });
  if (response.status === 401) {
    key = window.prompt("Enter your DocuMind API key (stored only for this browser session):") || "";
    if (!key) return response;
    sessionStorage.setItem("documind_api_key", key);
    headers.set("X-API-Key", key);
    response = await fetch(url, { ...options, headers });
  }
  return response;
}

async function checkHealth() {
  try {
    const res = await apiFetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error("not ok");
    statusDot.className = "w-2 h-2 rounded-full bg-neon pulse-dot";
    statusText.textContent = "Online";
  } catch {
    statusDot.className = "w-2 h-2 rounded-full bg-red-500";
    statusText.textContent = "Offline";
  }
}

async function loadDocuments() {
  try {
    const res = await apiFetch(`${API_BASE}/documents`);
    const data = await res.json();

    docList.innerHTML = "";
    docFilter.innerHTML = '<option value="">All documents</option>';

    if (!data.documents || data.documents.length === 0) {
      docList.innerHTML = '<li class="text-sm italic text-gray-600">No documents yet</li>';
      return;
    }

    data.documents.forEach((doc, i) => {
      const li = document.createElement("li");
      li.className = "group flex items-center justify-between bg-elevated border border-edge rounded-lg px-3 py-2.5 text-sm anim-slideIn";
      li.style.animationDelay = `${i * 0.05}s`;
      const name = document.createElement("span");
      name.className = "min-w-0 truncate";
      name.textContent = doc.filename;
      name.title = doc.filename;
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "doc-delete opacity-0 group-hover:opacity-100 transition-opacity duration-150 text-gray-500 hover:text-red-400 text-base px-1";
      remove.textContent = "×";
      remove.setAttribute("aria-label", `Delete ${doc.filename}`);
      remove.addEventListener("click", () => deleteDocument(doc.filename));
      li.append(name, remove);
      docList.appendChild(li);

      const option = document.createElement("option");
      option.value = doc.filename;
      option.textContent = doc.filename.replace(/\\.pdf$/i, "");
      docFilter.appendChild(option);
    });

  } catch (err) {
    console.error("Failed to load documents:", err);
  }
}

async function deleteDocument(filename) {
  try {
    const res = await apiFetch(`${API_BASE}/documents/${encodeURIComponent(filename)}`, {
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
    uploadStatus.className = "mt-2 text-xs min-h-[16px] text-red-400";
    return;
  }

  uploadStatus.textContent = `Uploading ${file.name}...`;
  uploadStatus.className = "mt-2 text-xs min-h-[16px] text-gray-400";

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await apiFetch(`${API_BASE}/upload`, { method: "POST", body: formData });
    const data = await res.json();

    if (!res.ok) {
      uploadStatus.textContent = data.detail || "Upload failed.";
      uploadStatus.className = "mt-2 text-xs min-h-[16px] text-red-400";
      return;
    }

    uploadStatus.textContent = `Indexed ${data.chunks_created} chunks.`;
    uploadStatus.className = "mt-2 text-xs min-h-[16px] text-neon";
    await loadDocuments();
  } catch (err) {
    uploadStatus.textContent = "Upload failed. Is the server running?";
    uploadStatus.className = "mt-2 text-xs min-h-[16px] text-red-400";
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
  uploadBox.classList.add("border-blue-500", "bg-blue-500/5", "scale-[1.02]");
});
uploadBox.addEventListener("dragleave", () => {
  uploadBox.classList.remove("border-blue-500", "bg-blue-500/5", "scale-[1.02]");
});
uploadBox.addEventListener("drop", (e) => {
  e.preventDefault();
  uploadBox.classList.remove("border-blue-500", "bg-blue-500/5", "scale-[1.02]");
  if (e.dataTransfer.files.length > 0) uploadFile(e.dataTransfer.files[0]);
});

function clearEmptyState() {
  const empty = messages.querySelector(".empty-state-msg");
  if (empty) empty.remove();
}

function addQuestionBubble(question) {
  clearEmptyState();
  const wrap = document.createElement("div");
  wrap.className = "flex justify-end anim-fadeUp";
  wrap.innerHTML = `
    <div class="max-w-[75%] text-white text-[15px] leading-relaxed px-4 py-3 rounded-2xl rounded-br-md"
         style="background: linear-gradient(135deg, #0052D4, #4364F7);">
      ${escapeHtml(question)}
    </div>
  `;
  messages.appendChild(wrap);
  messages.scrollTop = messages.scrollHeight;
}

function addLoadingBubble() {
  const div = document.createElement("div");
  div.id = "loadingBubble";
  div.className = "max-w-3xl w-full mx-auto flex items-center gap-1 text-gray-400 text-sm anim-fadeUp";
  div.innerHTML = `Generating<span class="blink-cursor ml-1">▍</span>`;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}

function removeLoadingBubble() {
  const el = document.getElementById("loadingBubble");
  if (el) el.remove();
}

function escapeHtml(str) {
  const d = document.createElement("div");
  d.textContent = str;
  return d.innerHTML;
}

function addAnswerBubble(answer, sources) {
  const wrap = document.createElement("div");
  wrap.className = "max-w-3xl w-full mx-auto anim-fadeUp";

  const uid = `acc-${Date.now()}`;

  let accordionRows = "";
  let pillTabs = "";

  if (sources && sources.length > 0) {
    accordionRows = sources
      .map((s, i) => {
        const rowId = `${uid}-row-${i}`;
        return `
          <div class="border-b border-edge last:border-b-0">
            <button
              type="button"
              class="acc-toggle w-full flex items-center justify-between text-left px-3 py-2 text-xs text-gray-400 hover:text-gray-200 transition-colors duration-150"
              data-target="${rowId}"
            >
              <span><b class="text-gray-300">Source ${s.source_number}</b> — ${escapeHtml(s.filename)} (chunk ${s.chunk_index})</span>
              <span class="chevron text-gray-600">&#8250;</span>
            </button>
            <div id="${rowId}" class="accordion-body px-3">
              <p class="text-xs text-gray-500 pb-3 leading-relaxed">${escapeHtml(s.text_snippet)}</p>
            </div>
          </div>
        `;
      })
      .join("");

    pillTabs = sources
      .map(
        (s) =>
          `<span class="text-[11px] bg-elevated2 text-gray-400 border border-edge rounded-full px-3 py-1">chunk ${s.chunk_index}</span>`
      )
      .join("");
  }

  wrap.innerHTML = `
    ${
      sources && sources.length > 0
        ? `<div class="bg-elevated border border-edge rounded-xl mb-3 overflow-hidden">
             <div class="px-3 py-2 text-[11px] uppercase tracking-wider text-gray-500 border-b border-edge">References (${sources.length})</div>
             ${accordionRows}
           </div>`
        : ""
    }
    <div class="bg-elevated border border-edge rounded-xl px-5 py-4 text-[15px] leading-relaxed text-white">
      ${escapeHtml(answer)}
      ${
        pillTabs
          ? `<div class="flex flex-wrap gap-2 mt-4 pt-4 border-t border-edge">${pillTabs}</div>`
          : ""
      }
    </div>
  `;

  messages.appendChild(wrap);

  wrap.querySelectorAll(".acc-toggle").forEach((btn) => {
    btn.addEventListener("click", () => {
      const body = document.getElementById(btn.dataset.target);
      const chevron = btn.querySelector(".chevron");
      body.classList.toggle("open");
      chevron.classList.toggle("open");
    });
  });

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
    const res = await apiFetch(`${API_BASE}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        source_filename: docFilter.value || null,
      }),
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