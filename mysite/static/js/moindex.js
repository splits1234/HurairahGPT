const history = {{ history | tojson }};
    const sessions = {{ (sessions or {}) | tojson }};
    const activeSession = {{ (active_session or '') | tojson }};
    const chatBox = document.getElementById("chat-box");
    const chatForm = document.getElementById("chat-form");
    const messageInput = document.getElementById("message-input");
    const sessionsListMobile = document.getElementById("sessions-list-mobile");
    const newSessionBtnMobile = document.getElementById("new-session-btn-mobile");
    const voiceInputBtn = document.getElementById("voice-input-btn");
    const sendSound = document.getElementById("send-sound");
    const receiveSound = document.getElementById("receive-sound");
    
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

    function appendMessage(msg, sender) {
      const div = document.createElement("div");
      div.className = "message " + sender;
      div.innerHTML = marked.parseInline(msg);
      chatBox.appendChild(div);
      chatBox.scrollTop = chatBox.scrollHeight;
      
      // Play sound effects
      try {
        if (sender === 'user') {
          sendSound.play().catch(e => console.warn('Sound play failed:', e));
        } else {
          receiveSound.play().catch(e => console.warn('Sound play failed:', e));
        }
      } catch (e) {
        console.warn('Sound error:', e);
      }
    }
    
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

    chatForm.addEventListener("submit", async e => {
      e.preventDefault();
      const msg = messageInput.value.trim();
      if (!msg) return;
      appendMessage(msg, "user");
      messageInput.value = "";
      
      // Create a bot message element for streaming
      const botMessageDiv = document.createElement("div");
      botMessageDiv.className = "message bot";
      botMessageDiv.innerHTML = "";
      chatBox.appendChild(botMessageDiv);
      chatBox.scrollTop = chatBox.scrollHeight;
      
      let fullResponse = "";
      let shouldSpeak = true; // Flag to speak only once when complete
      
      try {
        const res = await fetch("/chat", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({ message: msg, stream: true })
        });

        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              try {
                const data = JSON.parse(line.slice(6));
                if (data.chunk) {
                  fullResponse += data.chunk;
                  botMessageDiv.innerHTML = marked.parseInline(fullResponse);
                  chatBox.scrollTop = chatBox.scrollHeight;
                }
                if (data.done) {
                  if (data.error) {
                    botMessageDiv.innerHTML = marked.parseInline(data.error);
                    fullResponse = data.error;
                  } else if (data.full_response) {
                    fullResponse = data.full_response;
                    botMessageDiv.innerHTML = marked.parseInline(fullResponse);
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
                console.warn("Failed to parse SSE data:", e);
              }
            }
          }
        }
      } catch (err) {
        botMessageDiv.innerHTML = marked.parseInline("Network error. Please try again.");
        console.error("Streaming error:", err);
        try {
          receiveSound.play().catch(e => console.warn('Sound play failed:', e));
        } catch (e) {
          console.warn('Sound error:', e);
        }
      }
    });

    function clearChat() {
      chatBox.innerHTML = "";
      fetch("/chat", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({ message: "__CLEAR__" }) })
        .then(r=>r.json()).then(d=>appendMessage(d.response,"bot"));
    }
    function exportChat() {
      const text = Array.from(chatBox.querySelectorAll(".message"))
        .map(m=>m.textContent).join("\n");
      const blob = new Blob([text], {type:"text/plain"});
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "HurairahGPT_Chat.txt";
      a.click();
      URL.revokeObjectURL(a.href);
    }
    function toggleDarkMode() {
      document.body.classList.toggle("light");
      const light = document.body.classList.contains("light");
      document.getElementById("darkBtn").textContent = light ? "🌙 Dark Mode" : "☀️ Light Mode";
      localStorage.setItem("theme", light ? "light" : "dark");
      fetch("/theme", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({ theme: light ? "light":"dark" }) });
    }
    document.getElementById("personality-mobile").addEventListener("change", async function() {
      await fetch("/personality", {
        method: "POST", headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ personality: this.value })
      });
    });

    // Session management
    let currentSessions = sessions || {};
    let currentActiveSession = activeSession;

    function renderSessionsMobile() {
      sessionsListMobile.innerHTML = '';
      Object.entries(currentSessions).forEach(([id, session]) => {
        const item = document.createElement('div');
        item.className = 'side-btn';
        item.style.cssText = 'text-align:left;position:relative;padding-right:32px;';
        if (id === currentActiveSession) {
          item.style.background = 'rgba(99, 102, 241, 0.2)';
          item.style.borderColor = 'rgba(99, 102, 241, 0.6)';
        }
        item.innerHTML = `
          <span>${session.name}</span>
          ${id !== currentActiveSession ? `<button class="icon-btn" style="position:absolute;right:4px;top:50%;transform:translateY(-50%);padding:2px 6px;font-size:0.7rem;" data-action="delete" data-id="${id}" title="Delete">🗑</button>` : ''}
        `;
        item.addEventListener('click', (e) => {
          if (!e.target.closest('button')) {
            switchSessionMobile(id);
          }
        });
        sessionsListMobile.appendChild(item);
      });

      sessionsListMobile.querySelectorAll('button[data-action="delete"]').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          const sessionId = btn.dataset.id;
          if (confirm('Delete this chat session?')) {
            deleteSessionMobile(sessionId);
          }
        });
      });
    }

    async function createSessionMobile(name) {
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
          renderSessionsMobile();
          chatBox.innerHTML = '';
          sideMenu.classList.remove('open');
          return true;
        }
      } catch (e) {
        console.error('Failed to create session', e);
      }
      return false;
    }

    async function switchSessionMobile(sessionId) {
      if (sessionId === currentActiveSession) {
        sideMenu.classList.remove('open');
        return;
      }
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
          renderSessionsMobile();
          chatBox.innerHTML = '';
          data.history.forEach(h => {
            appendMessage(h.content, h.sender || 'bot');
          });
          chatBox.scrollTop = chatBox.scrollHeight;
          sideMenu.classList.remove('open');
        }
      } catch (e) {
        console.error('Failed to switch session', e);
      }
    }

    async function deleteSessionMobile(sessionId) {
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
          renderSessionsMobile();
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

    newSessionBtnMobile.addEventListener('click', () => {
      createSessionMobile();
    });

    window.addEventListener("DOMContentLoaded", ()=>{
      const theme = localStorage.getItem("theme");
      if(theme==="light") document.body.classList.add("light");
      renderSessionsMobile();
      history.forEach(({sender, content}) => appendMessage(content, sender));
    });

    const menuBtn = document.getElementById("menuToggle");
    const sideMenu = document.getElementById("sideMenu");
    const closeBtn = document.getElementById("closeMenu");
    menuBtn.onclick = ()=> sideMenu.classList.add("open");
    closeBtn.onclick = ()=> sideMenu.classList.remove("open");
    document.addEventListener("click", e=>{
      if(sideMenu.classList.contains("open") && !sideMenu.contains(e.target) && e.target!==menuBtn)
        sideMenu.classList.remove("open");
    });