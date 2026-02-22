/**
 * ParkSight Business Advisor Chatbot
 * Handles chat interface and RAG API communication
 */

const API_URL = 'http://localhost:5001';
const CHAT_STORAGE_KEY = 'parksight_chat_history';

// DOM elements
const chatToggle = document.getElementById('chatbot-toggle');
const chatPanel = document.getElementById('chatbot-panel');
const chatClose = document.getElementById('chatbot-close');
const chatClear = document.getElementById('chatbot-clear');
const chatMessages = document.getElementById('chatbot-messages');
const chatInput = document.getElementById('chatbot-input');
const chatSend = document.getElementById('chatbot-send');
const suggestionBtns = document.querySelectorAll('.suggestion-btn');

// State
let conversationHistory = [];

/**
 * Initialize chatbot on page load
 */
function initChatbot() {
    // Load conversation history from localStorage
    loadChatHistory();

    // Clear any old map markers on fresh load
    if (typeof clearRecommendations === 'function') {
        clearRecommendations();
    }

    // Event listeners
    chatToggle.addEventListener('click', openChat);
    chatClose.addEventListener('click', closeChat);
    chatClear.addEventListener('click', clearChatHistory);
    chatSend.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    suggestionBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const query = btn.dataset.query;
            sendMessageWithText(query);
        });
    });

    // Check API health
    checkHealth();
}

/**
 * Open chat panel
 */
function openChat() {
    chatPanel.classList.add('open');
    chatToggle.style.display = 'none';
    chatInput.focus();
}

/**
 * Close chat panel
 */
function closeChat() {
    chatPanel.classList.remove('open');
    chatToggle.style.display = 'flex';
}

/**
 * Send message to chatbot with provided text
 */
async function sendMessageWithText(text) {
    const message = text.trim();
    if (!message) return;

    // Add user message to UI
    addMessage(message, 'user');

    // Show typing indicator
    const typingId = showTypingIndicator();

    // Build conversation history for API (convert to Claude format)
    const apiHistory = conversationHistory
        .filter(msg => msg.role !== 'user' || msg.content !== message) // Exclude the message we just added
        .map(msg => ({
            role: msg.role === 'user' ? 'user' : 'assistant',
            content: msg.content
        }));

    try {
        // Call API with history
        const response = await fetch(`${API_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message,
                history: apiHistory
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        // Remove typing indicator
        removeTypingIndicator(typingId);

        // Add AI response
        addMessage(data.response, 'ai');

        // Process recommendation and highlight on map
        processChatbotRecommendation(data.response, message);

        // Save to history
        saveChatHistory();

    } catch (error) {
        console.error('Chat error:', error);

        // Remove typing indicator
        removeTypingIndicator(typingId);

        // Show error message
        addMessage(
            "I'm having trouble connecting to the advisor service. Please make sure the RAG API is running on port 5001.",
            'ai',
            true
        );
    }
}

/**
 * Send message to chatbot
 */
async function sendMessage() {
    const message = chatInput.value.trim();
    if (!message) return;

    // Clear input
    chatInput.value = '';

    // Use the common send function
    await sendMessageWithText(message);
}

/**
 * Add message to chat UI
 */
function addMessage(text, role, isError = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `chatbot-message ${role}-message`;

    if (role === 'user') {
        messageDiv.innerHTML = `
            <div class="message-avatar">You</div>
            <div class="message-content">${escapeHtml(text)}</div>
        `;
    } else {
        messageDiv.innerHTML = `
            <div class="message-avatar">AI</div>
            <div class="message-content ${isError ? 'error' : ''}">${isError ? escapeHtml(text) : formatAiMessage(text)}</div>
        `;
    }

    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Store in conversation history (exclude errors)
    if (!isError) {
        conversationHistory.push({ role, content: text });
    }
}

/**
 * Show typing indicator
 */
function showTypingIndicator() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'chatbot-message ai-message typing-indicator';
    typingDiv.id = `typing-${Date.now()}`;
    typingDiv.innerHTML = `
        <div class="message-avatar">AI</div>
        <div class="message-content">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
        </div>
    `;

    chatMessages.appendChild(typingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return typingDiv.id;
}

/**
 * Remove typing indicator
 */
function removeTypingIndicator(id) {
    const indicator = document.getElementById(id);
    if (indicator) {
        indicator.remove();
    }
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Format AI response text into clean HTML
 * Handles bold, bullets, headers, and paragraphs
 */
function formatAiMessage(text) {
    // Escape HTML first, then apply inline formatting across the entire string
    // so **bold** markers are resolved before we split into lines
    const inlined = applyInline(escapeHtml(text));
    const lines = inlined.split('\n');
    let html = '';
    let inList = false;
    let listTag = 'ul';

    lines.forEach(raw => {
        const line = raw.trim();

        if (!line) {
            if (inList) { html += `</${listTag}>` ; inList = false; }
            return;
        }

        // Heading: ## or #
        if (/^#{1,3}\s/.test(line)) {
            if (inList) { html += `</${listTag}>`; inList = false; }
            html += `<div class="chat-heading">${line.replace(/^#{1,3}\s+/, '')}</div>`;
            return;
        }

        // Bullet point
        if (/^[•\-]\s/.test(line)) {
            if (!inList || listTag !== 'ul') {
                if (inList) html += `</${listTag}>`;
                html += '<ul class="chat-list">'; inList = true; listTag = 'ul';
            }
            html += `<li>${line.replace(/^[•\-]\s+/, '')}</li>`;
            return;
        }

        // Numbered list
        if (/^\d+\.\s/.test(line)) {
            if (!inList || listTag !== 'ol') {
                if (inList) html += `</${listTag}>`;
                html += '<ol class="chat-list">'; inList = true; listTag = 'ol';
            }
            html += `<li>${line.replace(/^\d+\.\s+/, '')}</li>`;
            return;
        }

        if (inList) { html += `</${listTag}>`; inList = false; }
        html += `<p>${line}</p>`;
    });

    if (inList) html += `</${listTag}>`;
    return html;
}

// Apply inline formatting: **bold**, *italic*, `code`
function applyInline(text) {
    return text
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*([^*\n]+?)\*/g, '<em>$1</em>')
        .replace(/`(.+?)`/g,        '<code class="chat-code">$1</code>');
}

/**
 * Save chat history to localStorage
 */
function saveChatHistory() {
    try {
        localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(conversationHistory));
    } catch (error) {
        console.warn('Failed to save chat history:', error);
    }
}

/**
 * Load chat history from localStorage
 */
function loadChatHistory() {
    try {
        const stored = localStorage.getItem(CHAT_STORAGE_KEY);
        if (stored) {
            conversationHistory = JSON.parse(stored);

            // Restore messages to UI (skip the initial AI greeting)
            conversationHistory.forEach(msg => {
                if (msg.content !== "Hi! I'm your Atlanta retail site advisor. Tell me what kind of business you want to open and I'll find the best spots based on parking data and neighborhood intelligence.") {
                    addMessageWithoutHistory(msg.content, msg.role);
                }
            });
        }
    } catch (error) {
        console.warn('Failed to load chat history:', error);
    }
}

/**
 * Add message to UI without updating history
 */
function addMessageWithoutHistory(text, role) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `chatbot-message ${role}-message`;

    if (role === 'user') {
        messageDiv.innerHTML = `
            <div class="message-avatar">You</div>
            <div class="message-content">${escapeHtml(text)}</div>
        `;
    } else {
        messageDiv.innerHTML = `
            <div class="message-avatar">AI</div>
            <div class="message-content">${formatAiMessage(text)}</div>
        `;
    }

    chatMessages.appendChild(messageDiv);
}

/**
 * Clear chat history
 */
function clearChatHistory() {
    conversationHistory = [];
    localStorage.removeItem(CHAT_STORAGE_KEY);

    // Clear UI and restore initial greeting
    chatMessages.innerHTML = `
        <div class="chatbot-message ai-message">
            <div class="message-avatar">AI</div>
            <div class="message-content">
                Hi! I'm your Atlanta retail site advisor. Tell me what kind of business you want to open and I'll find the best spots based on parking data and neighborhood intelligence.
            </div>
        </div>
    `;

    // Clear map recommendations
    if (typeof clearRecommendations === 'function') {
        clearRecommendations();
    }
}

/**
 * Check API health
 */
async function checkHealth() {
    try {
        const response = await fetch(`${API_URL}/health`);
        const data = await response.json();

        if (data.vector_db !== 'connected') {
            console.warn('Vector DB not connected');
        }
    } catch (error) {
        console.warn('RAG API not reachable:', error);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initChatbot);
