// ==========================================================
// Gemini Flash Web Chatbot Client Logic
// ==========================================================

document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const welcomeSection = document.getElementById('welcome-section');
  const chatMessagesContainer = document.getElementById('chat-messages');
  const chatInput = document.getElementById('chat-input');
  const sendBtn = document.getElementById('send-btn');
  const newChatBtn = document.getElementById('new-chat-btn');
  const plusBtn = document.getElementById('plus-btn');
  const fileInput = document.getElementById('file-input');
  const attachmentPreviewBar = document.getElementById('attachment-preview-bar');
  const attachmentImgPreview = document.getElementById('attachment-img-preview');
  const attachmentFilename = document.getElementById('attachment-filename');
  const attachmentFilesize = document.getElementById('attachment-filesize');
  const removeAttachmentBtn = document.getElementById('remove-attachment-btn');

  // Model Dropdown
  const modelDropdownWrapper = document.getElementById('model-dropdown-wrapper');
  const modelSelectBtn = document.getElementById('model-select-btn');
  const selectedModelLabel = document.getElementById('selected-model-label');
  const navModelName = document.getElementById('nav-model-name');
  const modelOptions = document.querySelectorAll('.model-option');

  // User Name
  const userDisplayName = document.getElementById('user-display-name');
  const renameUserBtn = document.getElementById('rename-user-btn');

  // Mic & Status & Web Search
  const micBtn = document.getElementById('mic-btn');
  const webSearchBtn = document.getElementById('web-search-btn');
  const apiStatusBadge = document.getElementById('api-status-badge');
  const statusText = document.getElementById('status-text');

  // Suggestion Chips
  const suggestionChips = document.querySelectorAll('.chip');

  // State
  let currentModel = 'gemini-3.8-flash';
  let conversationHistory = []; // {role: 'user'|'model', content: string, image?: {mime_type, data}}
  let isGenerating = false;
  let isSearchEnabled = true; // Google Search Grounding connected by default
  let attachedImage = null; // {mime_type: string, data: string, name: string}
  let speechRecognition = null;
  let isRecording = false;

  // Initialize marked.js
  if (window.marked) {
    marked.setOptions({
      breaks: true,
      gfm: true,
      highlight: function(code, lang) {
        if (window.hljs && lang && hljs.getLanguage(lang)) {
          return hljs.highlight(code, { language: lang }).value;
        }
        return window.hljs ? hljs.highlightAuto(code).value : code;
      }
    });
  }

  // Load Saved Username
  const savedName = localStorage.getItem('gemini_user_name') || '사용자';
  userDisplayName.textContent = savedName;

  function editUserName() {
    const newName = prompt('화면에 표시할 이름을 입력해주세요:', userDisplayName.textContent.trim());
    if (newName && newName.trim()) {
      const cleanName = newName.trim();
      userDisplayName.textContent = cleanName;
      localStorage.setItem('gemini_user_name', cleanName);
    }
  }

  userDisplayName.addEventListener('click', editUserName);
  renameUserBtn.addEventListener('click', editUserName);

  // Check Backend Status
  async function checkStatus() {
    try {
      const res = await fetch('/api/status');
      const data = await res.json();
      if (data.apiKeySet) {
        apiStatusBadge.classList.add('ready');
        apiStatusBadge.classList.remove('error');
        statusText.textContent = `API 연결됨 (${data.maskedKey})`;
      } else {
        apiStatusBadge.classList.remove('ready');
        apiStatusBadge.classList.add('error');
        statusText.textContent = 'API 키 미설정';
      }
    } catch (e) {
      console.warn('Status check error:', e);
      statusText.textContent = '로컬 서버 확인 필요';
    }
  }
  checkStatus();

  // Model Selection Dropdown
  modelSelectBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    modelDropdownWrapper.classList.toggle('open');
    modelSelectBtn.setAttribute('aria-expanded', modelDropdownWrapper.classList.contains('open'));
  });

  document.addEventListener('click', (e) => {
    if (!modelDropdownWrapper.contains(e.target)) {
      modelDropdownWrapper.classList.remove('open');
      modelSelectBtn.setAttribute('aria-expanded', 'false');
    }
  });

  modelOptions.forEach(option => {
    option.addEventListener('click', () => {
      const modelId = option.getAttribute('data-model');
      setModel(modelId);
      modelDropdownWrapper.classList.remove('open');
      modelSelectBtn.setAttribute('aria-expanded', 'false');
    });
  });

  function setModel(modelId) {
    currentModel = modelId;
    modelOptions.forEach(opt => {
      if (opt.getAttribute('data-model') === modelId) {
        opt.classList.add('active');
      } else {
        opt.classList.remove('active');
      }
    });

    if (modelId === 'gemini-3.8-flash') {
      selectedModelLabel.textContent = 'Flash 3.8';
      navModelName.textContent = 'Gemini 3.8 Flash';
    } else {
      selectedModelLabel.textContent = 'Flash 3.7';
      navModelName.textContent = 'Gemini 3.7 Flash';
    }
  }

  // File Upload Handling (+)
  plusBtn.addEventListener('click', () => {
    fileInput.click();
  });

  fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      alert('현재 이미지 파일(.png, .jpg, .webp 등) 첨부만 지원됩니다.');
      fileInput.value = '';
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      const base64Data = event.target.result.split(',')[1];
      attachedImage = {
        mime_type: file.type,
        data: base64Data,
        name: file.name
      };

      attachmentImgPreview.src = event.target.result;
      attachmentFilename.textContent = file.name;
      attachmentFilesize.textContent = `${(file.size / 1024).toFixed(1)} KB`;
      attachmentPreviewBar.style.display = 'flex';
      validateInput();
    };
    reader.readAsDataURL(file);
  });

  removeAttachmentBtn.addEventListener('click', () => {
    clearAttachment();
  });

  function clearAttachment() {
    attachedImage = null;
    attachmentPreviewBar.style.display = 'none';
    attachmentImgPreview.src = '';
    fileInput.value = '';
    validateInput();
  }

  // Web Speech API (Microphone)
  if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    speechRecognition = new SpeechRecognition();
    speechRecognition.continuous = false;
    speechRecognition.interimResults = true;
    speechRecognition.lang = 'ko-KR';

    speechRecognition.onstart = () => {
      isRecording = true;
      micBtn.classList.add('recording');
      micBtn.setAttribute('data-tooltip', '듣고 있습니다... 클릭하여 중지');
    };

    speechRecognition.onresult = (event) => {
      let transcript = '';
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        transcript += event.results[i][0].transcript;
      }
      chatInput.value = transcript;
      adjustTextareaHeight();
      validateInput();
    };

    speechRecognition.onerror = (e) => {
      console.warn('Speech recognition error:', e);
      stopRecording();
    };

    speechRecognition.onend = () => {
      stopRecording();
    };

    micBtn.addEventListener('click', () => {
      if (isRecording) {
        stopRecording();
      } else {
        try {
          speechRecognition.start();
        } catch (e) {
          console.warn(e);
        }
      }
    });

    function stopRecording() {
      isRecording = false;
      micBtn.classList.remove('recording');
      micBtn.setAttribute('data-tooltip', '음성으로 질문하기');
      try {
        speechRecognition.stop();
      } catch (e) {}
    }
  } else {
    micBtn.style.opacity = '0.5';
    micBtn.setAttribute('data-tooltip', '이 브라우저는 음성 인식을 지원하지 않습니다');
  }

  // Web Search Toggle
  if (webSearchBtn) {
    webSearchBtn.addEventListener('click', () => {
      isSearchEnabled = !isSearchEnabled;
      if (isSearchEnabled) {
        webSearchBtn.classList.add('active');
        webSearchBtn.setAttribute('data-tooltip', '웹 검색 연결됨 (Google Search Grounding)');
      } else {
        webSearchBtn.classList.remove('active');
        webSearchBtn.setAttribute('data-tooltip', '웹 검색 꺼짐 (내부 지식만 사용)');
      }
    });
  }

  // Suggestion Chips Click
  suggestionChips.forEach(chip => {
    chip.addEventListener('click', () => {
      const prompt = chip.getAttribute('data-prompt');
      if (prompt) {
        chatInput.value = prompt;
        adjustTextareaHeight();
        validateInput();
        sendMessage();
      }
    });
  });

  // Auto-resize textarea
  chatInput.addEventListener('input', () => {
    adjustTextareaHeight();
    validateInput();
  });

  function adjustTextareaHeight() {
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 160) + 'px';
  }

  function validateInput() {
    const hasText = chatInput.value.trim().length > 0;
    const hasImage = attachedImage !== null;
    sendBtn.disabled = !(hasText || hasImage) || isGenerating;
  }

  // Keydown Handling (Enter / Shift+Enter)
  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!sendBtn.disabled) {
        sendMessage();
      }
    }
  });

  sendBtn.addEventListener('click', () => {
    if (!sendBtn.disabled) {
      sendMessage();
    }
  });

  // New Chat Button
  newChatBtn.addEventListener('click', () => {
    if (conversationHistory.length === 0) return;
    if (isGenerating) return;

    if (confirm('현재 대화를 비우고 새로운 대화를 시작하시겠습니까?')) {
      resetChat();
    }
  });

  function resetChat() {
    conversationHistory = [];
    chatMessagesContainer.innerHTML = '';
    chatMessagesContainer.style.display = 'none';
    welcomeSection.style.display = 'flex';
    welcomeSection.classList.remove('fade-out');
    clearAttachment();
    chatInput.value = '';
    adjustTextareaHeight();
    validateInput();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // Send Message Flow
  async function sendMessage() {
    const messageText = chatInput.value.trim();
    const currentAttachment = attachedImage;

    if (!messageText && !currentAttachment) return;
    if (isGenerating) return;

    // Transition from welcome screen to chat messages
    if (welcomeSection.style.display !== 'none') {
      welcomeSection.classList.add('fade-out');
      setTimeout(() => {
        welcomeSection.style.display = 'none';
        chatMessagesContainer.style.display = 'flex';
      }, 250);
    }

    // Add user message to history & UI
    const userMsgObj = {
      role: 'user',
      content: messageText,
      image: currentAttachment ? { mime_type: currentAttachment.mime_type, data: currentAttachment.data } : undefined
    };
    conversationHistory.push(userMsgObj);

    appendUserMessage(messageText, currentAttachment);

    // Clear input
    chatInput.value = '';
    adjustTextareaHeight();
    clearAttachment();
    validateInput();

    // Prepare Gemini message bubble for streaming
    const geminiBubbleId = 'gemini-bubble-' + Date.now();
    const currentModelName = currentModel === 'gemini-3.8-flash' ? 'Gemini 3.8 Flash' : 'Gemini 3.7 Flash';
    appendGeminiPlaceholder(geminiBubbleId, currentModelName);

    // Start streaming from backend
    isGenerating = true;
    sendBtn.disabled = true;

    const bubbleEl = document.getElementById(geminiBubbleId);
    let fullText = '';
    let groundingData = null;

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: currentModel,
          messages: conversationHistory,
          enable_search: isSearchEnabled,
          thinking_level: 'medium'
        })
      });

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({ detail: '서버 오류' }));
        throw new Error(errJson.detail || '응답을 받아오지 못했습니다.');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // Keep last incomplete line

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith('data: ')) continue;
          const dataStr = trimmed.substring(6).trim();
          if (dataStr === '[DONE]') break;

          try {
            const parsed = JSON.parse(dataStr);
            if (parsed.error) {
              fullText += `\n\n> ⚠️ **오류**: ${parsed.error}`;
              renderMarkdown(bubbleEl, fullText, false, groundingData);
            } else if (parsed.grounding) {
              groundingData = parsed.grounding;
            } else if (parsed.text) {
              fullText += parsed.text;
              renderMarkdown(bubbleEl, fullText, true, groundingData);
              scrollToBottom();
            }
          } catch (e) {
            console.error('SSE JSON parse error:', e, dataStr);
          }
        }
      }

      // Finish streaming
      renderMarkdown(bubbleEl, fullText, false, groundingData);
      conversationHistory.push({ role: 'model', content: fullText });

    } catch (err) {
      console.error('Chat error:', err);
      bubbleEl.innerHTML = `<div style="color: #ea4335;">⚠️ 통신 오류가 발생했습니다: ${escapeHtml(err.message)}</div>`;
    } finally {
      isGenerating = false;
      validateInput();
      chatInput.focus();
      scrollToBottom();
    }
  }

  // Append User Message to UI
  function appendUserMessage(text, attachment) {
    const row = document.createElement('div');
    row.className = 'message-row user';

    let attachmentHtml = '';
    if (attachment) {
      attachmentHtml = `<img src="data:${attachment.mime_type};base64,${attachment.data}" class="message-img-attachment" alt="첨부 이미지">`;
    }

    row.innerHTML = `
      <div class="message-content-wrapper">
        ${attachmentHtml}
        ${text ? `<div class="message-bubble">${escapeHtml(text).replace(/\n/g, '<br>')}</div>` : ''}
      </div>
      <div class="avatar user-avatar">
        ${escapeHtml(userDisplayName.textContent.trim().substring(0, 1) || 'U')}
      </div>
    `;

    chatMessagesContainer.appendChild(row);
    scrollToBottom();
  }

  // Append Gemini Placeholder
  function appendGeminiPlaceholder(id, modelName) {
    const row = document.createElement('div');
    row.className = 'message-row gemini';

    row.innerHTML = `
      <div class="avatar gemini-avatar">✦</div>
      <div class="message-content-wrapper">
        <div class="message-model-tag">${modelName}</div>
        <div class="message-bubble" id="${id}">
          <span class="streaming-cursor"></span>
        </div>
      </div>
    `;

    chatMessagesContainer.appendChild(row);
    scrollToBottom();
  }

  // Render Markdown with Code Block Copy Button and Grounding Citations
  function renderMarkdown(element, markdownText, isStreaming, groundingData) {
    if (!element) return;

    let html = '';
    if (window.marked) {
      html = marked.parse(markdownText);
    } else {
      html = escapeHtml(markdownText).replace(/\n/g, '<br>');
    }

    if (isStreaming) {
      html += '<span class="streaming-cursor"></span>';
    }

    // If grounding sources exist and streaming is finished (or available), append web sources
    if (groundingData && (groundingData.sources?.length > 0 || groundingData.queries?.length > 0)) {
      let sourcesHtml = '';
      if (groundingData.sources && groundingData.sources.length > 0) {
        sourcesHtml = groundingData.sources.map(s => `
          <a href="${escapeHtml(s.uri)}" target="_blank" rel="noopener noreferrer" class="source-item" title="${escapeHtml(s.title)}">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>
            <span>${escapeHtml(s.title)}</span>
          </a>
        `).join('');
      }

      let queriesHtml = '';
      if (groundingData.queries && groundingData.queries.length > 0) {
        queriesHtml = groundingData.queries.map(q => `
          <span class="query-chip">🔍 ${escapeHtml(q)}</span>
        `).join('');
      }

      html += `
        <div class="grounding-box">
          <div class="grounding-header">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1 4-10z"></path></svg>
            <span>Google 실시간 웹 검색 결과 기반</span>
          </div>
          ${queriesHtml ? `<div class="grounding-queries">${queriesHtml}</div>` : ''}
          ${sourcesHtml ? `<div class="grounding-sources">${sourcesHtml}</div>` : ''}
        </div>
      `;
    }

    element.innerHTML = html;

    // Attach copy buttons to <pre> code blocks
    const preBlocks = element.querySelectorAll('pre');
    preBlocks.forEach(pre => {
      if (pre.querySelector('.code-header')) return;

      const codeBlock = pre.querySelector('code');
      const langClass = codeBlock ? Array.from(codeBlock.classList).find(c => c.startsWith('language-')) : null;
      const langName = langClass ? langClass.replace('language-', '') : 'code';

      const header = document.createElement('div');
      header.className = 'code-header';
      header.innerHTML = `
        <span>${langName}</span>
        <button class="copy-code-btn" type="button">복사</button>
      `;

      const copyBtn = header.querySelector('.copy-code-btn');
      copyBtn.addEventListener('click', () => {
        const textToCopy = codeBlock ? codeBlock.innerText : pre.innerText;
        navigator.clipboard.writeText(textToCopy).then(() => {
          copyBtn.textContent = '복사됨!';
          setTimeout(() => { copyBtn.textContent = '복사'; }, 2000);
        });
      });

      pre.insertBefore(header, pre.firstChild);
    });
  }

  function scrollToBottom() {
    const mainContent = document.getElementById('main-content');
    mainContent.scrollTop = mainContent.scrollHeight;
  }

  function escapeHtml(str) {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
});
