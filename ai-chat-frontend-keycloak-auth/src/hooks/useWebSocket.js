import { useState, useRef, useEffect } from 'react';

const useWebSocket = (clientId) => {
  const [socket, setSocket] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState([]);
  const [connectionError, setConnectionError] = useState(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const connect = () => {
    try {
      const wsUrl = `ws://localhost:8081/ai-agent/ws/${clientId}`;
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setConnectionError(null);
        reconnectAttempts.current = 0;
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        setMessages(prev => [...prev, {
          id: Date.now() + Math.random(),
          role: 'assistant',
          content: data.message || data,
          timestamp: new Date()
        }]);
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
        setSocket(null);

        // Attempt to reconnect
        if (reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current++;
          setTimeout(() => {
            console.log(`Reconnection attempt ${reconnectAttempts.current}`);
            connect();
          }, 2000 * reconnectAttempts.current);
        } else {
          setConnectionError('Failed to reconnect after multiple attempts');
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionError('WebSocket connection error');
      };

      setSocket(ws);
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      setConnectionError('Failed to create WebSocket connection');
    }
  };

  const disconnect = () => {
    if (socket) {
      socket.close();
      setSocket(null);
      setIsConnected(false);
    }
  };

  const sendMessage = (message) => {
    if (socket && isConnected) {
      // Add user message to local state immediately
      setMessages(prev => [...prev, {
        id: Date.now() + Math.random(),
        role: 'user',
        content: message,
        timestamp: new Date()
      }]);

      // Send message through WebSocket
      socket.send(JSON.stringify({ message }));
    } else {
      console.error('WebSocket is not connected');
    }
  };

  useEffect(() => {
    if (clientId) {
      connect();
    } else {
      // Ensure any existing socket is closed if clientId becomes null/undefined
      if (socket) {
        socket.close();
      }
    }

    return () => {
      if (socket) {
        socket.close();
      }
    };
  }, [clientId]);

  return {
    isConnected,
    messages,
    sendMessage,
    connect,
    disconnect,
    connectionError
  };
};

export default useWebSocket;