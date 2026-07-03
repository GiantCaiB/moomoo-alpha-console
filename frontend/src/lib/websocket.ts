const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8020/api/v1/ws";

type EventHandler = (event: { type: string; data: unknown; timestamp: number }) => void;

class WebSocketClient {
  private ws: WebSocket | null = null;
  private handlers = new Map<string, EventHandler[]>();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    this.ws = new WebSocket(WS_URL);

    this.ws.onopen = () => {
      console.log("[WS] Connected");
    };

    this.ws.onmessage = (msg) => {
      try {
        const event = JSON.parse(msg.data);
        const typeHandlers = this.handlers.get(event.type) || [];
        typeHandlers.forEach((h) => h(event));
        const allHandlers = this.handlers.get("*") || [];
        allHandlers.forEach((h) => h(event));
      } catch {
        console.error("[WS] Parse error");
      }
    };

    this.ws.onclose = () => {
      console.log("[WS] Disconnected, reconnecting...");
      this.reconnectTimer = setTimeout(() => this.connect(), 3000);
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  disconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.ws?.close();
    this.ws = null;
  }

  on(type: string, handler: EventHandler) {
    if (!this.handlers.has(type)) this.handlers.set(type, []);
    this.handlers.get(type)!.push(handler);
  }

  off(type: string, handler: EventHandler) {
    const hs = this.handlers.get(type);
    if (hs) this.handlers.set(type, hs.filter((h) => h !== handler));
  }
}

export const wsClient = new WebSocketClient();
