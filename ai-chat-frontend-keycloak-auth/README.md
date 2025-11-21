# AI Chat Frontend

A React-based chat interface that connects to a FastAPI WebSocket endpoint for real-time communication with an AI assistant.

## Features

- Real-time WebSocket communication
- Auto-reconnection on connection loss
- Role-based message styling (user vs assistant)
- Responsive design
- Connection status indicator
- Message timestamps

## Getting Started

### Prerequisites

- Node.js (version 14 or higher)
- npm or yarn

### Installation

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm start
```

The application will open in your browser at `http://localhost:3000`.

### WebSocket Configuration

The application connects to the WebSocket endpoint at:
```
ws://localhost:8081/ai-agent/ws/{client_id}
```

Make sure your FastAPI backend is running on port 8081.

## Usage

1. The app automatically generates a unique client ID and connects to the WebSocket
2. Type your message in the input field at the bottom
3. Press Enter or click the send button to send your message
4. Messages from the assistant will appear in real-time
5. Connection status is displayed in the header

## Components

- `App.js` - Main application component
- `ChatWindow.js` - Message display area
- `Message.js` - Individual message component
- `MessageInput.js` - Message input form
- `useWebSocket.js` - Custom hook for WebSocket management

## Styling

The interface uses a clean, modern design with:
- Blue color scheme for user messages
- Gray color scheme for assistant messages
- Visual connection status indicators
- Responsive layout for different screen sizes

## Building for Production

```bash
npm run build
```

This creates a `build` folder with the production-ready application.