type MessageHandler = (data: unknown) => void;

let socket: WebSocket | null = null;
let messageHandler: MessageHandler | null = null;

export function connect(wsUrl: string, onMessage: MessageHandler): void {
  if (socket) {
    socket.close();
  }

  messageHandler = onMessage;
  socket = new WebSocket(wsUrl);

  socket.onmessage = (event) => {
    let data: unknown = event.data;
    if (typeof event.data === "string") {
      try {
        data = JSON.parse(event.data);
      } catch {
        data = event.data;
      }
    }

    messageHandler?.(data);
  };
}

export function sendMessage(text: string): void {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    return;
  }

  socket.send(JSON.stringify({ type: "user_message", text }));
}

export function disconnect(): void {
  if (socket) {
    socket.close();
    socket = null;
  }
  messageHandler = null;
}
