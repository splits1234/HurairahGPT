import { motion } from 'framer-motion';
import { Sun, Moon } from 'lucide-react';
import { useTheme } from '../hooks/useTheme';
import styles from './ThemeToggle.module.css';

export function ThemeToggle() {
    const { theme, toggleTheme } = useTheme();

    return (
        <motion.button
            className={styles.toggleBtn}
            onClick={toggleTheme}
            whileTap={{ scale: 0.95 }}
            whileHover={{ scale: 1.05 }}
            aria-label="Toggle Theme"
        >
            <motion.div
                initial={false}
                animate={{
                    rotate: theme === 'dark' ? 0 : 180,
                    opacity: theme === 'dark' ? 1 : 0
                }}
                transition={{ duration: 0.3 }}
                style={{ position: 'absolute' }}
            >
                <Moon size={20} color="var(--text-secondary)" />
            </motion.div>

            <motion.div
                initial={false}
                animate={{
                    rotate: theme === 'light' ? 0 : -180,
                    opacity: theme === 'light' ? 1 : 0
                }}
                transition={{ duration: 0.3 }}
                style={{ position: 'absolute' }}
            >
                <Sun size={20} color="var(--text-primary)" />
            </motion.div>
        </motion.button>
    );
}
