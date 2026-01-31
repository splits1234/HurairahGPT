import { useState } from 'react';
import { motion } from 'framer-motion';
import { Paperclip, Mic, ArrowUp } from 'lucide-react';
import styles from './InputBar.module.css';

export function InputBar({ onSend }) {
    const [text, setText] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!text.trim()) return;
        onSend(text);
        setText('');
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e);
        }
    };

    return (
        <div className={styles.container}>
            {/* Central Input Pill */}
            <motion.div
                className={styles.inputWrapper}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
            >
                <button className={styles.attachBtn} aria-label="Attach file">
                    <Paperclip size={20} />
                </button>

                <input
                    type="text"
                    placeholder="How can I help you today?"
                    className={styles.input}
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    onKeyDown={handleKeyDown}
                />

                <div className={styles.rightActions}>
                    <button className={styles.voiceBtn} onClick={handleSubmit} aria-label="Send">
                        <ArrowUp size={20} />
                    </button>
                </div>
            </motion.div>
        </div>
    );
}
