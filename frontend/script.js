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
    inConversation: false,
    conversationHistory: [],  // Track full conversation for context-aware retrieval
    activeApplianceCategory: null,
    selectedBrand: null,
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
    resetChat();
}

function resetChat() {
    conversationState = {
        originalQuery: null,
        needsClarification: false,
        clarifyingQuestions: [],
        clarifyingAnswers: [],
        mockData: null,
        inConversation: false,
        conversationHistory: [],
        activeApplianceCategory: null,
        selectedBrand: null,
    };
    chatMessages.replaceChildren();
    addMessage("Hi! I'm ApplianceAI. Ask me anything about your Whirlpool or GE appliances!", 'assistant');
    messageInput.value = '';
    setLoading(false);
}

function getApplianceCategory(message) {
    const normalizedMessage = message.toLowerCase();
    if (/\b(fridge|fidge|refrigerator|refrgerator|refrigirator|freezer)\b/.test(normalizedMessage)) {
        return 'refrigerator';
    }
    if (/\b(washer|washing machine)\b/.test(normalizedMessage)) {
        return 'washer';
    }
    if (/\bdishwasher\b/.test(normalizedMessage)) {
        return 'dishwasher';
    }
    if (/\bdryer\b/.test(normalizedMessage)) {
        return 'dryer';
    }
    return null;
}

function getSupportedBrand(message) {
    const normalizedMessage = message.toLowerCase();
    if (/\bwhirlpool\b/.test(normalizedMessage)) {
        return 'Whirlpool';
    }
    if (/\b(ge|ge appliances|general electric)\b/.test(normalizedMessage)) {
        return 'GE Appliances';
    }
    return null;
}

function startsNewApplianceIssue(message) {
    const appliancePattern = /\b(fridge|fidge|refrigerator|refrgerator|refrigirator|freezer|washer|washing machine|dishwasher|dryer)\b/i;
    const questionPattern = /\b(how|what|when|where|why|can|should|is|are|do|does|will|help|move|install|clean|repair|replace|prepare|safe|safely|not working|not cooling|not draining|not starting|leaking|broken|problem|issue)\b/i;
    const wordCount = message.split(/\s+/).length;

    // Short answers such as "yes", "no", and "cool" stay in the current
    // diagnosis. A substantive appliance question starts its own topic.
    return wordCount >= 3 && appliancePattern.test(message) && questionPattern.test(message);
}

function changesApplianceCategory(message) {
    const messageCategory = getApplianceCategory(message);
    return (
        messageCategory !== null
        && conversationState.activeApplianceCategory !== null
        && messageCategory !== conversationState.activeApplianceCategory
    );
}

// ===============================
// CHAT MESSAGE HANDLING
// ===============================

async function handleSendMessage(e) {
    e.preventDefault();

    const message = messageInput.value.trim();
    if (!message) return;

    // Check if we're answering clarifying questions (brand/model)
    if (conversationState.needsClarification) {
        handleClarifyingAnswer(message);
        messageInput.value = '';
        return;
    }

    // A full appliance problem statement starts a new diagnosis, even if a prior
    // conversation is still open in the chat window.
    if (
        conversationState.inConversation
        && startsNewApplianceIssue(message)
        && changesApplianceCategory(message)
    ) {
        conversationState.inConversation = false;
        conversationState.conversationHistory = [];
        conversationState.activeApplianceCategory = null;
        conversationState.selectedBrand = null;
    }

    // Check if we're in an active diagnostic conversation
    if (conversationState.inConversation) {
        addMessage(message, 'user');
        messageInput.value = '';
        setLoading(true);

        // Add user message to history
        conversationState.conversationHistory.push({
            role: 'user',
            content: message
        });

        try {
            // Send follow-up response directly to /query with full conversation history
            const response = await fetch(`${CONFIG.backendUrl}/query`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: message,
                    top_k: 5,
                    conversation_history: conversationState.conversationHistory
                }),
            });

            if (!response.ok) {
                throw new Error(`Query failed: ${response.status}`);
            }

            const result = await response.json();
            displayResponse(result);
            
            // Add assistant response to history
            conversationState.conversationHistory.push({
                role: 'assistant',
                content: result.answer
            });

        } catch (error) {
            console.error('Error:', error);
            addMessage(`❌ Error: ${error.message}`, 'assistant');
        } finally {
            setLoading(false);
        }
        return;
    }

    // New question - start fresh conversation
    addMessage(message, 'user');
    messageInput.value = '';
    setLoading(true);

    conversationState.originalQuery = message;
    conversationState.needsClarification = false;
    conversationState.clarifyingAnswers = [];
    conversationState.inConversation = false;
    conversationState.conversationHistory = [];  // Reset history for new conversation
    conversationState.activeApplianceCategory = getApplianceCategory(message);
    conversationState.selectedBrand = null;
    
    // Add initial user query to history
    conversationState.conversationHistory.push({
        role: 'user',
        content: message
    });

    try {
        // First, check if query needs clarification
        const clarifyResponse = await fetch(`${CONFIG.backendUrl}/clarify`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: message,
                top_k: 5
            }),
        });

        if (!clarifyResponse.ok) {
            throw new Error(`Clarify check failed: ${clarifyResponse.status}`);
        }

        const clarifyResult = await clarifyResponse.json();
        console.log('Clarify result:', clarifyResult);

        if (clarifyResult.needs_clarification) {
            // Collect product details before asking about the issue.
            addMessage(clarifyResult.message, 'assistant');
            
            // Show suggestions if available
            if (clarifyResult.suggestions && clarifyResult.suggestions.length > 0) {
                const suggestionText = `Common brands: ${clarifyResult.suggestions.join(', ')}`;
                addMessage(suggestionText, 'assistant');
            }
            
            conversationState.needsClarification = true;
            conversationState.clarifyingQuestions = [{
                question: clarifyResult.message,
                fieldName: 'product_specs'
            }, {
                question: 'Thanks. What problem are you experiencing with the appliance?',
                fieldName: 'issue'
            }];
            setLoading(false);
            return;
        }

        // Query is clear enough - proceed with normal query with conversation history
        const queryResponse = await fetch(`${CONFIG.backendUrl}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: message,
                top_k: 5,
                conversation_history: conversationState.conversationHistory
            }),
        });

        if (!queryResponse.ok) {
            throw new Error(`Query failed: ${queryResponse.status}`);
        }

        const queryResult = await queryResponse.json();
        console.log('Query result:', queryResult);

        // Mark that we're in active conversation now (so follow-ups don't call /clarify again)
        conversationState.inConversation = true;

        // Add assistant response to conversation history
        conversationState.conversationHistory.push({
            role: 'assistant',
            content: queryResult.answer
        });

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
    const isBrandAnswer = conversationState.clarifyingAnswers.length === 0;
    const selectedBrand = getSupportedBrand(answer);

    if (isBrandAnswer && !selectedBrand) {
        addMessage(answer, 'user');
        addMessage('Please choose Whirlpool or GE Appliances.', 'assistant');
        return;
    }

    // Track user's answer to clarifying question
    conversationState.clarifyingAnswers.push(answer);
    addMessage(answer, 'user');

    if (isBrandAnswer) {
        conversationState.selectedBrand = selectedBrand;
    }

    // Keep product details and the reported issue available for later retrieval.
    conversationState.conversationHistory.push({
        role: 'user',
        content: answer
    });

    // If we've answered all clarifying questions, proceed to answer
    if (conversationState.clarifyingAnswers.length >= conversationState.clarifyingQuestions.length) {
        submitClarifiedQuery();
    } else {
        // Show next clarifying question
        const nextQuestionIndex = conversationState.clarifyingAnswers.length;
        addMessage(conversationState.clarifyingQuestions[nextQuestionIndex].question, 'assistant');
    }
}

async function submitClarifiedQuery() {
    setLoading(true);
    conversationState.needsClarification = false;
    conversationState.inConversation = true;  // Mark that we're now in active diagnostic conversation

    try {
        // Begin retrieval only after product specifications and issue are collected.
        const productSpecs = conversationState.clarifyingAnswers[0] || '';
        const issue = conversationState.clarifyingAnswers[1] || conversationState.originalQuery;
        const enhancedQuery = `${issue} (${productSpecs})`;
        
        // Call /query with enhanced query and conversation history
        const response = await fetch(`${CONFIG.backendUrl}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: enhancedQuery,
                top_k: 5,
                conversation_history: conversationState.conversationHistory
            }),
        });

        if (!response.ok) {
            throw new Error(`Backend error: ${response.status}`);
        }

        const result = await response.json();
        
        // Add assistant response to conversation history
        conversationState.conversationHistory.push({
            role: 'assistant',
            content: result.answer
        });
        
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
