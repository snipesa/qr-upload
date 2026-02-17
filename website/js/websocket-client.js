(() => {
  class WebSocketClient {
    constructor(url, callbacks = {}) {
      this.url = url;
      this.callbacks = callbacks;
      this.socket = null;
    }

    connect() {
      if (this.socket) {
        this.close();
      }

      this.socket = new WebSocket(this.url);
      this.socket.onopen = (event) => this.callbacks.onOpen?.(event);
      this.socket.onmessage = (event) => this.callbacks.onMessage?.(event);
      this.socket.onerror = (event) => this.callbacks.onError?.(event);
      this.socket.onclose = (event) => this.callbacks.onClose?.(event);
    }

    send(data) {
      if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
        return;
      }
      this.socket.send(JSON.stringify(data));
    }

    close() {
      if (this.socket) {
        this.socket.close();
        this.socket = null;
      }
    }
  }

  window.WebSocketClient = WebSocketClient;
})();
