import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, MessageSquare, Plus, Trash2, LogOut } from 'lucide-react';
import styles from './Sidebar.module.css';
import { ThemeToggle } from './ThemeToggle';

export function Sidebar({ sessions, activeSessionId, onSwitchSession, onNewChat, onDeleteSession }) {
    const [searchQuery, setSearchQuery] = useState('');
    const [isSearchFocused, setIsSearchFocused] = useState(false);
    const [hoveredSession, setHoveredSession] = useState(null);

    // Convert sessions object to array and sort by date (newest first)
    // Filter by search query
    const sessionList = useMemo(() => {
        return Object.entries(sessions || {})
            .map(([id, sess]) => ({ id, ...sess }))
            .sort((a, b) => new Date(b.created || 0) - new Date(a.created || 0))
            .filter(sess => sess.name.toLowerCase().includes(searchQuery.toLowerCase()));
    }, [sessions, searchQuery]);

    return (
        <aside className={styles.sidebar}>
            <header className={styles.header}>
                <div className={styles.topRow} style={{ marginBottom: '10px' }}>
                    <button onClick={onNewChat} className={styles.newChatBtn}>
                        <Plus size={16} /> New Chat
                    </button>
                </div>
                <div className={`${styles.searchWrapper} ${isSearchFocused ? styles.focused : ''}`}>
                    <Search size={16} className={styles.searchIcon} />
                    <input
                        type="text"
                        placeholder="Search"
                        className={styles.searchInput}
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        onFocus={() => setIsSearchFocused(true)}
                        onBlur={() => setIsSearchFocused(false)}
                    />
                </div>
            </header>

            <div className={styles.historySection}>
                <div className={styles.historyHeader}>
                    <MessageSquare size={14} />
                    <span>Chats</span>
                </div>
                <div className={styles.historyList}>
                    <AnimatePresence>
                        {sessionList.map((sess) => (
                            <motion.div
                                key={sess.id}
                                className={styles.sessionWrapper}
                                onMouseEnter={() => setHoveredSession(sess.id)}
                                onMouseLeave={() => setHoveredSession(null)}
                                layout
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -20, height: 0 }}
                                transition={{ duration: 0.2 }}
                            >
                                <div
                                    className={`${styles.historyItem} ${sess.id === activeSessionId ? styles.activeHistory : ''}`}
                                    onClick={() => onSwitchSession(sess.id)}
                                >
                                    <span className={styles.sessionName}>
                                        {sess.name.length === 3 ? sess.name.toUpperCase() : sess.name}
                                    </span>

                                    {hoveredSession === sess.id && (
                                        <button
                                            className={styles.deleteBtn}
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                if (window.confirm('Delete this chat?')) onDeleteSession(sess.id);
                                            }}
                                        >
                                            <Trash2 size={14} />
                                        </button>
                                    )}
                                </div>
                            </motion.div>
                        ))}
                    </AnimatePresence>
                </div>
            </div>

            <footer className={styles.footer}>
                <div className={styles.userProfile}>
                    <div className={styles.userInfo}>
                        <span className={styles.userName}>HurairahGPT</span>
                    </div>
                </div>
                <div className={styles.footerActions}>
                    <button
                        className={styles.logoutBtn}
                        onClick={() => window.location.href = '/logout'}
                        title="Log Out"
                        aria-label="Log Out"
                    >
                        <LogOut size={18} />
                    </button>
                    <ThemeToggle />
                </div>
            </footer>
        </aside>
    );
}
