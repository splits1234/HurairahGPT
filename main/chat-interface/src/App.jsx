
import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sidebar } from './components/Sidebar';
import { InputBar } from './components/InputBar';
import { Download, Trash, Settings } from 'lucide-react';
import styles from './App.module.css';

const PERSONALITIES = {
  "default": "Default",
  "funny": "Funny",
  "islamic": "Islamic",
  "coder": "Coder"
};

function App() {
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);
  const [sessions, setSessions] = useState({});
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [history, setHistory] = useState([]);
  const [personality, setPersonality] = useState('default');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true); // Mobile handling eventually

  // Load initial data
  useEffect(() => {
    fetch('/api/init')
      .then(res => {
        if (res.status === 401) window.location.href = '/login';
        return res.json();
      })
      .then(data => {
        setUser(data.user);
        setSessions(data.sessions);
        setActiveSessionId(data.active_session_id);
        setHistory(data.history);
        setPersonality(data.user.personality || 'default');
        setLoading(false);

        // Sync API theme to local theme if different
        if (data.user.theme) {
          document.documentElement.setAttribute('data-theme', data.user.theme);
        }
      })
      .catch(err => console.error("Init failed", err));
  }, []);

  // Actions
  const handleSendMessage = async (text) => {
    // Optimistic UI update
    const tempMsg = { sender: 'user', content: text, time: new Date().toISOString() };
    setHistory(prev => [...prev, tempMsg]);

    // Check if this is the VERY FIRST message of the session
    const currentSession = sessions[activeSessionId];
    const isFirstMessage = (!currentSession.history || currentSession.history.length === 0) && history.length === 0;

    try {
      const response = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, stream: false }) // Streaming TODO later if needed, keep simple for now
      });
      const data = await response.json();

      const botMsg = { sender: 'bot', content: data.response, time: new Date().toISOString() };
      setHistory(prev => [...prev, botMsg]);

      // If it WAS the first message, generate title NOW, using the text we just sent
      if (isFirstMessage) {
        // Use tempMsg in array because state update hasn't flushed to 'history' variable yet in this closure probably
        // Actually safer to pass just the message content or a constructed array
        generateTitle(activeSessionId, [tempMsg]);
      }

    } catch (error) {
      console.error("Chat error", error);
      setHistory(prev => [...prev, { sender: 'bot', content: "Error: Could not reach backend.", error: true }]);
    }
  };

  const generateTitle = async (sessionId, currentHistory) => {
    try {
      // console.log("Generating title for", sessionId);
      const res = await fetch('/api/generate_title', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ history: currentHistory })
      });
      const data = await res.json();
      if (data.title) {
        handleRenameSession(sessionId, data.title);
      }
    } catch (e) {
      console.error("Title gen error", e);
    }
  };

  const handleSwitchSession = async (sessionId) => {
    try {
      const res = await fetch('/sessions/switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId })
      });
      const data = await res.json();
      if (data.success) {
        setActiveSessionId(sessionId);
        setHistory(data.history);
      }
    } catch (e) { console.error(e); }
  };

  const handleNewChat = async () => {
    try {
      const res = await fetch('/sessions/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      const data = await res.json();
      if (data.success) {
        setSessions(data.sessions);
        setActiveSessionId(data.session_id);
        setHistory([]);
      }
    } catch (e) { console.error(e); }
  };

  const handleDeleteSession = async (sessionId) => {
    try {
      const res = await fetch('/sessions/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId })
      });
      const data = await res.json();
      if (data.success) {
        setSessions(data.sessions);
        setActiveSessionId(data.active_session);
        setHistory(data.history);
      } else {
        alert(data.error);
      }
    } catch (e) { console.error(e); }
  };

  const handleRenameSession = async (sessionId, newName) => {
    try {
      const res = await fetch('/sessions/rename', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, name: newName })
      });
      const data = await res.json();
      if (data.sessions) { // API was fixed to return sessions 
        setSessions(data.sessions);
      }
    } catch (e) { console.error(e); }
  }

  const handleClearChat = async () => {
    if (!window.confirm("Clear this chat history?")) return;
    handleSendMessage("__CLEAR__");
    // UI update optimization
    setHistory([]);
  };

  const handleExportChat = () => {
    const text = history.map(m => `${m.sender.toUpperCase()}: ${m.content} `).join('\n\n');
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chat -export -${new Date().toISOString()}.txt`;
    a.click();
  };

  const handlePersonalityChange = async (e) => {
    const p = e.target.value;
    setPersonality(p);
    await fetch('/personality', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ personality: p })
    });
  };

  if (loading) return <div className={styles.loading}>Loading...</div>; // Could be a nice spinner

  return (
    <div className={styles.appContainer}>
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSwitchSession={handleSwitchSession}
        onNewChat={handleNewChat}
        onDeleteSession={handleDeleteSession}
      />

      <main className={styles.mainCanvas}>
        {/* Top Toolbar for Personality, Export, Clear */}
        <div className={styles.topToolbar}>
          <select value={personality} onChange={handlePersonalityChange} className={styles.personalitySelect}>
            {Object.entries(PERSONALITIES).map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>

          <button onClick={handleExportChat} title="Export Chat" className={styles.iconBtn}>
            <Download size={18} />
          </button>
          <button onClick={handleClearChat} title="Clear Chat" className={styles.iconBtn}>
            <Trash size={18} />
          </button>
        </div>

        <div className={styles.contentWrapper} style={{ justifyContent: history.length > 0 ? 'flex-end' : 'center' }}>

          {history.length === 0 && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={styles.logoContainer}
            >
              <h1 className={styles.logo}>HurairahGPT</h1>
            </motion.div>
          )}

          {history.length > 0 && (
            <div className={styles.chatHistory}>
              {history.map((msg, idx) => (
                <div key={idx} className={`${styles.messageRow} ${msg.sender === 'user' ? styles.userRow : styles.botRow} `}>
                  <div className={styles.messageBubble}>
                    {msg.content} {/* TODO: Markdown support */}
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className={styles.inputContainer}>
            <InputBar onSend={handleSendMessage} />
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
