/**
 * FlowMind AI — AI Chat Component
 * Decision-focused conversational interface with quick actions and context display.
 */

import React, { useState, useRef, useEffect } from 'react';
import { sendChatMessage } from '../../services/api';
import './AIChat.css';

const QUICK_ACTIONS = [
  { icon: '\uD83C\uDF54', text: 'Where should I get food with the shortest wait?' },
  { icon: '\uD83D\uDEBB', text: 'Which restroom has the shortest line?' },
  { icon: '\uD83D\uDC65', text: 'Which area is least crowded right now?' },
  { icon: '\uD83D\uDEAA', text: 'What\'s the fastest exit right now?' },
  { icon: '\u231A', text: 'Should I leave now or wait?' },
  { icon: '\uD83D\uDDFA\uFE0F', text: 'How do I get to the North Stand?' },
];

const LANGUAGES = [
  { code: 'en', label: '\uD83C\uDDEC\uD83C\uDDE7 English' },
  { code: 'hi', label: '\uD83C\uDDEE\uD83C\uDDF3 Hindi' },
  { code: 'es', label: '\uD83C\uDDEA\uD83C\uDDF8 Spanish' },
  { code: 'fr', label: '\uD83C\uDDEB\uD83C\uDDF7 French' },
  { code: 'de', label: '\uD83C\uDDE9\uD83C\uDDEA German' },
  { code: 'pt', label: '\uD83C\uDDE7\uD83C\uDDF7 Portuguese' },
  { code: 'ar', label: '\uD83C\uDDF8\uD83C\uDDE6 Arabic' },
  { code: 'ja', label: '\uD83C\uDDEF\uD83C\uDDF5 Japanese' },
  { code: 'zh', label: '\uD83C\uDDE8\uD83C\uDDF3 Chinese' },
  { code: 'ko', label: '\uD83C\uDDF0\uD83C\uDDF7 Korean' },
];

export default function AIChat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [language, setLanguage] = useState('en');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleSend = async (text) => {
    const messageText = text || input.trim();
    if (!messageText || isTyping) return;

    // Add user message
    const userMsg = {
      id: Date.now(),
      role: 'user',
      content: messageText,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsTyping(true);

    try {
      const response = await sendChatMessage(messageText, null, language);

      const assistantMsg = {
        id: Date.now() + 1,
        role: 'assistant',
        content: response.response,
        action: response.recommended_action,
        zones: response.related_zones || [],
        confidence: response.confidence,
        timestamp: response.timestamp,
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err) {
      const errorMsg = {
        id: Date.now() + 1,
        role: 'assistant',
        content: 'Sorry, I\'m having trouble connecting to the stadium systems. Please try again in a moment.',
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="chat-container">
      {/* Main Chat */}
      <div className="glass-card chat-main">
        <div className="chat-messages">
          {messages.length === 0 && (
            <div className="chat-welcome">
              <span className="chat-welcome-icon">{'\uD83E\uDD16'}</span>
              <h3>FlowMind AI Assistant</h3>
              <p>
                Ask me anything about the stadium — crowd conditions, wait times,
                best routes, food options, or exit strategies. I have real-time data
                and I&apos;ll give you specific, actionable advice.
              </p>
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id} className={`chat-message ${msg.role}`}>
              <div className="chat-avatar">
                {msg.role === 'user' ? 'U' : 'AI'}
              </div>
              <div>
                <div className="chat-bubble">
                  {msg.content}
                  {msg.action && (
                    <div className="chat-action">{msg.action}</div>
                  )}
                  {msg.zones && msg.zones.length > 0 && (
                    <div className="chat-zones">
                      {msg.zones.map((zone, i) => (
                        <span key={i} className="chat-zone-tag">{zone}</span>
                      ))}
                    </div>
                  )}
                </div>
                <div className="chat-timestamp">{formatTime(msg.timestamp)}</div>
              </div>
            </div>
          ))}

          {isTyping && (
            <div className="chat-message assistant">
              <div className="chat-avatar">AI</div>
              <div className="chat-bubble">
                <div className="typing-indicator">
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="chat-input-area">
          <textarea
            ref={inputRef}
            className="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about crowds, wait times, exits..."
            rows={1}
            disabled={isTyping}
          />
          <button
            className="chat-send-btn"
            onClick={() => handleSend()}
            disabled={!input.trim() || isTyping}
          >
            Send
          </button>
        </div>
      </div>

      {/* Sidebar Quick Actions */}
      <div className="chat-sidebar">
        {/* Language Selector */}
        <div className="glass-card quick-actions-card">
          <h3>{"\uD83C\uDF10"} Language</h3>
          <select
            className="chat-lang-select"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
          >
            {LANGUAGES.map((lang) => (
              <option key={lang.code} value={lang.code}>{lang.label}</option>
            ))}
          </select>
        </div>

        <div className="glass-card quick-actions-card">
          <h3>Quick Questions</h3>
          {QUICK_ACTIONS.map((action, i) => (
            <button
              key={i}
              className="quick-action-btn"
              onClick={() => handleSend(action.text)}
              disabled={isTyping}
            >
              <span className="qa-icon">{action.icon}</span>
              {action.text}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
