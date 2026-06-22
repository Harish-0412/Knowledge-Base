import React, { useState, useRef, useEffect } from "react";
import { API_BASE } from "../lib/api";

function Chatbot({ user }) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { role: "assistant", content: "Hi! I'm your Compatibility Assistant. How can I help you today?" }
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Get user's first letter for avatar
  const getUserInitial = () => {
    if (!user) return "U";
    if (user.displayName) {
      return user.displayName.charAt(0).toUpperCase();
    }
    if (user.email) {
      return user.email.charAt(0).toUpperCase();
    }
    return "U";
  };

  // Frontend guardrails
  const isAllowedQuestion = (question) => {
    const lowerQuestion = question.toLowerCase();
    
    // Blocked categories (medical/financial)
    const blockedKeywords = [
      "medical", "health", "doctor", "hospital", "medicine", "treatment",
      "financial", "money", "bank", "loan", "credit", "investment", "stock",
      "insurance", "tax", "finance"
    ];
    
    // Check if any blocked keyword is present
    const isBlocked = blockedKeywords.some(keyword => lowerQuestion.includes(keyword));
    if (isBlocked) return false;
    
    // Allowed categories: greetings, computer/IT, CompatIQ project
    const allowedKeywords = [
      // Greetings
      "hello", "hi", "hey", "how are you", "good morning", "good afternoon",
      "good evening", "good day", "nice to meet you", "what's up",
      // Computer/IT
      "computer", "it", "bios", "cpu", "ram", "motherboard", "hard drive",
      "ssd", "gpu", "operating system", "os", "windows", "linux", "mac",
      "software", "hardware", "network", "server", "internet", "wifi",
      "bluetooth", "usb", "driver", "update", "install", "download",
      "error", "bug", "fix", "troubleshoot", "laptop", "desktop",
      "keyboard", "mouse", "monitor", "printer", "scanner", "router",
      "modem", "firewall", "antivirus", "malware", "virus", "backup",
      // CompatIQ project
      "compatibility", "compat", "document", "upload", "rule", "candidate",
      "inventory", "device", "compliance", "analysis", "pipeline", "cisco",
      "knowledge base", "knowledgebase", "guardrail", "audit", "tier", "extract",
      "normalize", "review", "approve", "reject", "cve", "security", "release notes",
      "compatiq", "dashboard", "landing", "workspace", "profile", "chunk", "api"
    ];
    
    return allowedKeywords.some(keyword => lowerQuestion.includes(keyword));
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    // Check guardrails first
    if (!isAllowedQuestion(input)) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "I can only answer greetings, CompatIQ project questions, and computer/IT related questions. I cannot answer medical or financial questions."
        }
      ]);
      setIsLoading(false);
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/api/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: input })
      });

      let answer;
      if (response.ok) {
        const data = await response.json();
        answer = data.answer;
      } else {
        answer = "I'm sorry, I couldn't find an answer to that question. Please try again later.";
      }

      setMessages((prev) => [...prev, { role: "assistant", content: answer }]);
    } catch (error) {
      setMessages((prev) => [...prev, { role: "assistant", content: "An error occurred. Please try again." }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="chatbot-container">
      {!isOpen ? (
        <button
          className="wave-menu"
          onClick={() => setIsOpen(true)}
          aria-label="Open Chatbot"
        >
          <li></li>
          <li></li>
          <li></li>
          <li></li>
          <li></li>
          <li></li>
          <li></li>
          <li></li>
          <li></li>
          <li></li>
        </button>
      ) : (
        <div className="chatbot-window">
          <div className="chatbot-header">
            <span className="chatbot-title">Compatibility Assistant</span>
            <button className="chatbot-close" onClick={() => setIsOpen(false)} aria-label="Close Chatbot">
              ×
            </button>
          </div>
          <div className="chatbot-messages">
            {messages.map((msg, idx) => (
              <div key={idx} className={`chatbot-message ${msg.role}`}>
                <div className="chatbot-avatar">
                  {msg.role === "assistant" ? "AI" : getUserInitial()}
                </div>
                <div className="chatbot-content">{msg.content}</div>
              </div>
            ))}
            {isLoading && (
              <div className="chatbot-message assistant">
                <div className="chatbot-avatar">AI</div>
                <div className="chatbot-content typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
          <form className="chatbot-input-form" onSubmit={handleSend}>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about greetings, CompatIQ, or computer/IT..."
              disabled={isLoading}
            />
            <button type="submit" disabled={isLoading}>
              Send
            </button>
          </form>
        </div>
      )}
      <style jsx>{`
        .chatbot-container {
          position: fixed;
          bottom: 24px;
          right: 24px;
          z-index: 9999;
        }

        .wave-menu {
          border: 4px solid #545FE5;
          border-radius: 50px;
          width: 200px;
          height: 45px;
          display: flex;
          justify-content: center;
          align-items: center;
          padding: 0;
          margin: 0;
          cursor: pointer;
          transition: ease 0.2s;
          position: relative;
          background: #fff;
        }

        .wave-menu li {
          list-style: none;
          height: 30px;
          width: 4px;
          border-radius: 10px;
          background: #545FE5;
          margin: 0 6px;
          padding: 0;
          animation-name: wave1;
          animation-duration: 0.3s;
          animation-iteration-count: infinite;
          animation-direction: alternate;
          transition: ease 0.2s;
        }

        .wave-menu:hover > li {
          background: #fff;
        }

        .wave-menu:hover {
          background: #545FE5;
        }

        .wave-menu li:nth-child(2) {
          animation-name: wave2;
          animation-delay: 0.2s;
        }

        .wave-menu li:nth-child(3) {
          animation-name: wave3;
          animation-delay: 0.23s;
          animation-duration: 0.4s;
        }

        .wave-menu li:nth-child(4) {
          animation-name: wave4;
          animation-delay: 0.1s;
          animation-duration: 0.3s;
        }

        .wave-menu li:nth-child(5) {
          animation-delay: 0.5s;
        }

        .wave-menu li:nth-child(6) {
          animation-name: wave2;
          animation-duration: 0.5s;
        }

        .wave-menu li:nth-child(8) {
          animation-name: wave4;
          animation-delay: 0.4s;
          animation-duration: 0.25s;
        }

        .wave-menu li:nth-child(9) {
          animation-name: wave3;
          animation-delay: 0.15s;
        }

        @keyframes wave1 {
          from { transform: scaleY(1); }
          to { transform: scaleY(0.5); }
        }

        @keyframes wave2 {
          from { transform: scaleY(0.3); }
          to { transform: scaleY(0.6); }
        }

        @keyframes wave3 {
          from { transform: scaleY(0.6); }
          to { transform: scaleY(0.8); }
        }

        @keyframes wave4 {
          from { transform: scaleY(0.2); }
          to { transform: scaleY(0.5); }
        }

        .chatbot-window {
          width: 380px;
          height: 520px;
          background: white;
          border-radius: 16px;
          box-shadow: 0 10px 40px rgba(0,0,0,0.2);
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }

        .chatbot-header {
          background: linear-gradient(135deg, #545FE5 0%, #4a54d6 100%);
          color: white;
          padding: 16px 20px;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .chatbot-title {
          font-weight: 600;
          font-size: 16px;
        }

        .chatbot-close {
          background: transparent;
          border: none;
          color: white;
          font-size: 28px;
          cursor: pointer;
          line-height: 1;
          padding: 0;
        }

        .chatbot-messages {
          flex: 1;
          padding: 16px;
          overflow-y: auto;
          background: #f7f8fa;
        }

        .chatbot-message {
          display: flex;
          gap: 12px;
          margin-bottom: 16px;
          align-items: flex-start;
        }

        .chatbot-message.user {
          flex-direction: row-reverse;
        }

        .chatbot-avatar {
          width: 36px;
          height: 36px;
          border-radius: 50%;
          background: #545FE5;
          color: white;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 12px;
          font-weight: 600;
          flex-shrink: 0;
        }

        .chatbot-message.user .chatbot-avatar {
          background: #0f172a;
        }

        .chatbot-content {
          max-width: 75%;
          padding: 12px 16px;
          border-radius: 12px;
          background: white;
          box-shadow: 0 1px 2px rgba(0,0,0,0.08);
          font-size: 14px;
          line-height: 1.5;
          color: #000000;
        }

        .chatbot-message.user .chatbot-content {
          background: #545FE5;
          color: white;
        }

        .typing-indicator {
          display: flex;
          gap: 4px;
          padding: 12px 16px;
        }

        .typing-indicator span {
          width: 8px;
          height: 8px;
          background: #545FE5;
          border-radius: 50%;
          animation: typing 1.4s infinite ease-in-out;
        }

        .typing-indicator span:nth-child(1) { animation-delay: 0s; }
        .typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
        .typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

        @keyframes typing {
          0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
          40% { transform: scale(1); opacity: 1; }
        }

        .chatbot-input-form {
          padding: 16px;
          background: white;
          border-top: 1px solid #e5e7eb;
          display: flex;
          gap: 10px;
        }

        .chatbot-input-form input {
          flex: 1;
          padding: 10px 14px;
          border: 1px solid #e5e7eb;
          border-radius: 8px;
          font-size: 14px;
        }

        .chatbot-input-form input:focus {
          outline: none;
          border-color: #545FE5;
        }

        .chatbot-input-form button {
          background: #545FE5;
          color: white;
          border: none;
          padding: 10px 20px;
          border-radius: 8px;
          cursor: pointer;
          font-size: 14px;
          font-weight: 500;
          transition: background 0.2s;
        }

        .chatbot-input-form button:hover:not(:disabled) {
          background: #4a54d6;
        }

        .chatbot-input-form button:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
      `}</style>
    </div>
  );
}

export default Chatbot;
