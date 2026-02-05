/**
 * HurairahGPT - Input Bar Component
 * ==================================
 * 
 * A styled input component for the HurairahGPT chat interface.
 * Provides a modern, accessible text input with submit functionality.
 * 
 * Features:
 * - Animated input field with focus states
 * - Keyboard support (Enter to submit)
 * - File attachment button (UI only)
 * - New chat button
 * - Smooth transitions and micro-interactions
 * 
 * @component
 * @version 1.0.0
 * @author Hurairah
 */

import { useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { Paperclip, ArrowUp, Plus } from 'lucide-react';
import styles from './InputBar.module.css';

/**
 * InputBar Component Props
 * @typedef {Object} InputBarProps
 * @property {Function} onSend - Callback function when message is sent
 * @property {Function} [onNewChat] - Callback function for new chat button
 */

/**
 * InputBar - Chat Message Input Component
 * 
 * @param {InputBarProps} props - Component properties
 * @returns {JSX.Element} Rendered input bar component
 */
export function InputBar({ onSend, onNewChat }) {
  const [inputText, setInputText] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const fileInputRef = useRef(null);

  /**
   * Handle form submission
   * 
   * @param {Event} event - Form submit event
   */
  const handleSubmit = (event) => {
    event.preventDefault();
    
    // Only send if text is not empty
    if (inputText.trim()) {
      onSend(inputText.trim());
      setInputText('');
    }
  };

  /**
   * Handle keyboard input
   * Supports Enter to submit, Shift+Enter for new line (disabled)
   * 
   * @param {KeyboardEvent} event - Keyboard event
   */
  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSubmit(event);
    }
  };

  /**
   * Handle new chat button click
   */
  const handleNewChat = () => {
    if (onNewChat) {
      onNewChat();
    }
  };

  return (
    <div className={styles.container}>
      {/* Animated Input Pill Container */}
      <motion.div
        className={styles.inputWrapper}
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.2 }}
      >
        {/* Attachment Button */}
        <button
          className={styles.attachButton}
          aria-label="Attach file"
          type="button"
        >
          <Paperclip size={20} />
        </button>

        {/* Main Text Input */}
        <input
          type="text"
          placeholder="Send a message to HurairahGPT..."
          className={styles.textInput}
          value={inputText}
          onChange={(event) => setInputText(event.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          aria-label="Message input"
          disabled={false}
        />

        {/* Right Action Buttons */}
        <div className={styles.rightActions}>
          {/* New Chat Button */}
          <button
            className={styles.newChatButton}
            onClick={handleNewChat}
            aria-label="New chat"
            type="button"
          >
            <Plus size={20} />
          </button>

          {/* Send Button */}
          <motion.button
            className={styles.sendButton}
            onClick={handleSubmit}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            disabled={!inputText.trim()}
            aria-label="Send message"
            type="button"
          >
            <ArrowUp size={20} />
          </motion.button>
        </div>
      </motion.div>

      {/* Helper Text */}
      <motion.p
        className={styles.helperText}
        animate={{ opacity: isFocused ? 1 : 0.5 }}
      >
        Press Enter to send, Shift+Enter for new line
      </motion.p>
    </div>
  );
}

export default InputBar;
