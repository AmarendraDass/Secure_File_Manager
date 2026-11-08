const landingScreen = document.getElementById("landing-screen");
const authScreen = document.getElementById("auth-screen");
const authForm = document.getElementById("auth-form");
const authUsername = document.getElementById("auth-username");
const authPassword = document.getElementById("auth-password");
const authError = document.getElementById("auth-error");
const authSubmit = document.getElementById("auth-submit");
const authTitle = document.getElementById("auth-title");
const authDescription = document.getElementById("auth-description");
const authSwitchPrompt = document.getElementById("auth-switch-prompt");
const authToggle = document.getElementById("auth-toggle");
const passwordHint = document.getElementById("password-hint");
const appShell = document.querySelector(".app-shell");
const uploadForm = document.getElementById("upload-form");
const fileInput = document.getElementById("file-input");
const fileLabel = document.getElementById("file-label");
const uploadButton = document.getElementById("upload-button");
const uploadResult = document.getElementById("upload-result");
const dropzone = document.getElementById("dropzone");
const filesTableBody = document.querySelector("#files-table tbody");
const emptyState = document.getElementById("table-empty");
const noResultsState = document.getElementById("table-no-results");
const searchInput = document.getElementById("search-input");
const toast = document.getElementById("toast");

let files = [];
let toastTimer;
let authMode = "login";
let accessToken = sessionStorage.getItem("accessToken") || "";

function showToast(message, isError = false) {
    toast.textContent = message;
    toast.classList.toggle("toast-error", isError);
    toast.classList.add("toast-visible");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("toast-visible"), 3200);
}

function setConnection(connected) {
    const status = document.getElementById("connection-status");
    status.classList.toggle("is-connected", connected);
    const dot = document.createElement("span");
    dot.className = "status-dot";
    status.replaceChildren(dot, document.createTextNode(connected ? " Connected" : " Unavailable"));
}

function errorMessage(detail, fallback) {
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map(item => item.msg).filter(Boolean).join(" ");
    return fallback;
}

function showAuth(message = "") {
    landingScreen.hidden = true;
    appShell.hidden = true;
    authScreen.hidden = false;
    authError.textContent = message;
    authError.hidden = !message;
    authUsername.focus();
}

function showLanding() {
    landingScreen.hidden = false;
    authScreen.hidden = true;
    appShell.hidden = true;
}

function setAuthMode(mode) {
    authMode = mode;
    const registering = mode === "register";
    authTitle.textContent = registering ? "Create your private vault" : "Sign in to your vault";
    authDescription.textContent = registering
        ? "Create an account to keep your file records private."
        : "Access your account-isolated files and integrity records.";
    authSubmit.textContent = registering ? "Create account" : "Sign in";
    authSwitchPrompt.textContent = registering ? "Already have an account?" : "New to Vaultline?";
    authToggle.textContent = registering ? "Sign in" : "Create an account";
    authPassword.autocomplete = registering ? "new-password" : "current-password";
    authPassword.minLength = registering ? 12 : 1;
    passwordHint.textContent = registering
        ? "Use at least 12 characters. Passwords are stored as bcrypt hashes."
        : "Use your account password.";
    authError.hidden = true;
    authError.textContent = "";
}

function clearSession(message = "") {
    accessToken = "";
    sessionStorage.removeItem("accessToken");
    files = [];
    setAuthMode("login");
    showAuth(message);
}

async function api(url, options = {}) {
    const headers = new Headers(options.headers || {});
    if (accessToken && !url.startsWith("/auth/")) {
        headers.set("Authorization", `Bearer ${accessToken}`);
    }

    const response = await fetch(url, { ...options, headers });
    const contentType = response.headers.get("content-type") || "";
    const body = contentType.includes("application/json") ? await response.json() : null;
    if (response.status === 401 && accessToken && !url.startsWith("/auth/")) {
        clearSession("Your session expired. Please sign in again.");
    }
    if (!response.ok) {
        throw new Error(errorMessage(body?.detail, `Request failed (${response.status})`));
    }
    return body;
}

function formatDate(value) {
    if (!value) return "—";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short"
    });
}

function createCell(text, className = "") {
    const cell = document.createElement("td");
    if (className) cell.className = className;
    cell.textContent = text || "—";
    return cell;
}

function renderFiles() {
    const query = searchInput.value.trim().toLowerCase();
    const filtered = files.filter(file =>
        [file.filename, file.mime_type, file.sha256, file.extension]
            .some(value => String(value || "").toLowerCase().includes(query))
    );
    filesTableBody.replaceChildren();
    document.getElementById("table-count").textContent = String(files.length);
    emptyState.hidden = files.length > 0;
    noResultsState.hidden = files.length === 0 || filtered.length > 0;

    filtered.forEach(file => {
        const row = document.createElement("tr");
        const nameCell = document.createElement("td");
        nameCell.className = "file-name-cell";
        const fileGlyph = document.createElement("span");
        fileGlyph.className = "file-glyph";
        fileGlyph.setAttribute("aria-hidden", "true");
        fileGlyph.textContent = "▧";
        const name = document.createElement("span");
        name.className = "file-name";
        name.textContent = file.filename || "Unnamed file";
        nameCell.append(fileGlyph, name);

        const typeCell = document.createElement("td");
        const typeBadge = document.createElement("span");
        typeBadge.className = "type-badge";
        typeBadge.textContent = file.mime_type || "Unknown type";
        typeCell.appendChild(typeBadge);

        const hashCell = document.createElement("td");
        hashCell.className = "hash-cell";
        const hash = document.createElement("code");
        hash.textContent = file.sha256 || "—";
        hash.title = file.sha256 || "";
        hashCell.appendChild(hash);

        const actionsCell = document.createElement("td");
        actionsCell.className = "actions-cell";
        const download = document.createElement("button");
        download.className = "icon-button";
        download.type = "button";
        download.setAttribute("aria-label", `Download ${file.filename || "file"}`);
        download.title = "Download";
        download.textContent = "↓";
        download.addEventListener("click", () => downloadFile(file));
        const remove = document.createElement("button");
        remove.className = "icon-button delete-button";
        remove.type = "button";
        remove.setAttribute("aria-label", `Delete ${file.filename || "file"}`);
        remove.title = "Delete";
        remove.textContent = "×";
        remove.addEventListener("click", () => deleteFile(file));
        actionsCell.append(download, remove);

        row.append(
            nameCell,
            typeCell,
            hashCell,
            createCell(formatDate(file.upload_time), "date-cell"),
            actionsCell
        );
        filesTableBody.appendChild(row);
    });
}

async function loadFiles() {
    const refreshButton = document.getElementById("refresh-btn");
    refreshButton.disabled = true;
    refreshButton.classList.add("is-loading");
    try {
        const data = await api("/files/list");
        if (!Array.isArray(data)) throw new Error("The server returned an invalid file list.");
        files = data;
        document.getElementById("metric-files").textContent = String(files.length);
        document.getElementById("metric-formats").textContent =
            String(new Set(files.map(file => file.mime_type).filter(Boolean)).size);
        document.getElementById("metric-integrity").textContent =
            String(files.filter(file => file.sha256).length);
        document.getElementById("nav-file-count").textContent = String(files.length);
        renderFiles();
        setConnection(true);
    } catch (error) {
        setConnection(false);
        showToast(error.message || "Could not load the file list.", true);
        document.getElementById("metric-files").textContent = "—";
        document.getElementById("metric-formats").textContent = "—";
        document.getElementById("metric-integrity").textContent = "—";
    } finally {
        refreshButton.disabled = false;
        refreshButton.classList.remove("is-loading");
    }
}

async function enterWorkspace(username) {
    document.getElementById("account-name").textContent = username;
    authScreen.hidden = true;
    appShell.hidden = false;
    await loadFiles();
}

async function downloadFile(file) {
    try {
        const response = await fetch(`/files/download/${encodeURIComponent(file.id)}`, {
            headers: { Authorization: `Bearer ${accessToken}` }
        });
        if (response.status === 401) {
            clearSession("Your session expired. Please sign in again.");
            return;
        }
        if (!response.ok) {
            const body = await response.json().catch(() => null);
            throw new Error(errorMessage(body?.detail, "Could not download the file."));
        }
        const objectUrl = URL.createObjectURL(await response.blob());
        const link = document.createElement("a");
        link.href = objectUrl;
        link.download = file.filename || "download";
        document.body.appendChild(link);
        link.click();
        link.remove();
        setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
    } catch (error) {
        showToast(error.message || "Could not download the file.", true);
    }
}

async function deleteFile(file) {
    if (!window.confirm(`Delete "${file.filename}" from your private vault?`)) return;
    try {
        await api(`/files/delete/${encodeURIComponent(file.id)}`, { method: "DELETE" });
        showToast("File deleted from your vault.");
        await loadFiles();
    } catch (error) {
        showToast(error.message || "Could not delete the file.", true);
    }
}

function selectFile(file) {
    if (!file) return;
    fileLabel.textContent = file.name;
    fileLabel.classList.add("selected-file-name");
    uploadButton.disabled = false;
}

authToggle.addEventListener("click", () => {
    setAuthMode(authMode === "login" ? "register" : "login");
});

document.getElementById("landing-login").addEventListener("click", () => {
    setAuthMode("login");
    showAuth();
});
document.getElementById("landing-register").addEventListener("click", () => {
    setAuthMode("register");
    showAuth();
});
document.getElementById("landing-get-started").addEventListener("click", () => {
    setAuthMode("register");
    showAuth();
});

authForm.addEventListener("submit", async event => {
    event.preventDefault();
    authSubmit.disabled = true;
    authSubmit.textContent = authMode === "register" ? "Creating account..." : "Signing in...";
    authError.hidden = true;
    const username = authUsername.value.trim();
    const password = authPassword.value;
    try {
        const response = authMode === "register"
            ? await api("/auth/register", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password })
            })
            : await api("/auth/login", {
                method: "POST",
                headers: { "Content-Type": "application/x-www-form-urlencoded" },
                body: new URLSearchParams({ username, password })
            });
        accessToken = response.access_token;
        sessionStorage.setItem("accessToken", accessToken);
        authPassword.value = "";
        await enterWorkspace(response.username || username);
    } catch (error) {
        authError.textContent = error.message || "Authentication failed. Please try again.";
        authError.hidden = false;
    } finally {
        authSubmit.disabled = false;
        authSubmit.textContent = authMode === "register" ? "Create account" : "Sign in";
    }
});

document.getElementById("logout-btn").addEventListener("click", () => clearSession());
document.getElementById("refresh-btn").addEventListener("click", loadFiles);
searchInput.addEventListener("input", renderFiles);
fileInput.addEventListener("change", () => selectFile(fileInput.files[0]));

document.addEventListener("keydown", event => {
    if (event.key === "/" && !["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)) {
        event.preventDefault();
        searchInput.focus();
    }
});

for (const eventName of ["dragenter", "dragover"]) {
    dropzone.addEventListener(eventName, event => {
        event.preventDefault();
        dropzone.classList.add("is-dragging");
    });
}
for (const eventName of ["dragleave", "drop"]) {
    dropzone.addEventListener(eventName, event => {
        event.preventDefault();
        dropzone.classList.remove("is-dragging");
    });
}
dropzone.addEventListener("drop", event => {
    const [file] = event.dataTransfer.files;
    if (!file) return;
    const transfer = new DataTransfer();
    transfer.items.add(file);
    fileInput.files = transfer.files;
    selectFile(file);
});

uploadForm.addEventListener("submit", async event => {
    event.preventDefault();
    if (!fileInput.files.length) return;
    uploadButton.disabled = true;
    uploadButton.classList.add("is-loading");
    uploadButton.textContent = "Uploading...";
    uploadResult.hidden = true;
    try {
        const result = await api("/files/upload", {
            method: "POST",
            body: new FormData(uploadForm)
        });
        uploadResult.replaceChildren();
        uploadResult.className = `upload-result${result.extension_mismatch ? " result-warning" : " result-success"}`;
        uploadResult.hidden = false;
        const title = document.createElement("strong");
        title.textContent = result.extension_mismatch
            ? "File uploaded — extension may not match its detected type"
            : "File uploaded and checksum recorded";
        const details = document.createElement("span");
        details.textContent = `${result.mime_type || "Unknown type"} · SHA-256 `;
        const checksum = document.createElement("code");
        checksum.textContent = result.sha256 || "unavailable";
        details.appendChild(checksum);
        uploadResult.append(title, details);
        showToast("File added to your vault.");
        uploadForm.reset();
        fileLabel.classList.remove("selected-file-name");
        fileLabel.replaceChildren(document.createTextNode("Drop a file here, or "));
        const browseLabel = document.createElement("span");
        browseLabel.textContent = "browse";
        fileLabel.appendChild(browseLabel);
        await loadFiles();
    } catch (error) {
        showToast(error.message || "Upload failed. Please try again.", true);
    } finally {
        uploadButton.disabled = !fileInput.files.length;
        uploadButton.classList.remove("is-loading");
        uploadButton.replaceChildren(document.createTextNode("Upload file "));
        const arrow = document.createElement("span");
        arrow.setAttribute("aria-hidden", "true");
        arrow.textContent = "→";
        uploadButton.appendChild(arrow);
    }
});

async function initialize() {
    if (!accessToken) {
        showLanding();
        return;
    }
    try {
        const user = await api("/auth/me", {
            headers: { Authorization: `Bearer ${accessToken}` }
        });
        await enterWorkspace(user.username);
    } catch {
        clearSession("Please sign in to access your private vault.");
    }
}

initialize();
