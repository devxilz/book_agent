// Shared JavaScript for all AI Book Teacher frontend pages.
// Each HTML page sets body[data-page], and this file activates only that page.

const defaultApiBase = window.location.origin.startsWith("http")
  ? window.location.origin
  : "http://127.0.0.1:8000";
const MAX_UPLOAD_BYTES = 100 * 1024 * 1024;

const state = {
  // The frontend is served by FastAPI, so API requests should stay same-origin.
  apiBase: defaultApiBase,
  user: null,
  books: [],
  activeBook: null,
};

const pageName = document.body.dataset.page || "entry";

function qs(selector) {
  // Tiny helper so the rest of the file stays readable.
  return document.querySelector(selector);
}

function setText(selector, value) {
  const element = qs(selector);
  if (element) {
    element.textContent = value;
  }
}

function getApiBase() {
  return state.apiBase.replace(/\/+$/, "");
}

function authHeaders() {
  // Auth now lives in an httpOnly cookie, so JavaScript does not read the token.
  return {};
}

function getFormValues(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function setBusy(form, isBusy) {
  if (!form) {
    return;
  }
  form.querySelectorAll("button, input, textarea").forEach((control) => {
    control.disabled = isBusy;
  });
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => {
    const replacements = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;",
    };
    return replacements[character];
  });
}

// Uploaded files often contain source tags or ".pdf"; this keeps UI titles clean.
function cleanBookTitle(filename) {
  return String(filename)
    .replace(/\.pdf$/i, "")
    .replace(/\([^)]*(z-library|z-lib|1lib|libgen|archive|\.sk|\.com|\.org)[^)]*\)/gi, "")
    .replace(/\[[^\]]*(z-library|z-lib|1lib|libgen|archive|\.sk|\.com|\.org)[^\]]*\]/gi, "")
    .replace(/\s+/g, " ")
    .trim();
}

// Formats the teacher response into readable HTML while escaping unsafe markup.
function formatLessonText(value) {
  return escapeHtml(value)
    .replace(/^### (.*)$/gm, "<h3>$1</h3>")
    .replace(/^## (.*)$/gm, "<h2>$1</h2>")
    .replace(/^# (.*)$/gm, "<h1>$1</h1>")
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br>");
}

async function parseResponse(response) {
  const contentType = response.headers.get("content-type") || "";
  const body = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const message = body?.detail || body?.message || body || response.statusText;
    throw new Error(formatErrorMessage(message));
  }

  return body;
}

function formatErrorMessage(message) {
  if (Array.isArray(message)) {
    return message
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }

        const location = Array.isArray(item.loc) ? item.loc.join(".") : "field";
        return `${location}: ${item.msg || "Invalid value"}`;
      })
      .join("\n");
  }

  if (message && typeof message === "object") {
    return JSON.stringify(message, null, 2);
  }

  return String(message);
}

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  // credentials:"same-origin" sends the httpOnly cookie to this FastAPI app.
  const response = await fetch(`${getApiBase()}${path}`, {
    ...options,
    headers,
    credentials: "same-origin",
  });

  return parseResponse(response);
}

async function logout() {
  try {
    await request("/logout", { method: "POST" });
  } finally {
    // Clean up keys used by older frontend versions.
    localStorage.removeItem("aiBookTeacherToken");
    localStorage.removeItem("aiBookTeacherApiBase");
    state.user = null;
  }
  window.location.href = "/login";
}

function setupLogout() {
  const button = qs("#logoutButton");
  if (button) {
    button.addEventListener("click", logout);
  }
}

function setPageStatus(message) {
  setText("#pageStatus", message);
  setText("#appStatus", message);
}

function renderAssistantMessage(type, text) {
  const container = qs("#chatMessages");
  if (!container) {
    return;
  }

  const bubble = document.createElement("article");
  const className = type === "user" ? "user-bubble" : type === "error" ? "system-bubble error" : type === "system" ? "system-bubble" : "assistant-bubble";
  bubble.className = className;
  bubble.textContent = text;
  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

async function loadCurrentUser() {
  state.user = await request("/library/me", {
    headers: authHeaders(),
  });
  return state.user;
}

async function requireSession() {
  try {
    // /library/me is the frontend's "am I logged in?" endpoint.
    await loadCurrentUser();
    return true;
  } catch {
    window.location.href = "/login";
    return false;
  }
}

async function loadBooks() {
  const data = await request("/library/books", {
    headers: authHeaders(),
  });
  state.books = data.books || [];
  return state.books;
}

async function loadChapters(bookId) {
  const data = await request(`/library/books/${encodeURIComponent(bookId)}/chapters`, {
    headers: authHeaders(),
  });
  return data.chapters || [];
}

function renderBookList(targetSelector, mode = "upload") {
  const container = qs(targetSelector);
  if (!container) {
    return;
  }

  if (!state.books.length) {
    container.innerHTML = '<p class="empty-state">No books uploaded yet.</p>';
    return;
  }

  container.innerHTML = "";
  state.books.forEach((book) => {
    const card = document.createElement("button");
    card.type = "button";
    card.className = `book-card ${state.activeBook?.book_id === book.book_id ? "is-active" : ""}`;
    const title = book.display_name || cleanBookTitle(book.book_name);
    card.innerHTML = `
      <span class="book-card-kicker">${mode === "reader" ? "Reading" : "Textbook"}</span>
      <h3>${escapeHtml(title)}</h3>
    `;

    if (mode === "reader") {
      card.addEventListener("click", () => selectReaderBook(book));
    } else {
      card.addEventListener("click", () => {
        sessionStorage.setItem("aiBookTeacherActiveBookId", book.book_id);
        window.location.href = "/reader";
      });
    }

    container.appendChild(card);
  });
}

function renderChapterList(chapters) {
  const container = qs("#chapterList");
  if (!container) {
    return;
  }

  const seen = new Set();
  const unique = chapters.filter((chapter) => {
    const key = `${chapter.title}|${chapter.start_page}|${chapter.end_page}`;
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });

  if (!unique.length) {
    container.innerHTML = '<p class="empty-state">No chapters found.</p>';
    return;
  }

  container.innerHTML = "";
  unique.forEach((chapter) => {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "chapter-card";
    card.innerHTML = `
      <h3>${escapeHtml(chapter.title)}</h3>
    `;
    card.addEventListener("click", () => {
      const pageInput = qs("#pageForm")?.elements.page;
      if (pageInput) {
        pageInput.value = chapter.start_page;
      }
      renderAssistantMessage("system", `Page set to ${chapter.start_page}.`);
    });
    container.appendChild(card);
  });
}

async function selectReaderBook(book) {
  state.activeBook = book;
  sessionStorage.setItem("aiBookTeacherActiveBookId", book.book_id);

  const pageForm = qs("#pageForm");
  if (pageForm) {
    pageForm.elements.book_id.value = book.book_id;
    pageForm.elements.page.value = "1";
  }

  setText("#activeBookTitle", book.display_name || cleanBookTitle(book.book_name));
  setText("#activeBookMeta", `${book.page_count} pages - ${book.chapter_count} chapters`);
  renderBookList("#bookList", "reader");

  const chapters = await loadChapters(book.book_id);
  renderChapterList(chapters);
}

async function initLoginPage() {
  const form = qs("#loginForm");
  if (!form) {
    return;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const values = getFormValues(form);

    setBusy(form, true);
    setText("#authStatus", "Logging in...");
    try {
      const body = new URLSearchParams();
      body.set("username", values.email);
      body.set("password", values.password);

      await request("/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body:body,
      });

      // Remove old localStorage tokens from earlier versions of this frontend.
      localStorage.removeItem("aiBookTeacherToken");
      localStorage.removeItem("aiBookTeacherApiBase");
      window.location.href = "/upload";
    } catch (error) {
      setText("#authStatus", error.message);
    } finally {
      setBusy(form, false);
    }
  });
}

async function initSignupPage() {
  const form = qs("#signupForm");
  if (!form) {
    return;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const values = getFormValues(form);

    setBusy(form, true);
    setText("#authStatus", "Creating account...");
    try {
      await request("/signin", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
      });

      setText("#authStatus", "Account created. Redirecting to login...");
      window.setTimeout(() => {
        window.location.href = "/login";
      }, 900);
    } catch (error) {
      setText("#authStatus", error.message);
    } finally {
      setBusy(form, false);
    }
  });
}

async function initUploadPage() {
  if (!(await requireSession())) {
    return;
  }

  setupLogout();
  setPageStatus("Loading your library...");

  try {
    await loadBooks();
    renderBookList("#bookList", "upload");
    setPageStatus(`Signed in as ${state.user.email}`);
  } catch (error) {
    setPageStatus(error.message);
  }

  const uploadForm = qs("#uploadForm");
  uploadForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    setBusy(uploadForm, true);
    setPageStatus("Uploading and indexing PDF...");

    try {
      const fileInput = uploadForm.elements.book;
      const selectedFile = fileInput.files[0];
      if (!selectedFile) {
        throw new Error("Choose a PDF before uploading.");
      }
      if (!selectedFile.name.toLowerCase().endsWith(".pdf")) {
        throw new Error("Only PDF files are allowed.");
      }
      if (selectedFile.size > MAX_UPLOAD_BYTES) {
        throw new Error("PDF is too large. Maximum allowed size is 100 MB.");
      }

      const body = new FormData();
      body.append("file", selectedFile);

      await request("/upload/books", {
        method: "POST",
        headers: authHeaders(),
        body,
      });

      uploadForm.reset();
      await loadBooks();
      renderBookList("#bookList", "upload");
      setPageStatus("Upload complete. Select the book to open it in the reader.");
    } catch (error) {
      setPageStatus(error.message);
    } finally {
      setBusy(uploadForm, false);
    }
  });

  qs("#refreshLibrary")?.addEventListener("click", async () => {
    setPageStatus("Refreshing library...");
    try {
      await loadBooks();
      renderBookList("#bookList", "upload");
      setPageStatus("Library refreshed.");
    } catch (error) {
      setPageStatus(error.message);
    }
  });
}

async function initReaderPage() {
  if (!(await requireSession())) {
    return;
  }

  setupLogout();

  try {
    await loadBooks();
    renderBookList("#bookList", "reader");

    const savedBookId = sessionStorage.getItem("aiBookTeacherActiveBookId");
    const selectedBook = state.books.find((book) => book.book_id === savedBookId) || state.books[0];
    if (selectedBook) {
      await selectReaderBook(selectedBook);
    } else {
      qs("#lessonOutput").innerHTML = '<p class="empty-state">Upload a PDF first, then return to the reader.</p>';
    }
  } catch (error) {
    renderAssistantMessage("error", error.message);
  }

  qs("#refreshLibrary")?.addEventListener("click", async () => {
    try {
      await loadBooks();
      renderBookList("#bookList", "reader");
    } catch (error) {
      renderAssistantMessage("error", error.message);
    }
  });

  qs("#pageForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    await teachCurrentPage();
  });

  qs("#previousPage")?.addEventListener("click", async () => {
    const pageInput = qs("#pageForm").elements.page;
    const page = Number(pageInput.value);
    if (page <= 1) {
      renderAssistantMessage("system", "Page number cannot go below 1.");
      return;
    }
    pageInput.value = page - 1;
    await teachCurrentPage();
  });

  qs("#nextPage")?.addEventListener("click", async () => {
    const pageInput = qs("#pageForm").elements.page;
    pageInput.value = Number(pageInput.value || 1) + 1;
    await teachCurrentPage();
  });

  qs("#questionForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    await askQuestion();
  });

  qs("#clearChat")?.addEventListener("click", () => {
    qs("#chatMessages").innerHTML = "";
    renderAssistantMessage("assistant", "Chat cleared. Ask a question from the selected book.");
  });
}

async function teachCurrentPage() {
  const form = qs("#pageForm");
  const lessonOutput = qs("#lessonOutput");
  if (!form || !lessonOutput) {
    return;
  }
  const values = getFormValues(form);
  const page = Number(values.page);
  const maxPage = Number(state.activeBook?.max_page || 0);

  if (!values.book_id) {
    renderAssistantMessage("error", "Select a book before teaching a page.");
    return;
  }

  if (maxPage && page > maxPage) {
    renderAssistantMessage("error", `This book only has ${maxPage} pages.`);
    return;
  }

  setBusy(form, true);
  lessonOutput.textContent = "Teaching page...";

  try {
    const params = new URLSearchParams({
      book_id: values.book_id,
      page: values.page,
    });

    const data = await request(`/chat/page_summary?${params.toString()}`, {
      method: "POST",
      headers: authHeaders(),
    });

    lessonOutput.innerHTML = formatLessonText(data.response);
    renderAssistantMessage("system", `Page ${values.page} lesson is ready.`);
  } catch (error) {
    lessonOutput.textContent = error.message;
    renderAssistantMessage("error", error.message);
  } finally {
    setBusy(form, false);
  }
}

async function askQuestion() {
  const form = qs("#questionForm");
  if (!form) {
    return;
  }
  const values = getFormValues(form);
  const question = values.text.trim();
  const bookId = state.activeBook?.book_id || qs("#pageForm")?.elements.book_id.value;

  if (!question) {
    return;
  }

  if (!bookId) {
    renderAssistantMessage("error", "Select a book before asking a question.");
    return;
  }

  setBusy(form, true);
  renderAssistantMessage("user", question);

  try {
    const params = new URLSearchParams({
      text: question,
      book_id: bookId,
    });

    const data = await request(`/chat/user_query?${params.toString()}`, {
      method: "POST",
      headers: authHeaders(),
    });

    renderAssistantMessage("assistant", data.response);
    form.reset();
  } catch (error) {
    renderAssistantMessage("error", error.message);
  } finally {
    setBusy(form, false);
  }
}

if (pageName === "login") {
  initLoginPage();
}

if (pageName === "signup") {
  initSignupPage();
}

if (pageName === "upload") {
  initUploadPage();
}

if (pageName === "reader") {
  initReaderPage();
}
