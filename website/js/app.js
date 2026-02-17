(() => {
  const infoMessages = [
    "Did you know? QR codes can store thousands of characters.",
    "Tip: Use a well-lit area for faster scanning.",
    "Quick fact: QR stands for Quick Response.",
    "Uploads are temporary and auto-expire for safety.",
    "JPEG, PNG, and GIF files are supported.",
  ];

  class QRUploadApp {
    constructor() {
      this.config = {
        httpApiUrl: "https://YOUR_HTTP_API_ID.execute-api.REGION.amazonaws.com",
        wsApiUrl: "wss://YOUR_WS_API_ID.execute-api.REGION.amazonaws.com/production",
        ...(window.QR_UPLOAD_CONFIG || {}),
      };

      this.state = {
        sessionId: null,
        wsClient: null,
        currentView: "initial",
      };

      this.elements = {
        infoMessage: document.getElementById("info-message"),
        sessionId: document.getElementById("session-id"),
        uploadUrl: document.getElementById("upload-url"),
        qrCode: document.getElementById("qr-code"),
        successDetails: document.getElementById("success-details"),
        errorMessage: document.getElementById("error-message"),
        startButton: document.getElementById("start-upload"),
        cancelButton: document.getElementById("cancel-upload"),
        retryButton: document.getElementById("retry-upload"),
        resetButton: document.getElementById("reset-upload"),
        newUploadButton: document.getElementById("new-upload"),
      };
    }

    init() {
      this.displayRandomMessage();
      this.attachEvents();
      this.showView("initial");
    }

    displayRandomMessage() {
      const message = infoMessages[Math.floor(Math.random() * infoMessages.length)];
      this.elements.infoMessage.textContent = message;
    }

    attachEvents() {
      this.elements.startButton.addEventListener("click", () => this.startUpload());
      this.elements.cancelButton.addEventListener("click", () => this.cancelUpload());
      this.elements.retryButton.addEventListener("click", () => this.startUpload());
      this.elements.resetButton.addEventListener("click", () => this.reset());
      this.elements.newUploadButton.addEventListener("click", () => this.reset());
    }

    showView(name) {
      document.querySelectorAll(".view").forEach((view) => {
        view.classList.toggle("view--active", view.dataset.view === name);
      });
      this.state.currentView = name;
    }

    async startUpload() {
      this.showView("loading");
      this.clearError();

      try {
        const session = await this.createSession();
        this.state.sessionId = session.sessionId;
        const uploadUrl = `${this.config.httpApiUrl}/upload-url?sessionId=${encodeURIComponent(
          session.sessionId
        )}`;

        this.elements.sessionId.textContent = session.sessionId;
        this.elements.uploadUrl.textContent = uploadUrl;
        window.QRGenerator.generateQRCode(this.elements.qrCode, uploadUrl);

        this.connectWebSocket(session.sessionId);
        this.showView("qr");
      } catch (error) {
        console.error("Failed to start upload", error);
        this.showError("Unable to create a session. Please try again.");
      }
    }

    async createSession() {
      const response = await fetch(`${this.config.httpApiUrl}/sessions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`Session creation failed: ${response.status}`);
      }

      return response.json();
    }

    connectWebSocket(sessionId) {
      const wsUrl = `${this.config.wsApiUrl}?sessionId=${encodeURIComponent(sessionId)}`;

      this.state.wsClient = new window.WebSocketClient(wsUrl, {
        onOpen: () => console.log("WebSocket connected"),
        onMessage: (event) => this.handleWebSocketMessage(event),
        onError: (event) => {
          console.error("WebSocket error", event);
          this.showError("WebSocket connection failed. Please try again.");
        },
        onClose: () => console.log("WebSocket closed"),
      });

      this.state.wsClient.connect();
    }

    handleWebSocketMessage(event) {
      let data = null;
      try {
        data = JSON.parse(event.data);
      } catch (error) {
        console.warn("Unexpected WebSocket message", event.data);
        return;
      }

      if (data.action === "UPLOAD_COMPLETED" && data.sessionId === this.state.sessionId) {
        this.showSuccess(data);
      }
    }

    showSuccess(data) {
      this.teardownWebSocket();
      const key = data.uploadKey || "(no key provided)";
      this.elements.successDetails.textContent = `Upload saved as ${key}.`;
      this.showView("success");
    }

    showError(message) {
      this.teardownWebSocket();
      this.elements.errorMessage.textContent = message;
      this.showView("error");
    }

    clearError() {
      this.elements.errorMessage.textContent = "";
    }

    cancelUpload() {
      this.reset();
    }

    reset() {
      this.teardownWebSocket();
      this.state.sessionId = null;
      this.elements.qrCode.innerHTML = "";
      this.elements.sessionId.textContent = "";
      this.elements.uploadUrl.textContent = "";
      this.displayRandomMessage();
      this.showView("initial");
    }

    teardownWebSocket() {
      if (this.state.wsClient) {
        this.state.wsClient.close();
        this.state.wsClient = null;
      }
    }
  }

  window.addEventListener("DOMContentLoaded", () => {
    const app = new QRUploadApp();
    app.init();
  });
})();
