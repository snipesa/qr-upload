(() => {
  const config = {
    httpApiUrl: "https://3rdlx5nks0.execute-api.us-east-1.amazonaws.com/dev",
    ...(window.QR_UPLOAD_CONFIG || {}),
  };

  const state = {
    sessionId: null,
    uploadUrl: null,
    uploadKey: null,
    file: null,
  };

  const elements = {
    sessionId: document.getElementById("session-id"),
    fileInput: document.getElementById("file-input"),
    fileName: document.getElementById("file-name"),
    uploadButton: document.getElementById("upload-button"),
    successDetails: document.getElementById("success-details"),
    errorMessage: document.getElementById("error-message"),
    retryButton: document.getElementById("retry-upload"),
  };

  function showView(name) {
    document.querySelectorAll(".view").forEach((view) => {
      view.classList.toggle("view--active", view.dataset.view === name);
    });
  }

  function showError(message) {
    elements.errorMessage.textContent = message;
    showView("error");
  }

  function setFile(file) {
    state.file = file || null;
    elements.fileName.textContent = file ? file.name : "";
    elements.uploadButton.disabled = !file;
  }

  async function loadUploadUrl() {
    showView("loading");

    const response = await fetch(
      `${config.httpApiUrl}/upload-url?sessionId=${encodeURIComponent(state.sessionId)}`
    );

    if (!response.ok) {
      throw new Error(`Unable to fetch upload URL (${response.status})`);
    }

    const data = await response.json();
    state.uploadUrl = data.uploadUrl;
    state.uploadKey = data.uploadKey;
  }

  async function uploadFile() {
    if (!state.file) {
      showError("Please select an image to upload.");
      return;
    }

    if (!state.uploadUrl) {
      showError("Upload URL not ready yet. Please try again.");
      return;
    }

    showView("uploading");

    const response = await fetch(state.uploadUrl, {
      method: "PUT",
      headers: {
        "Content-Type": state.file.type || "application/octet-stream",
      },
      body: state.file,
    });

    if (!response.ok) {
      throw new Error(`Upload failed (${response.status})`);
    }

    elements.successDetails.textContent = state.uploadKey
      ? `Uploaded as ${state.uploadKey}.`
      : "Upload finished successfully.";
    showView("success");
  }

  async function init() {
    const params = new URLSearchParams(window.location.search);
    state.sessionId = params.get("sessionId");

    if (!state.sessionId) {
      showError("Missing session id. Please rescan the QR code.");
      return;
    }

    elements.sessionId.textContent = state.sessionId;
    setFile(null);

    try {
      await loadUploadUrl();
      showView("ready");
    } catch (error) {
      console.error("Failed to prepare upload", error);
      showError("Unable to prepare the upload. Please try again.");
    }
  }

  elements.fileInput.addEventListener("change", (event) => {
    const file = event.target.files && event.target.files[0];
    setFile(file);
  });

  elements.uploadButton.addEventListener("click", async () => {
    try {
      await uploadFile();
    } catch (error) {
      console.error("Upload failed", error);
      showError("Upload failed. Please try again.");
    }
  });

  elements.retryButton.addEventListener("click", () => {
    init();
  });

  window.addEventListener("DOMContentLoaded", () => {
    init();
  });
})();
