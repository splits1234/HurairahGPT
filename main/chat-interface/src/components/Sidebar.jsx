/**
 * HurairahGPT - Sidebar Component
 * ===============================
 * 
 * The sidebar component provides navigation and session management features
 * for the HurairahGPT chat application. It displays the user's chat sessions,
 * allows switching between sessions, creating new chats, and deleting sessions.
 * 
 * Features:
 * - Session list with search functionality
 * - Create new chat sessions
 * - Switch between existing sessions
 * - Delete sessions with confirmation
 * - Search through session names
 * - Theme toggle integration
 * - User profile display
 * - Logout functionality
 * 
 * @component
 * @version 1.0.0
 * @author Hurairah
 */

import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, MessageSquare, Plus, Trash2, LogOut } from 'lucide-react';
import styles from './Sidebar.module.css';
import { ThemeToggle } from './ThemeToggle';

/**
 * Sidebar Component Props
 * @typedef {Object} SidebarProps
 * @property {Object} sessions - Dictionary of chat sessions
 * @property {string|null} activeSessionId - Currently active session ID
 * @property {Function} onSwitchSession - Callback when switching sessions
 * @property {Function} onNewChat - Callback when creating new chat
 * @property {Function} onDeleteSession - Callback when deleting session
 */

/**
 * Session Data Interface
 * @typedef {Object} SessionData
 * @property {string} id - Unique session identifier
 * @property {string} name - Display name for session
 * @property {string} created - Creation timestamp
 * @property {Array} history - Chat message history
 */

/**
 * Sidebar - Session Management Component
 * 
 * @param {SidebarProps} props - Component properties
 * @returns {JSX.Element} Rendered sidebar component
 */
export function Sidebar({ 
  sessions, 
  activeSessionId, 
  onSwitchSession, 
  onNewChat, 
  onDeleteSession 
}) {
  // State for search functionality
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearchFocused, setIsSearchFocused] = useState(false);
  const [hoveredSession, setHoveredSession] = useState(null);

  /**
   * Filter and sort sessions based on search query
   * 
   * This useMemo hook ensures efficient filtering and sorting
   * of sessions without causing unnecessary re-renders.
   * 
   * @returns {Array<SessionData>} Filtered and sorted session list
   */
  const filteredSessions = useMemo(() => {
    return Object.entries(sessions || {})
      .map(([id, session]) => ({ id, ...session }))
      .sort((a, b) => new Date(b.created || 0) - new Date(a.created || 0))
      .filter(session => 
        session.name.toLowerCase().includes(searchQuery.toLowerCase())
      );
  }, [sessions, searchQuery]);

  /**
   * Handle session deletion with user confirmation
   * 
   * @param {string} sessionId - ID of session to delete
   */
  const handleDeleteWithConfirmation = (sessionId) => {
    if (window.confirm('Are you sure you want to delete this chat? This action cannot be undone.')) {
      onDeleteSession(sessionId);
    }
  };

  /**
   * Format session name for display
   * Shows uppercase 3-letter code for short names
   * 
   * @param {string} name - Original session name
   * @returns {string} Formatted display name
   */
  const formatSessionName = (name) => {
    if (name.length === 3) {
      return name.toUpperCase();
    }
    return name;
  };

  return (
    <aside className={styles.sidebar} aria-label="Chat sidebar">
      {/* Header Section */}
      <header className={styles.header}>
        <div className={styles.topRow}>
          {/* New Chat Button */}
          <motion.button
            onClick={onNewChat}
            className={styles.newChatButton}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            type="button"
          >
            <Plus size={16} />
            <span>New Chat</span>
          </motion.button>
        </div>

        {/* Search Bar */}
        <div className={`${styles.searchWrapper} ${isSearchFocused ? styles.focused : ''}`}>
          <Search size={16} className={styles.searchIcon} aria-hidden="true" />
          <input
            type="text"
            placeholder="Search conversations..."
            className={styles.searchInput}
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            onFocus={() => setIsSearchFocused(true)}
            onBlur={() => setIsSearchFocused(false)}
            aria-label="Search conversations"
          />
        </div>
      </header>

      {/* Session History Section */}
      <div className={styles.historySection}>
        <div className={styles.historyHeader}>
          <MessageSquare size={14} aria-hidden="true" />
          <span>Conversations</span>
          <span className={styles.sessionCount}>
            ({filteredSessions.length})
          </span>
        </div>

        <div className={styles.historyList} role="list" aria-label="Chat sessions">
          <AnimatePresence mode="popLayout">
            {filteredSessions.map((session) => (
              <motion.div
                key={session.id}
                className={styles.sessionWrapper}
                onMouseEnter={() => setHoveredSession(session.id)}
                onMouseLeave={() => setHoveredSession(null)}
                layout
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20, height: 0 }}
                transition={{ duration: 0.2 }}
                role="listitem"
              >
                <div
                  className={`${styles.historyItem} ${
                    session.id === activeSessionId ? styles.activeSession : ''
                  }`}
                  onClick={() => onSwitchSession(session.id)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      onSwitchSession(session.id);
                    }
                  }}
                  tabIndex={0}
                  role="button"
                  aria-pressed={session.id === activeSessionId}
                  aria-label={`Open conversation: ${session.name}`}
                >
                  <span className={styles.sessionName}>
                    {formatSessionName(session.name)}
                  </span>

                  {/* Delete Button - Shown on Hover */}
                  {hoveredSession === session.id && (
                    <motion.button
                      className={styles.deleteButton}
                      onClick={(event) => {
                        event.stopPropagation();
                        handleDeleteWithConfirmation(session.id);
                      }}
                      onKeyDown={(event) => event.stopPropagation()}
                      whileHover={{ scale: 1.1 }}
                      whileTap={{ scale: 0.9 }}
                      aria-label={`Delete conversation: ${session.name}`}
                      type="button"
                    >
                      <Trash2 size={14} />
                    </motion.button>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Empty State */}
          {filteredSessions.length === 0 && (
            <motion.div
              className={styles.emptyState}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <MessageSquare size={32} className={styles.emptyIcon} />
              <p>No conversations yet</p>
              <p className={styles.emptyHint}>Start a new chat to begin!</p>
            </motion.div>
          )}
        </div>
      </div>

      {/* Footer - User Profile & Actions */}
      <footer className={styles.footer}>
        <div className={styles.userProfile}>
          <div className={styles.userInfo}>
            <div className={styles.avatar}>
              <span>H</span>
            </div>
            <div className={styles.userDetails}>
              <span className={styles.userName}>HurairahGPT</span>
              <span className={styles.userStatus}>Online</span>
            </div>
          </div>
        </div>

        <div className={styles.footerActions}>
          {/* Theme Toggle */}
          <ThemeToggle />

          {/* Logout Button */}
          <motion.button
            className={styles.logoutButton}
            onClick={() => window.location.href = '/logout'}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            title="Log Out"
            aria-label="Log out of your account"
            type="button"
          >
            <LogOut size={18} />
          </motion.button>
        </div>
      </footer>
    </aside>
  );
}

export default Sidebar;
