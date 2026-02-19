/**
 * HurairahGPT - Theme Toggle Component
 * =====================================
 * 
 * A toggle button component that switches between light and dark themes.
 * Features smooth animated transitions between theme states.
 * 
 * Features:
 * - Animated slider switch
 * - Smooth slide transitions
 * - Persistent theme preference (localStorage)
 * - Accessibility support
 * 
 * @component
 * @version 2.0.0
 * @author Hurairah
 */

import { useTheme } from '../hooks/useTheme';
import styles from './ThemeToggle.module.css';

/**
 * ThemeToggle - Theme Switching Button Component
 * 
 * A visually appealing toggle switch that slides between dark and light modes.
 * Uses the sun/moon box-shadow animation for visual feedback.
 * 
 * @returns {JSX.Element} Rendered theme toggle button
 */
export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <label 
      className={styles.switch}
      title={`Current theme: ${theme}. Click to switch.`}
    >
      <input
        type="checkbox"
        className={styles.checkbox}
        checked={theme === 'light'}
        onChange={() => toggleTheme()}
        aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
      />
      <span className={styles.slider}></span>
    </label>
  );
}

export default ThemeToggle;
