// State Management
let currentState = {
    activeCharacter: null,
    activeChat: null,
    messages: [],
    view: 'my' // 'recent', 'my', 'search'
};

// DOM Elements
const elements = {
    myUsername: document.getElementById('myUsername'),
    myAvatar: document.getElementById('myAvatar'),
    characterList: document.getElementById('characterList'),
    messagesContainer: document.getElementById('messagesContainer'),
    activeCharAvatar: document.getElementById('activeCharAvatar'),
    activeCharName: document.getElementById('activeCharName'),
    activeCharTitle: document.getElementById('activeCharTitle'),
    messageInput: document.getElementById('messageInput'),
    sendBtn: document.getElementById('sendBtn'),
    charSearchInput: document.getElementById('charSearchInput'),
    navRecent: document.getElementById('navRecent'),
    navMy: document.getElementById('navMy'),
    navSearch: document.getElementById('navSearch'),
    navCreate: document.getElementById('navCreate'),
    createModal: document.getElementById('createModal'),
    createCharForm: document.getElementById('createCharForm'),
    closeModal: document.querySelector('.close-modal'),
    newChatBtn: document.getElementById('newChatBtn')
};

// Initialize
async function init() {
    await fetchUserProfile();
    await loadCharacters('my');
    setupEventListeners();
}

// Event Listeners
function setupEventListeners() {
    // Navigation
    // elements.navRecent.addEventListener('click', () => switchView('recent'));
    elements.navMy.addEventListener('click', () => switchView('my'));
    // elements.navSearch.addEventListener('click', () => switchView('search'));

    // Search
    let searchTimeout;
    elements.charSearchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        if (currentState.view === 'search') {
            searchTimeout = setTimeout(() => {
                loadCharacters('search', e.target.value);
            }, 500);
        } else {
            // Local filter for current list
            filterLocalCharacters(e.target.value);
        }
    });

    // Message Input
    elements.messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    elements.sendBtn.addEventListener('click', sendMessage);

    // Modal
    elements.navCreate.addEventListener('click', () => elements.createModal.style.display = 'flex');
    elements.closeModal.addEventListener('click', () => elements.createModal.style.display = 'none');
    window.addEventListener('click', (e) => {
        if (e.target === elements.createModal) elements.createModal.style.display = 'none';
    });

    elements.createCharForm.addEventListener('submit', handleCreateCharacter);

    // Refresh Chat
    elements.newChatBtn.addEventListener('click', () => {
        if (currentState.activeCharacter) {
            startChat(currentState.activeCharacter.character_id);
        }
    });
}

// API Functions
async function fetchUserProfile() {
    try {
        const response = await fetch('/me');
        const data = await response.json();
        elements.myUsername.textContent = `@${data.username}`;
        if (data.avatar_url) elements.myAvatar.src = data.avatar_url;
    } catch (error) {
        console.error('Error fetching profile:', error);
    }
}

async function loadCharacters(type, query = '') {
    elements.characterList.innerHTML = '<div class="loading-spinner"></div>';

    let url = '/characters/recent';
    if (type === 'my') url = '/characters/my';
    if (type === 'search') url = `/characters/search?query=${encodeURIComponent(query || 'AI')}`;

    try {
        const response = await fetch(url);
        const characters = await response.json();
        renderCharacterList(characters);
    } catch (error) {
        console.error('Error loading characters:', error);
        elements.characterList.innerHTML = '<p class="error">Failed to load characters</p>';
    }
}

function renderCharacterList(characters) {
    elements.characterList.innerHTML = '';
    if (characters.length === 0) {
        elements.characterList.innerHTML = '<p class="empty-msg">No characters found</p>';
        return;
    }

    characters.forEach(char => {
        const item = document.createElement('div');
        item.className = 'char-item';
        if (currentState.activeCharacter?.character_id === char.character_id) {
            item.classList.add('active');
        }

        const avatarSeed = char.name.replace(/\s+/g, '');
        item.innerHTML = `
            <img src="https://api.dicebear.com/6.x/bottts/svg?seed=${avatarSeed}" alt="${char.name}" class="item-avatar">
            <div class="item-info">
                <span class="item-name">${char.name}</span>
                <span class="item-title">${char.title || '@' + (char.author_username || 'unknown')}</span>
            </div>
        `;

        item.onclick = () => selectCharacter(char);
        elements.characterList.appendChild(item);
    });
}

async function selectCharacter(char) {
    currentState.activeCharacter = char;

    // Update active state in list
    document.querySelectorAll('.char-item').forEach(el => el.classList.remove('active'));
    event.currentTarget.classList.add('active');

    // Update Header
    elements.activeCharName.textContent = char.name;
    elements.activeCharTitle.textContent = char.title || 'Conversation';
    const avatarSeed = char.name.replace(/\s+/g, '');
    elements.activeCharAvatar.src = `https://api.dicebear.com/6.x/bottts/svg?seed=${avatarSeed}`;

    // Clear messages and show welcome/start chat
    elements.messagesContainer.innerHTML = '<div class="loading-spinner"></div>';
    elements.messageInput.disabled = true;
    elements.sendBtn.disabled = true;

    await startChat(char.character_id);
}

async function startChat(character_id) {
    try {
        const response = await fetch(`/chat/create?character_id=${character_id}`, { method: 'POST' });
        const data = await response.json();

        currentState.activeChat = data.chat_id;
        currentState.messages = [{
            author_name: data.character_name,
            text: data.greeting
        }];

        renderMessages();

        elements.messageInput.disabled = false;
        elements.sendBtn.disabled = false;
        elements.messageInput.focus();
    } catch (error) {
        console.error('Error starting chat:', error);
        addMessage('system', 'Failed to start chat session. Please try again.');
    }
}

async function sendMessage() {
    const text = elements.messageInput.value.trim();
    if (!text || !currentState.activeChat) return;

    elements.messageInput.value = '';
    elements.messageInput.style.height = 'auto';

    // Add user message locally
    const userMsg = { author_name: 'You', text: text, isUser: true };
    currentState.messages.push(userMsg);
    renderMessages();

    // Create a temporary message bubble for the bot response
    const botMsgDiv = addMessage('bot', '...', false, currentState.activeCharacter?.name);
    const bubble = botMsgDiv.querySelector('.msg-bubble');

    try {
        const response = await fetch('/chat/send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                character_id: currentState.activeCharacter.character_id,
                chat_id: currentState.activeChat,
                message: text
            })
        });

        if (!response.ok) throw new Error('Failed to send message');

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullText = '';

        bubble.textContent = ''; // Clear typing indicator

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            // In PyCharacterAI streaming, each yield is usually the updated full text
            // We'll update the bubble with the latest received text
            fullText += chunk;
            bubble.textContent = fullText;
            scrollToBottom();
        }

        // Add the final message to state
        currentState.messages.push({
            author_name: currentState.activeCharacter.name,
            text: fullText
        });

    } catch (error) {
        console.error('Error sending message:', error);
        botMsgDiv.remove();
        addMessage('system', 'Error: Could not reach the character.');
    }
}

function renderMessages() {
    elements.messagesContainer.innerHTML = '';
    currentState.messages.forEach(msg => {
        addMessage(msg.isUser ? 'user' : 'bot', msg.text, false, msg.author_name);
    });
    scrollToBottom();
}

function addMessage(type, text, isTemporary = false, name = '') {
    const div = document.createElement('div');
    div.className = `message ${type}`;

    div.innerHTML = `
        <div class="msg-bubble">${text}</div>
        <div class="msg-info">${name || (type === 'user' ? 'You' : currentState.activeCharacter?.name)}</div>
    `;

    elements.messagesContainer.appendChild(div);
    scrollToBottom();
    return div;
}

function scrollToBottom() {
    elements.messagesContainer.scrollTop = elements.messagesContainer.scrollHeight;
}

function switchView(view) {
    currentState.view = view;

    // UI Update
    [elements.navRecent, elements.navMy, elements.navSearch].forEach(el => {
        if (el) el.classList.remove('active');
    });

    if (view === 'recent' && elements.navRecent) elements.navRecent.classList.add('active');
    if (view === 'my' && elements.navMy) elements.navMy.classList.add('active');
    if (view === 'search') {
        if (elements.navSearch) elements.navSearch.classList.add('active');
        elements.charSearchInput.placeholder = 'Search globally...';
    } else {
        elements.charSearchInput.placeholder = 'Filter results...';
    }

    loadCharacters(view);
}

function filterLocalCharacters(query) {
    const items = elements.characterList.querySelectorAll('.char-item');
    const q = query.toLowerCase();

    items.forEach(item => {
        const name = item.querySelector('.item-name').textContent.toLowerCase();
        if (name.includes(q)) {
            item.style.display = 'flex';
        } else {
            item.style.display = 'none';
        }
    });
}

async function handleCreateCharacter(e) {
    e.preventDefault();
    const formData = new FormData(elements.createCharForm);
    const payload = Object.fromEntries(formData.entries());

    try {
        const response = await fetch('/characters/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            const data = await response.json();
            elements.createModal.style.display = 'none';
            elements.createCharForm.reset();
            alert('Character created successfully!');
            switchView('my');
        } else {
            const error = await response.json();
            alert('Error: ' + (error.detail || 'Failed to create character'));
        }
    } catch (error) {
        console.error('Error creating character:', error);
        alert('Failed to create character. Check console.');
    }
}

// Auto-expand textarea
elements.messageInput.addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
});

// Run Init
init();
