import React from 'react';
import './Message.css';

const Message = ({ message, role }) => {
  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Heuristic: detect ASCII/Markdown tables, including ones without leading/trailing pipes.
  const isAsciiTable = (text) => {
    if (typeof text !== 'string') return false;
    const lines = text.split('\n');
    // Lines that contain column separators
    const pipeLines = lines.filter(l => l.includes('|'));
    // Border/separator rows like "-----+------" or "|-----|"
    const hasBorder = lines.some(l => /^[\-+|\s]+$/.test(l.trim()));
    // Consider it a table if we see at least two lines with pipes (header+row)
    // or a classic border row
    return pipeLines.length >= 2 || hasBorder;
  };

  return (
    <div className={`message ${role}`}>
      <div className="message-content">
        <div className="message-header">
          <span className="message-role">{role === 'user' ? 'You' : 'Assistant'}</span>
          <span className="message-time">{formatTime(message.timestamp)}</span>
        </div>
        {isAsciiTable(message.content) ? (
          <pre className="message-text pre">{message.content}</pre>
        ) : (
          <div className="message-text">{message.content}</div>
        )}
      </div>
    </div>
  );
};

export default Message;