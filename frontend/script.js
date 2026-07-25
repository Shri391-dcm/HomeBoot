// ===============================
// CONFIG
// ===============================

const CONFIG = {
    backendUrl: 'http://localhost:8000',
    mockDataPath: '../tests/',
};

// ===============================
// STATE
// ===============================

let isLoading = false;
let conversationState = {
    originalQuery: null,
    needsClarification: false,
    clarifyingQuestions: [],
    clarifyingAnswers: [],
    mockData: null,
};

// ===============================
// DOM ELEMENTS
// ===============================

const chatModal = document.getElementById('chat-modal');
const startChatBtn = document.getElementById('start-chat-btn');
const closeChatBtn = document.getElementById('close-chat-btn');
const chatMessages = document.getElementById('chat-messages');
const messageInput = document.getElementById('message-input');
const chatForm = document.getElementById('chat-form');
const loadingIndicator = document.getElementById('loading-indicator');
const citationModal = document.getElementById('citation-modal');
const citationTitle = document.getElementById('citation-title');
const citationBody = document.getElementById('citation-body');
const citationLink = document.getElementById('citation-link');
const modalClose = document.querySelector('.modal-close');

// ===============================
// INITIALIZATION
// ===============================

document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
});

// ===============================
// EVENT LISTENERS
// ===============================

function setupEventListeners() {
    startChatBtn.addEventListener('click', openChat);
    closeChatBtn.addEventListener('click', closeChat);
    chatForm.addEventListener('submit', handleSendMessage);
    modalClose.addEventListener('click', closeCitationModal);
    citationModal.addEventListener('click', (e) => {
        if (e.target === citationModal) closeCitationModal();
    });
}

// ===============================
// CHAT MODAL CONTROLS
// ===============================

function openChat() {
    chatModal.classList.add('show');
    messageInput.focus();
}

function closeChat() {
    chatModal.classList.remove('show');
}

// ===============================
// CHAT MESSAGE HANDLING
// ===============================

async function handleSendMessage(e) {
    e.preventDefault();

    const message = messageInput.value.trim();
    if (!message) return;

    // Check if we're answering clarifying questions
    if (conversationState.needsClarification) {
        handleClarifyingAnswer(message);
        messageInput.value = '';
        return;
    }

    // New question - start fresh
    addMessage(message, 'user');
    messageInput.value = '';
    setLoading(true);

    conversationState.originalQuery = message;
    conversationState.needsClarification = false;
    conversationState.clarifyingAnswers = [];

    try {
        // Call backend /query endpoint for full RAG pipeline
        const queryResponse = await fetch(`${CONFIG.backendUrl}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: message,
                top_k: 5
            }),
        });

        if (!queryResponse.ok) {
            throw new Error(`Query failed: ${queryResponse.status}`);
        }

        const queryResult = await queryResponse.json();
        console.log('Query result:', queryResult);

        // Display answer
        addMessage(queryResult.answer, 'assistant');
        
        // Display citations if available
        if (queryResult.citations && queryResult.citations.length > 0) {
            queryResult.citations.forEach(citation => {
                const citationText = `📎 ${citation.source || 'Source'}`;
                addMessage(citationText, 'citation', citation);
            });
        }

    } catch (error) {
        console.error('Error:', error);
        addMessage(`❌ Error: ${error.message}. Backend must be running on ${CONFIG.backendUrl}`, 'assistant');
    } finally {
        setLoading(false);
    }
}

function handleClarifyingAnswer(answer) {
    // Track user's answer to clarifying question
    conversationState.clarifyingAnswers.push(answer);
    addMessage(answer, 'user');

    // If we've answered all clarifying questions, proceed to answer
    if (conversationState.clarifyingAnswers.length >= conversationState.clarifyingQuestions.length) {
        submitClarifiedQuery();
    } else {
        // Show next clarifying question
        const nextQuestionIndex = conversationState.clarifyingAnswers.length;
        addMessage(`${conversationState.clarifyingQuestions[nextQuestionIndex]}`, 'assistant');
    }
}

async function submitClarifiedQuery() {
    setLoading(true);
    conversationState.needsClarification = false;

    try {
        // Call /query/followup with clarifying answers
        const response = await fetch(`${CONFIG.backendUrl}/query/followup`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                original_query: conversationState.originalQuery,
                clarifying_answers: conversationState.clarifyingAnswers,
                retrieved_passages: conversationState.mockData.retrieved_passages || [],
            }),
        });

        if (!response.ok) {
            throw new Error(`Backend error: ${response.status}`);
        }

        const result = await response.json();
        displayResponse(result);

    } catch (error) {
        console.error('Error:', error);
        addMessage(`❌ Error: ${error.message}`, 'assistant');
    } finally {
        setLoading(false);
    }
}

async function handleQueryResponse(message, mockData) {
    try {
        // Call backend API for direct answer
        const response = await fetch(`${CONFIG.backendUrl}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: message,
                retrieved_passages: mockData.retrieved_passages || [],
            }),
        });

        if (!response.ok) {
            throw new Error(`Backend error: ${response.status}`);
        }

        const result = await response.json();
        displayResponse(result);

    } catch (error) {
        console.error('Error:', error);
        addMessage(`❌ Error: ${error.message}`, 'assistant');
    }
}

function showClarifyingQuestions(questions) {
    const questionsHtml = `<div style="padding: 8px; background: #f0f4f8; border-left: 3px solid #1565F5;">
        <strong>I need a bit more info:</strong>
        <ul style="margin: 8px 0; padding-left: 20px;">
            ${questions.map(q => `<li style="margin: 4px 0; font-size: 14px;">${q}</li>`).join('')}
        </ul>
        <div style="margin-top: 12px; font-size: 14px; font-style: italic; color: #555;">
            Please provide the details above ↑
        </div>
    </div>`;
    addMessage(questionsHtml, 'assistant', true);
}

async function loadMockData(question = '') {
    // NEW: Call real retrieval API instead of mock data
    try {
        const retrieveResponse = await fetch(`${CONFIG.backendUrl}/retrieve`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: question,
                top_k: 5
            }),
        });
        
        if (retrieveResponse.ok) {
            const retrieveData = await retrieveResponse.json();
            console.log('Retrieved passages from real pipeline:', retrieveData);
            
            // Convert to same format as mock data for backward compatibility
            return {
                query: retrieveData.query,
                retrieved_passages: retrieveData.passages
            };
        }
    } catch (error) {
        console.error('Real retrieval failed:', error);
    }
    
    // Fallback: Return default mock drainage data
    return {
        "query": "my washing machine won't drain",
        "retrieved_passages": [
            {
                "rank": 1,
                "chunk_id": "whirlpool_washer_drain_1",
                "text": "If water won't drain from your washer, first check the drain pump filter for clogs. Drain filter clogs are one of the most common causes of drainage issues. The filter is usually located at the bottom front of the machine.",
                "source_url": "https://www.whirlpool.com/en-us/support/washers/drainage",
                "heading_path": "Troubleshooting > Drainage Issues",
                "page_type": "support_page",
                "effective_date": "2024-07-01",
                "pre_rerank_score": 0.87,
                "post_rerank_score": 0.95
            },
            {
                "rank": 2,
                "chunk_id": "whirlpool_washer_hoses_1",
                "text": "Check the inlet hoses for kinks or damage that might restrict water flow. Kinked hoses can prevent proper drainage and water fill. Straighten any bent hoses and replace if damaged.",
                "source_url": "https://www.whirlpool.com/en-us/support/washers/hoses",
                "heading_path": "Maintenance > Inlet Hoses",
                "page_type": "support_page",
                "effective_date": "2024-06-15",
                "pre_rerank_score": 0.82,
                "post_rerank_score": 0.88
            },
            {
                "rank": 3,
                "chunk_id": "ge_washer_drain_1",
                "text": "For GE washers, drainage problems often stem from a blocked drain hose. Remove the drain hose from the back of the machine and check for blockages. You can use a plumbing snake to clear any debris.",
                "source_url": "https://www.ge.com/appliances/support/washers/drainage",
                "heading_path": "Troubleshooting > Drain Issues",
                "page_type": "support_page",
                "effective_date": "2024-06-20",
                "pre_rerank_score": 0.79,
                "post_rerank_score": 0.84
            }
        ]
    };
}

function displayResponse(result) {
    // Handle safety flag
    if (result.safety_flag) {
        const html = `<strong>🚨 Safety Alert:</strong> ${result.safety_message}`;
        addMessage(html, 'assistant', true);
        return;
    }

    // Handle refusal
    if (result.refusal) {
        const html = `<strong>⚠️ Cannot answer:</strong> ${result.refusal_reason}`;
        addMessage(html, 'assistant', true);
        return;
    }

    // Add answer
    if (result.answer) {
        addMessage(result.answer, 'assistant');
    }

    // Add citations
    if (result.citations && result.citations.length > 0) {
        const citationsHtml = result.citations
            .map(c => `<small style="display: block; margin-top: 8px; cursor: pointer; color: #1565F5;" onclick="showCitationModal(${JSON.stringify(c).replace(/"/g, '&quot;')})">📌 Source: ${c.source_url}</small>`)
            .join('');
        addMessage(citationsHtml, 'assistant', true);
    }
}

function addMessage(content, role, isHtml = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${role}`;

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';

    if (isHtml) {
        bubble.innerHTML = content;
    } else {
        const p = document.createElement('p');
        p.textContent = content;
        bubble.appendChild(p);
    }

    messageDiv.appendChild(bubble);
    chatMessages.appendChild(messageDiv);

    // Auto-scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ===============================
// UTILITY FUNCTIONS
// ===============================

function setLoading(loading) {
    isLoading = loading;
    loadingIndicator.style.display = loading ? 'flex' : 'none';
    messageInput.disabled = loading;
}

// ===============================
// CITATION MODAL
// ===============================

function showCitationModal(citation) {
    citationTitle.textContent = citation.heading_path || 'Source';
    citationBody.textContent = citation.quote || citation.text || 'No content available';
    citationLink.href = citation.source_url || '#';
    citationLink.textContent = 'View full page →';
    citationModal.classList.add('show');
}

function closeCitationModal() {
    citationModal.classList.remove('show');
}

// ===============================
// KEYBOARD SHORTCUTS
// ===============================

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        if (citationModal.classList.contains('show')) {
            closeCitationModal();
        }
    }
});
