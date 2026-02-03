/**
 * HurairahGPT - Theme Management Hook
 * ====================================
 * 
 * A custom React hook for managing the application's theme state.
 * Provides theme switching functionality with localStorage persistence.
 * 
 * Features:
 * - Theme state management (dark/light)
 * - LocalStorage persistence
 * - Document-level theme application
 * - SSR-safe (checks for window availability)
 * 
 * @hook
 * @version 1.0.0
 * @author Hurairah
 */

import { useState, useEffect, useCallback } from 'react';

/**
 * Theme Type Definition
 * @typedef {'dark' | 'light'} Theme
 */

/**
 * Theme Hook Return Type
 * @typedef {Object} ThemeReturn
 * @property {Theme} theme - Current theme ('dark' or 'light')
 * @property {Function} toggleTheme - Function to toggle between themes
 */

/**
 * useTheme - Custom Hook for Theme Management
 * 
 * Manages the application's theme state and provides methods to toggle
 * between light and dark modes. The theme preference is persisted
 * in localStorage and applied to the document's data-theme attribute.
 * 
 * @returns {ThemeReturn} Object containing current theme and toggle function
 * 
 * @example
 * const { theme, toggleTheme } = useTheme();
 * 
 * // Toggle theme
 * toggleTheme();
 * 
 * // Use in component
 * <div data-theme={theme}>Content</div>
 */
export function useTheme() {
  /**
   * Theme state
   * Defaults to 'dark' if no saved preference or on first visit
   */
  const [theme, setTheme] = useState('dark');

  /**
   * Initialize theme on component mount
   * 
   * This effect:
   * 1. Checks localStorage for saved theme preference
   * 2. Falls back to 'dark' if no preference exists
   * 3. Applies theme to document element
   */
  useEffect(() => {
    // Check if window is available (SSR safety)
    if (typeof window === 'undefined') {
      return;
    }

    // Retrieve saved theme from localStorage
    const savedTheme = localStorage.getItem('hurairahgpt_theme');

    if (savedTheme) {
      // Use saved preference
      setTheme(savedTheme);
      document.documentElement.setAttribute('data-theme', savedTheme);
    } else {
      // Default to dark theme
      document.documentElement.setAttribute('data-theme', 'dark');
    }
  }, []);

  /**
   * Toggle between light and dark themes
   * 
   * This function:
   * 1. Determines the new theme (opposite of current)
   * 2. Updates React state
   * 3. Applies theme to document element
   * 4. Persists preference in localStorage
   * 
   * @returns {void}
   */
  const toggleTheme = useCallback(() => {
    setTheme((currentTheme) => {
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      
      // Apply to document
      document.documentElement.setAttribute('data-theme', newTheme);
      
      // Persist preference
      localStorage.setItem('hurairahgpt_theme', newTheme);
      
      return newTheme;
    });
  }, []);

  /**
   * Set a specific theme programmatically
   * 
   * @param {Theme} newTheme - The theme to set ('dark' or 'light')
   */
  const setSpecificTheme = useCallback((newTheme) => {
    if (newTheme === 'dark' || newTheme === 'light') {
      setTheme(newTheme);
      document.documentElement.setAttribute('data-theme', newTheme);
      localStorage.setItem('hurairahgpt_theme', newTheme);
    }
  }, []);

  return { 
    theme, 
    toggleTheme,
    setTheme: setSpecificTheme
  };
}

export default useTheme;
