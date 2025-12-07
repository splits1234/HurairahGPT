// --- data from server via Jinja ---
    const history = {{ history | tojson }};
    const sessions = {{ (sessions or {}) | tojson }};
    const activeSession = {{ (active_session or '') | tojson }};

    // --- element refs ---
    const chatBox = document.getElementById('chat-box');
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const darkModeBtn = document.getElementById('darkModeBtn');
    const clearBtn = document.getElementById('clearBtn');
    const exportBtn = document.getElementById('exportBtn');
    const personalitySelect = document.getElementById('personality');
    const sendSound = document.getElementById('send-sound');
    const receiveSound = document.getElementById('receive-sound');
    const voiceInputBtn = document.getElementById('voice-input-btn');
    
    // Voice input/output setup
    let recognition = null;
    let isRecording = false;
    let synth = window.speechSynthesis;
    let currentUtterance = null;
    
    // Initialize speech recognition
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-US';
      
      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        messageInput.value = transcript;
        messageInput.focus();
      };
      
      recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        voiceInputBtn.classList.remove('recording');
        isRecording = false;
      };
      
      recognition.onend = () => {
        voiceInputBtn.classList.remove('recording');
        isRecording = false;
      };
    } else {
      voiceInputBtn.style.display = 'none';
    }
    
    // Voice input button handler
    voiceInputBtn.addEventListener('click', () => {
      if (!recognition) return;
      
      if (isRecording) {
        recognition.stop();
        isRecording = false;
        voiceInputBtn.classList.remove('recording');
      } else {
        recognition.start();
        isRecording = true;
        voiceInputBtn.classList.add('recording');
      }
    });
    
    // Text-to-speech function
    function speakText(text) {
      if (!synth) return;
      
      // Stop any current speech
      if (currentUtterance) {
        synth.cancel();
      }
      
      // Clean text (remove markdown formatting for speech)
      const cleanText = text.replace(/[#*_`\[\]()]/g, '').trim();
      if (!cleanText) return;
      
      currentUtterance = new SpeechSynthesisUtterance(cleanText);
      currentUtterance.lang = 'en-US';
      currentUtterance.rate = 1.0;
      currentUtterance.pitch = 1.0;
      currentUtterance.volume = 0.8;
      
      synth.speak(currentUtterance);
      
      currentUtterance.onend = () => {
        currentUtterance = null;
      };
    }
    const sessionsList = document.getElementById('sessions-list');
    const newSessionBtn = document.getElementById('new-session-btn');

    // Safety: use DOMPurify + marked
    const renderMarkdown = (text) => {
      // marked.parse supports multiline & block formatting
      const raw = marked.parse(String(text || ''));
      return DOMPurify.sanitize(raw, {ALLOWED_TAGS: ['b','i','em','strong','a','p','code','pre','br','ul','ol','li','blockquote','img','h1','h2','h3','span'], ALLOWED_ATTR: ['href','target','rel','src','alt','class','title','width','height','style']});
    };

    // Install prompt deferred globally so our install button can call it
    let deferredPrompt = null;

    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault();
      deferredPrompt = e;
      // show an unobtrusive install button in bottom-right
      if (!document.getElementById('pwa-install-btn')) {
        const installBtn = document.createElement('button');
        installBtn.id = 'pwa-install-btn';
        installBtn.textContent = 'Install HurairahGPT';
        installBtn.setAttribute('aria-label','Install HurairahGPT');
        Object.assign(installBtn.style, { position:'fixed', right:'18px', bottom:'18px', zIndex:1100, padding:'10px 14px', borderRadius:'10px' });
        document.body.appendChild(installBtn);
        installBtn.addEventListener('click', async () => {
          installBtn.style.display = 'none';
          try {
            await deferredPrompt.prompt();
            const choice = await deferredPrompt.userChoice;
            console.log('PWA install outcome', choice);
          } catch (err) {
            console.warn('Install prompt failed', err);
          } finally {
            deferredPrompt = null;
          }
        });
      }
    });

    // appendMessage with safety for images & reactions
    function appendMessage(message, sender='bot') {
      const wrapper = document.createElement('div');
      wrapper.className = 'message ' + sender;

      // If message is an image URL, render img (but still sanitize)
      const trimmed = String(message || '').trim();
      const isImgUrl = /^https?:\/\/.+\.(png|jpe?g|gif|webp|svg)(\?.*)?$/i.test(trimmed);

      if (isImgUrl) {
        const img = document.createElement('img');
        img.src = trimmed;
        img.alt = 'user provided image';
        wrapper.appendChild(img);
      } else {
        // Use marked + DOMPurify to safely convert markdown -> sanitized HTML
        wrapper.innerHTML = renderMarkdown(trimmed);
      }

      // If bot message, add small reaction buttons
      if (sender === 'bot') {
        const reactBox = document.createElement('span');
        reactBox.className = 'reactions';
        ['👍','😂','❤️'].forEach(r => {
          const btn = document.createElement('button');
          btn.className = 'reaction-btn';
          btn.type = 'button';
          btn.title = `React ${r}`;
          btn.textContent = r;
          btn.onclick = () => {
            // Simple optimistic UI: show a small toast-like message
            // (replace with any telemetry or server call you need)
            const prev = document.getElementById('reaction-toast');
            if (prev) prev.remove();
            const toast = document.createElement('div');
            toast.id = 'reaction-toast';
            toast.textContent = `You reacted ${r}`;
            Object.assign(toast.style, { position:'fixed', right:'18px', bottom:'70px', padding:'8px 12px', background:'#111', color:'#fff', borderRadius:'8px', zIndex:1200 });
            document.body.appendChild(toast);
            setTimeout(()=> toast.remove(), 1400);
          };
          reactBox.appendChild(btn);
        });
        wrapper.appendChild(reactBox);
      }

      chatBox.appendChild(wrapper);
      chatBox.scrollTop = chatBox.scrollHeight;

      // play sound
      try { 
        if (sender === 'user') {
          sendSound.play().catch(e => console.warn('Sound play failed:', e));
        } else {
          receiveSound.play().catch(e => console.warn('Sound play failed:', e));
        }
      } catch(e){
        console.warn('Sound error:', e);
      }
      return wrapper;
    }

    // show typing indicator
    function showTyping() {
      if (document.getElementById('typing')) return;
      const t = document.createElement('div');
      t.id = 'typing';
      t.className = 'typing-indicator';
      t.textContent = 'Hurairah is typing...';
      chatBox.appendChild(t);
      chatBox.scrollTop = chatBox.scrollHeight;
    }
    function hideTyping() { const t = document.getElementById('typing'); if (t) t.remove(); }

    // clear & export
    async function clearChat() {
      chatBox.innerHTML = '';
      try {
        const res = await fetch('/chat', { method:'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ message: '__CLEAR__' }) });
        const data = await res.json();
        if (data && data.response) appendMessage(data.response, 'bot');
      } catch (e) {
        appendMessage('Network error clearing chat.', 'bot');
      }
    }
    async function exportChat() {
      const lines = Array.from(chatBox.querySelectorAll('.message')).map(m => m.textContent.trim()).filter(Boolean);
      const blob = new Blob([lines.join('\n\n')], {type:'text/plain;charset=utf-8'});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'HurairahGPT_Chat.txt';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    }

    // submit handler with streaming support
    chatForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const msg = messageInput.value.trim();
      if (!msg) return;
      appendMessage(msg, 'user');
      messageInput.value = '';
      messageInput.disabled = true;
      messageInput.focus();
      
      // Create a bot message element for streaming
      const botMessageDiv = document.createElement('div');
      botMessageDiv.className = 'message bot';
      botMessageDiv.innerHTML = '';
      chatBox.appendChild(botMessageDiv);
      chatBox.scrollTop = chatBox.scrollHeight;
      
      let fullResponse = '';
      let shouldSpeak = true; // Flag to speak only once when complete
      
      try {
        const res = await fetch('/chat', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ message: msg, stream: true })
        });

        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // Keep incomplete line in buffer

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                if (data.chunk) {
                  fullResponse += data.chunk;
                  // Update the message content with markdown rendering
                  botMessageDiv.innerHTML = renderMarkdown(fullResponse);
                  chatBox.scrollTop = chatBox.scrollHeight;
                }
                if (data.done) {
                  if (data.error) {
                    botMessageDiv.innerHTML = renderMarkdown(data.error);
                    fullResponse = data.error;
                  } else if (data.full_response) {
                    fullResponse = data.full_response;
                    botMessageDiv.innerHTML = renderMarkdown(fullResponse);
                  }
                  
                  // Play receive sound and speak response
                  try {
                    receiveSound.play().catch(e => console.warn('Sound play failed:', e));
                  } catch (e) {
                    console.warn('Sound error:', e);
                  }
                  
                  // Speak the response
                  if (shouldSpeak && fullResponse) {
                    speakText(fullResponse);
                    shouldSpeak = false;
                  }
                  break;
                }
              } catch (e) {
                console.warn('Failed to parse SSE data:', e);
              }
            }
          }
        }
      } catch (err) {
        botMessageDiv.innerHTML = renderMarkdown('Network error. Please try again.');
        console.error('Streaming error:', err);
        try {
          receiveSound.play().catch(e => console.warn('Sound play failed:', e));
        } catch (e) {
          console.warn('Sound error:', e);
        }
      } finally {
        messageInput.disabled = false;
        messageInput.focus();
      }
    });

    // Enter to send (Shift+Enter for newline)
    messageInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        chatForm.requestSubmit();
      }
    });

    // theme toggle
    function toggleDarkMode() {
      const isLight = document.body.classList.toggle('light');
      darkModeBtn.textContent = isLight ? '🌙 Dark Mode' : '☀️ Light Mode';
      darkModeBtn.setAttribute('aria-pressed', isLight ? 'true':'false');
      localStorage.setItem('theme', isLight ? 'light':'dark');
      // persist to server (best-effort)
      fetch('/theme', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ theme: isLight ? 'light':'dark' }) }).catch(()=>{/*silent*/});
    }
    darkModeBtn.addEventListener('click', toggleDarkMode);

    // personality selector persistence
    personalitySelect.addEventListener('change', async function(){
      const val = this.value;
      try { await fetch('/personality', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ personality: val }) }); } catch(e){ console.warn('personality save failed'); }
    });

    // Session management
    let currentSessions = sessions || {};
    let currentActiveSession = activeSession;

    function renderSessions() {
      sessionsList.innerHTML = '';
      Object.entries(currentSessions).forEach(([id, session]) => {
        const item = document.createElement('div');
        item.className = `session-item ${id === currentActiveSession ? 'active' : ''}`;
        item.innerHTML = `
          <span class="session-name" title="${session.name}">${session.name}</span>
          <div class="session-actions">
            <button class="session-btn delete" data-action="delete" data-id="${id}" title="Delete session">🗑</button>
          </div>
        `;
        item.addEventListener('click', (e) => {
          if (!e.target.closest('.session-actions')) {
            switchSession(id);
          }
        });
        sessionsList.appendChild(item);
      });

      // Add delete handlers
      sessionsList.querySelectorAll('.session-btn.delete').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          const sessionId = btn.dataset.id;
          if (confirm('Delete this chat session? This cannot be undone.')) {
            deleteSession(sessionId);
          }
        });
      });
    }

    async function createSession(name) {
      try {
        const res = await fetch('/sessions/create', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: name || `Chat ${Object.keys(currentSessions).length + 1}` })
        });
        const data = await res.json();
        if (data.success) {
          currentSessions = data.sessions;
          currentActiveSession = data.session_id;
          renderSessions();
          chatBox.innerHTML = '';
          return true;
        }
      } catch (e) {
        console.error('Failed to create session', e);
      }
      return false;
    }

    async function switchSession(sessionId) {
      if (sessionId === currentActiveSession) return;
      try {
        const res = await fetch('/sessions/switch', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sessionId })
        });
        const data = await res.json();
        if (data.success) {
          currentActiveSession = sessionId;
          currentSessions = data.sessions;
          renderSessions();
          chatBox.innerHTML = '';
          data.history.forEach(h => {
            appendMessage(h.content, h.sender || 'bot');
          });
          chatBox.scrollTop = chatBox.scrollHeight;
        }
      } catch (e) {
        console.error('Failed to switch session', e);
      }
    }

    async function deleteSession(sessionId) {
      try {
        const res = await fetch('/sessions/delete', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sessionId })
        });
        const data = await res.json();
        if (data.success) {
          currentSessions = data.sessions;
          currentActiveSession = data.active_session;
          renderSessions();
          chatBox.innerHTML = '';
          data.history.forEach(h => {
            appendMessage(h.content, h.sender || 'bot');
          });
          chatBox.scrollTop = chatBox.scrollHeight;
        }
      } catch (e) {
        console.error('Failed to delete session', e);
      }
    }

    newSessionBtn.addEventListener('click', () => {
      createSession();
    });

    // drag & drop images into chat
    chatBox.addEventListener('dragover', (e) => e.preventDefault());
    chatBox.addEventListener('drop', (e) => {
      e.preventDefault();
      const f = e.dataTransfer.files && e.dataTransfer.files[0];
      if (f && f.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = () => appendMessage(reader.result, 'user');
        reader.readAsDataURL(f);
      }
    });

    // service worker registration
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/static/service-worker.js').catch(err => console.warn('SW failed', err));
    }

    // install hooks: also expose deferredPrompt on window for debugging
    window.deferredPrompt = deferredPrompt;

    // attach small convenience handlers
    clearBtn.addEventListener('click', clearChat);
    exportBtn.addEventListener('click', exportChat);

    // load history on DOMContentLoaded
    window.addEventListener('DOMContentLoaded', () => {
      const savedTheme = localStorage.getItem('theme');
      if (savedTheme === 'light') {
        document.body.classList.add('light');
      }
      darkModeBtn.textContent = document.body.classList.contains('light') ? '🌙 Dark Mode' : '☀️ Light Mode';
      
      // Render sessions
      renderSessions();
      
      // render existing conversation history
      if (Array.isArray(history)) {
        history.forEach(h => {
          // each history entry expected {sender: 'user'|'bot', content: '...'}
          appendMessage(h.content, h.sender || 'bot');
        });
      }
      chatBox.scrollTop = chatBox.scrollHeight;
      // focus input for quick typing
      messageInput.focus();
    });