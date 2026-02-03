/**
 * HurairahGPT - Theme Toggle Component
 * =====================================
 * 
 * A toggle button component that switches between light and dark themes.
 * Features smooth animated transitions between theme states.
 * 
 * Features:
 * - Animated sun/moon icons
 * - Smooth rotation transitions
 * - Persistent theme preference (localStorage)
 * - Accessibility support
 * 
 * @component
 * @version 1.0.0
 * @author Hurairah
 */

import { motion } from 'framer-motion';
import { Sun, Moon } from 'lucide-react';
import { useTheme } from '../hooks/useTheme';
import styles from './ThemeToggle.module.css';

/**
 * ThemeToggle - Theme Switching Button Component
 * 
 * A visually appealing toggle button that displays either a sun or moon
 * icon depending on the current theme. Clicking toggles between themes.
 * 
 * @returns {JSX.Element} Rendered theme toggle button
 */
export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <motion.button
      className={styles.toggleButton}
      onClick={toggleTheme}
      whileTap={{ scale: 0.95 }}
      whileHover={{ scale: 1.05 }}
      aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
      title={`Current theme: ${theme}. Click to switch.`}
      type="button"
    >
      {/* Moon Icon - Visible in Dark Mode */}
      <motion.div
        className={styles.moonIcon}
        initial={false}
        animate={{
          rotate: theme === 'dark' ? 0 : 180,
          opacity: theme === 'dark' ? 1 : 0
        }}
        transition={{ duration: 0.3 }}
      >
        <Moon size={20} />
      </motion.div>

      {/* Sun Icon - Visible in Light Mode */}
      <motion.div
        className={styles.sunIcon}
        initial={false}
        animate={{
          rotate: theme === 'light' ? 0 : -180,
          opacity: theme === 'light' ? 1 : 0
        }}
        transition={{ duration: 0.3 }}
      >
        <Sun size={20} />
      </motion.div>
    </motion.button>
  );
}

export default ThemeToggle;
