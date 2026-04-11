/**
 * FlowMind AI — AI Chat Component
 * WCAG 2.1 AA: role="log" on message feed, aria-live="assertive" for new AI messages,
 * labelled input/button, aria-busy on typing state.
 */

import React, { useState, useRef, useEffect } from 'react';
import { sendChatMessage } from '../../services/api';
import './AIChat.css';

const QUICK_ACTIONS = [
  { icon: '🍔', text: 'Where should I get food with the shortest wait?' },
  { icon: '🚻', text: 'Which restroom has the shortest line?' },
  { icon: '👥', text: 'Which area is least crowded right now?' },
  { icon: '🚪', text: "What's the fastest exit right now?" },
  { icon: '⌚', text: 'Should I leave now or wait?' },
  { icon: '🗺️', text: 'How do I get to the North Stand?' },
];

const LANGUAGES = [
  { code: 'en', label: '🇬🇧 English' },
  { code: 'hi', label: '🇮🇳 Hindi' },
  { code: 'es', label: '🇪🇸 Spanish' },
  { code: 'fr', label: '🇫🇷 French' },
  { code: 'de', label: '🇩🇪 German' },
  { code: 'pt', label: '🇧🇷 Portuguese' },
  { code: 'ar', label: '🇸🇦 Arabic' },
  { code: 'ja', label: '🇯🇵 Japanese' },
  { code: 'zh', label: '🇨🇳 Chinese' },
  { code: 'ko', label: '🇰🇷 Korean' },
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
    } catch {
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'assistant',
        content: 'Sorry, I\'m having trouble connecting to the stadium systems. Please try again in a moment.',
        timestamp: new Date().toISOString(),
      }]);
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

  const formatTime = (ts) => {
    if (!ts) return '';
    return new Date(ts).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="chat-container">
      {/* Main Chat */}
      <section className="glass-card chat-main" aria-label="AI chat conversation">
        {/* Message feed */}
        <div
          className="chat-messages"
          role="log"
          aria-live="polite"
          aria-atomic="false"
          aria-relevant="additions"
          aria-label="Conversation messages"
          tabIndex={0}
        >
          {messages.length === 0 && (
            <div className="chat-welcome" aria-live="polite">
              <span className="chat-welcome-icon" aria-hidden="true">🤖</span>
              <h2>FlowMind AI Assistant</h2>
              <p>
                Ask me anything about the stadium — crowd conditions, wait times,
                best routes, food options, or exit strategies. I have real-time data
                and I&apos;ll give you specific, actionable advice.
              </p>
            </div>
          )}

          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`chat-message ${msg.role}`}
              aria-label={`${msg.role === 'user' ? 'You' : 'FlowMind AI'} at ${formatTime(msg.timestamp)}: ${msg.content}`}
            >
              <div className="chat-avatar" aria-hidden="true">
                {msg.role === 'user' ? 'U' : 'AI'}
              </div>
              <div>
                <div className="chat-bubble">
                  {msg.content}
                  {msg.action && (
                    <div className="chat-action" aria-label={`Recommended action: ${msg.action}`}>
                      {msg.action}
                    </div>
                  )}
                  {msg.zones && msg.zones.length > 0 && (
                    <div className="chat-zones" aria-label={`Related zones: ${msg.zones.join(', ')}`}>
                      {msg.zones.map((zone, i) => (
                        <span key={i} className="chat-zone-tag">{zone}</span>
                      ))}
                    </div>
                  )}
                </div>
                <div className="chat-timestamp" aria-hidden="true">
                  <time dateTime={msg.timestamp}>{formatTime(msg.timestamp)}</time>
                </div>
              </div>
            </div>
          ))}

          {isTyping && (
            <div
              className="chat-message assistant"
              role="status"
              aria-label="FlowMind AI is typing a response"
              aria-live="assertive"
            >
              <div className="chat-avatar" aria-hidden="true">AI</div>
              <div className="chat-bubble" aria-hidden="true">
                <div className="typing-indicator">
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} tabIndex={-1} />
        </div>

        {/* Input area */}
        <div className="chat-input-area" role="group" aria-label="Send a message">
          <label htmlFor="chat-input" className="visually-hidden">
            Message FlowMind AI
          </label>
          <textarea
            id="chat-input"
            ref={inputRef}
            className="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about crowds, wait times, exits..."
            rows={1}
            disabled={isTyping}
            aria-disabled={isTyping}
            aria-describedby="chat-hint"
          />
          <span id="chat-hint" className="visually-hidden">
            Press Enter to send, Shift+Enter for a new line
          </span>
          <button
            className="chat-send-btn"
            onClick={() => handleSend()}
            disabled={!input.trim() || isTyping}
            aria-label="Send message"
            aria-busy={isTyping}
          >
            Send
          </button>
        </div>
      </section>

      {/* Sidebar Quick Actions */}
      <aside className="chat-sidebar" aria-label="Chat options">
        {/* Language Selector */}
        <div className="glass-card quick-actions-card">
          <h2>🌐 Language</h2>
          <label htmlFor="language-select" className="visually-hidden">
            Select response language
          </label>
          <select
            id="language-select"
            className="chat-lang-select"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            aria-label="Select response language"
          >
            {LANGUAGES.map((lang) => (
              <option key={lang.code} value={lang.code}>{lang.label}</option>
            ))}
          </select>
        </div>

        <div className="glass-card quick-actions-card">
          <h2>Quick Questions</h2>
          {QUICK_ACTIONS.map((action, i) => (
            <button
              key={i}
              className="quick-action-btn"
              onClick={() => handleSend(action.text)}
              disabled={isTyping}
              aria-disabled={isTyping}
              aria-label={action.text}
            >
              <span className="qa-icon" aria-hidden="true">{action.icon}</span>
              {action.text}
            </button>
          ))}
        </div>
      </aside>
    </div>
  );
}
