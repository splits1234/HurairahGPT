/**
 * HurairahGPT - Main Chat Application Component
 * =============================================
 * 
 * This is the primary application component for the HurairahGPT chat interface.
 * It manages the overall application state including user sessions, chat history,
 * theme preferences, and AI personality settings.
 * 
 * Features:
 * - AI assistant Real-time chat with
 * - Multiple chat sessions management
 * - Session switching, creation, and deletion
 * - Theme toggle (dark/light mode)
 * - AI personality selection
 * - Chat export functionality
 * 
 * @version 1.0.0
 * @author Hurairah (Solo Developer)
 * @email hurairahgpt.devteam@gmail.com
 * @website talktohurairah.com
 */

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sidebar } from './components/Sidebar';
import { InputBar } from './components/InputBar';
import { Download, Trash, Settings } from 'lucide-react';
import styles from './App.module.css';

/**
 * AI Personality Configuration
 * 
 * Defines the available AI personalities that users can choose from.
 * Each personality has a distinct communication style and expertise.
 */
const PERSONALITIES = {
  "default": "Default",
  "funny": "Funny",
  "islamic": "Islamic",
  "coder": "Coder"
};

/**
 * Application State Interfaces
 * @typedef {Object} UserState
 * @property {string|null} email - User's email address
 * @property {string} tier - User's subscription tier
 * @property {string} theme - Current theme (dark/light)
 * @property {string} personality - Selected AI personality
 */

/**
 * Session Interface
 * @typedef {Object} Session
 * @property {string} id - Unique session identifier
 * @property {string} name - Session display name
 * @property {Array} history - Array of chat messages
 * @property {string} created - Creation timestamp
 */

/**
 * Message Interface
 * @typedef {Object} Message
 * @property {string} sender - Message sender ('user' or 'bot')
 * @property {string} content - Message content
 * @property {string} time - Timestamp
 * @property {boolean} [error] - Whether message is an error
 */

/**
 * Main Application Component
 * 
 * @component
 * @returns {JSX.Element} The rendered application component
 */
function App() {
  // Application state management
  const [isLoading, setIsLoading] = useState(true);
  const [user, setUser] = useState(null);
  const [sessions, setSessions] = useState({});
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);
  const [personality, setPersonality] = useState('default');
  const [isSidebarVisible, setIsSidebarVisible] = useState(true);

  /**
   * Initialize application by fetching user data from server
   * 
   * @effect
   * @returns {Promise<void>}
   */
  useEffect(() => {
    /**
     * Fetch initial application data from the server
     * 
     * This function retrieves:
     * - User profile information
     * - All chat sessions
     * - Active session data
     * - Theme preferences
     */
    const fetchInitialData = async () => {
      try {
        const response = await fetch('/api/init');
        if (response.status === 401) {
          // Redirect to login if unauthorized
          window.location.href = '/login';
          return;
        }
        
        const data = await response.json();
        
        // Update application state with fetched data
        setUser(data.user);
        setSessions(data.sessions);
        setActiveSessionId(data.active_session_id);
        setChatHistory(data.history);
        setPersonality(data.user.personality || 'default');
        setIsLoading(false);

        // Apply saved theme to document
        if (data.user.theme) {
          document.documentElement.setAttribute('data-theme', data.user.theme);
        }
      } catch (error) {
        console.error("Failed to initialize application:", error);
        setIsLoading(false);
      }
    };

    fetchInitialData();
  }, []);

  /**
   * Send a message to the AI and receive a response
   * 
   * @param {string} messageText - The user's message content
   * @returns {Promise<void>}
   */
  const handleSendMessage = useCallback(async (messageText) => {
    // Optimistic UI update - show user message immediately
    const temporaryMessage = { 
      sender: 'user', 
      content: messageText, 
      time: new Date().toISOString() 
    };
    setChatHistory(prev => [...prev, temporaryMessage]);

    // Check if this is the first message of a new session
    const currentSession = sessions[activeSessionId];
    const isFirstMessage = (
      (!currentSession?.history || currentSession.history.length === 0) && 
      chatHistory.length === 0
    );

    try {
      const response = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message: messageText, 
          stream: false 
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      // Add AI response to chat
      const botMessage = { 
        sender: 'bot', 
        content: data.response, 
        time: new Date().toISOString() 
      };
      setChatHistory(prev => [...prev, botMessage]);

      // Generate title for first message in session
      if (isFirstMessage) {
        generateSessionTitle(activeSessionId, [temporaryMessage]);
      }

    } catch (error) {
      console.error("Chat error:", error);
      // Show error message in chat
      setChatHistory(prev => [...prev, { 
        sender: 'bot', 
        content: "Error: Could not reach the server. Please check your connection and try again.", 
        error: true 
      }]);
    }
  }, [sessions, activeSessionId, chatHistory]);

  /**
   * Generate a title for a chat session using AI
   * 
   * @param {string} sessionId - The session to generate title for
   * @param {Message[]} currentHistory - Chat history for context
   */
  const generateSessionTitle = useCallback(async (sessionId, currentHistory) => {
    try {
      const response = await fetch('/api/generate_title', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ history: currentHistory })
      });

      const data = await response.json();
      if (data.title) {
        renameSession(sessionId, data.title);
      }
    } catch (error) {
      console.error("Title generation error:", error);
    }
  }, []);

  /**
   * Switch to a different chat session
   * 
   * @param {string} sessionId - The session to switch to
   */
  const handleSwitchSession = useCallback(async (sessionId) => {
    try {
      const response = await fetch('/sessions/switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId })
      });

      const data = await response.json();
      if (data.success) {
        setActiveSessionId(sessionId);
        setChatHistory(data.history);
      }
    } catch (error) {
      console.error("Session switch error:", error);
    }
  }, []);

  /**
   * Create a new chat session
   */
  const handleCreateNewChat = useCallback(async () => {
    try {
      const response = await fetch('/sessions/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });

      const data = await response.json();
      if (data.success) {
        setSessions(data.sessions);
        setActiveSessionId(data.session_id);
        setChatHistory([]);
      }
    } catch (error) {
      console.error("Create chat error:", error);
    }
  }, []);

  /**
   * Delete a chat session
   * 
   * @param {string} sessionId - The session to delete
   */
  const handleDeleteSession = useCallback(async (sessionId) => {
    try {
      const response = await fetch('/sessions/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId })
      });

      const data = await response.json();
      if (data.success) {
        setSessions(data.sessions);
        setActiveSessionId(data.active_session);
        setChatHistory(data.history);
      } else {
        alert(data.error);
      }
    } catch (error) {
      console.error("Delete session error:", error);
    }
  }, []);

  /**
   * Rename a chat session
   * 
   * @param {string} sessionId - The session to rename
   * @param {string} newName - The new session name
   */
  const renameSession = useCallback(async (sessionId, newName) => {
    try {
      const response = await fetch('/sessions/rename', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, name: newName })
      });

      const data = await response.json();
      if (data.sessions) {
        setSessions(data.sessions);
      }
    } catch (error) {
      console.error("Rename session error:", error);
    }
  }, []);

  /**
   * Clear all messages from the current chat
   */
  const handleClearChat = useCallback(async () => {
    if (!window.confirm("Are you sure you want to clear this chat history? This action cannot be undone.")) {
      return;
    }
    
    // Send clear command to server
    await handleSendMessage("__CLEAR__");
    
    // Update UI immediately
    setChatHistory([]);
  }, [handleSendMessage]);

  /**
   * Export chat history as a text file
   */
  const handleExportChat = useCallback(() => {
    const chatText = chatHistory
      .map(message => `${message.sender.toUpperCase()}: ${message.content}`)
      .join('\n\n');
    
    const blob = new Blob([chatText], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `hurairahgpt-chat-${new Date().toISOString().slice(0, 10)}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  }, [chatHistory]);

  /**
   * Change the AI personality
   * 
   * @param {Event} event - The select change event
   */
  const handlePersonalityChange = useCallback(async (event) => {
    const newPersonality = event.target.value;
    setPersonality(newPersonality);
    
    try {
      await fetch('/personality', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ personality: newPersonality })
      });
    } catch (error) {
      console.error("Personality change error:", error);
    }
  }, []);

  // Show loading state
  if (isLoading) {
    return (
      <div className={styles.loadingContainer}>
        <motion.div 
          className={styles.loadingSpinner}
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
        />
        <p className={styles.loadingText}>Loading HurairahGPT...</p>
      </div>
    );
  }

  return (
    <div className={styles.appContainer}>
      {/* Sidebar Component - Session Management */}
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSwitchSession={handleSwitchSession}
        onNewChat={handleCreateNewChat}
        onDeleteSession={handleDeleteSession}
      />

      {/* Main Chat Area */}
      <main className={styles.mainCanvas}>
        {/* Top Toolbar - Personality, Export, Clear */}
        <div className={styles.topToolbar}>
          <select 
            value={personality} 
            onChange={handlePersonalityChange} 
            className={styles.personalitySelect}
            aria-label="Select AI Personality"
          >
            {Object.entries(PERSONALITIES).map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>

          <button 
            onClick={handleExportChat} 
            title="Export Chat" 
            className={styles.iconButton}
            aria-label="Export chat as text file"
          >
            <Download size={18} />
          </button>
          
          <button 
            onClick={handleClearChat} 
            title="Clear Chat" 
            className={styles.iconButton}
            aria-label="Clear chat history"
          >
            <Trash size={18} />
          </button>
        </div>

        {/* Chat Content Area */}
        <div 
          className={styles.contentWrapper}
          style={{ 
            justifyContent: chatHistory.length > 0 ? 'flex-end' : 'center' 
          }}
        >
          {/* Welcome Logo - Shown when no messages */}
          <AnimatePresence>
            {chatHistory.length === 0 && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className={styles.logoContainer}
              >
                <h1 className={styles.logo}>HurairahGPT</h1>
                <p className={styles.tagline}>Your AI Assistant</p>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Chat Messages - Shown when messages exist */}
          {chatHistory.length > 0 && (
            <div className={styles.chatHistory}>
              <AnimatePresence>
                {chatHistory.map((message, index) => (
                  <motion.div
                    key={index}
                    className={`${styles.messageRow} ${
                      message.sender === 'user' ? styles.userRow : styles.botRow
                    }`}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3 }}
                  >
                    <div className={`${styles.messageBubble} ${message.error ? styles.errorBubble : ''}`}>
                      {message.content}
                    </div>
                    <span className={styles.messageTime}>
                      {new Date(message.time).toLocaleTimeString([], { 
                        hour: '2-digit', 
                        minute: '2-digit' 
                      })}
                    </span>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          )}

          {/* Input Bar */}
          <div className={styles.inputContainer}>
            <InputBar onSend={handleSendMessage} />
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
