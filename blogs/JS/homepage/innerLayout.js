// import config from './config.js';

// Initial animations
gsap.to(".title", {
    opacity: 1,
    y: 0,
    duration: 0.8,
    ease: "power3.out"
});

gsap.to(".search-container", {
    opacity: 1,
    y: 0,
    duration: 0.8,
    delay: 0.3,
    ease: "power3.out"
});

// Add animation to quick-actions
gsap.from(".quick-actions", { opacity: 0, y: 50, duration: 1 });

// Search bar hover animation
const searchWrapper = document.querySelector('.search-bar-wrapper');

searchWrapper.addEventListener('mouseenter', () => {
    gsap.to(searchWrapper, {
        boxShadow: "0 6px 25px rgba(0, 0, 0, 0.15)",
        duration: 0.3
    });
});

searchWrapper.addEventListener('mouseleave', () => {
    gsap.to(searchWrapper, {
        boxShadow: "0 4px 15px rgba(0, 0, 0, 0.1)",
        duration: 0.3
    });
});

// Quick-action button functionality
document.querySelectorAll('.quick-action').forEach(button => {
    button.addEventListener('click', () => {
        const text = button.textContent.trim();
        searchBar.value = `/${text}`;
    });
});

// History panel toggle
const historyIcon = document.querySelector('.history-icon');
const historyPanel = document.querySelector('.history-panel');
const closeIcon = document.querySelector('.close-icon');
let isHistoryOpen = false;

document.addEventListener('DOMContentLoaded', () => {
    const savedHistory = JSON.parse(localStorage.getItem('searchHistory')) || [];
    savedHistory.forEach(item => {
        const historyItem = document.createElement('div');
        historyItem.classList.add('history-item');
        historyItem.innerHTML = `<span class="history-text">${item}</span><i class="fa-regular fa-trash-can icon delete-icon"></i>`;
        historyPanel.appendChild(historyItem);
    });
});

function toggleHistory() {
    isHistoryOpen = !isHistoryOpen;
    gsap.to(historyPanel, {
        scaleY: isHistoryOpen ? 1 : 0,
        opacity: isHistoryOpen ? 1 : 0,
        duration: 0.4,
        ease: "power3.inOut"
    });

    if (isHistoryOpen) {
        gsap.to(historyPanel, { zIndex: 2 });
        gsap.to(resultBox, { zIndex: 1 });
        gsap.to('.quick-actions', { opacity: 0, duration: 0.4, onComplete: () => document.querySelector('.quick-actions').classList.add('hidden') });
    } else {
        gsap.to(historyPanel, { zIndex: 1 });
        gsap.to(resultBox, { zIndex: 2 });
        document.querySelector('.quick-actions').classList.remove('hidden');
        gsap.to('.quick-actions', { opacity: 1, duration: 0.4 });
    }
}

historyIcon.addEventListener('click', toggleHistory);
closeIcon.addEventListener('click', toggleHistory);

// Icon hover animations
document.querySelectorAll('.icon').forEach(icon => {
    icon.addEventListener('mouseenter', () => {
        gsap.to(icon, {
            scale: 1.1,
            duration: 0.3
        });
    });

    icon.addEventListener('mouseleave', () => {
        gsap.to(icon, {
            scale: 1,
            duration: 0.3
        });
    });
});

// Result box animation
const searchBar = document.querySelector('.search-bar');
const resultBox = document.querySelector('.result-box');
const resultContent = document.querySelector('.result-content');
const dots = document.querySelectorAll('.dot');

// Animate dots
function animateDots() {
    gsap.to(dots, {
        opacity: 1,
        stagger: 0.2,
        repeat: -1,
        yoyo: true,
        duration: 0.5
    });
}

// Gemini API integration
async function fetchGeminiResponse(prompt) {
    const API_KEY = '';
    // const API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent';

    try {
        const response = await fetch(`${API_URL}?key=${API_KEY}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                contents: [{ parts: [{ text: prompt }] }]
            })
        });

        if (!response.ok) {
            throw new Error('API request failed');
        }

        const data = await response.json();
        return data.candidates[0].content.parts[0].text;
    } catch (error) {
        console.error('Error:', error);
        throw error;
    }
}

async function showResult(userPrompt) {
    resultBox.style.display = 'block';
    gsap.to(resultBox, {
        opacity: 1,
        y: 0,
        duration: 0.5,
        ease: "power3.out"
    });
    gsap.to('.quick-actions', { opacity: 0, duration: 0.4, onComplete: () => document.querySelector('.quick-actions').classList.add('hidden') });
    animateDots();

    try {
        const response = await fetchGeminiResponse(userPrompt);
        let formattedResponse = response;

        // Check if the prompt is code-related
        const codeKeywords = ['code', 'script', 'function', 'algorithm', 'program', 'syntax'];
        const isCodeRelated = codeKeywords.some(keyword => userPrompt.toLowerCase().includes(keyword));

        if (isCodeRelated) {
            // Detect code blocks and format them
            formattedResponse = formattedResponse.replace(/HTML\s*```html\s*([\s\S]*?)```/g, '<div class="code-block"><pre><code class="language-html">$1</code></pre></div>')
                .replace(/CSS\s*```css\s*([\\s\S]*?)```/g, '<div class="code-block"><pre><code class="language-css">$1</code></pre></div>')
                .replace(/JavaScript\s*```javascript\s*([\s\S]*?)```/g, '<div class="code-block"><pre><code class="language-javascript">$1</code></pre></div>')
                .replace(/```([\s\S]*?)```/g, '<div class="code-block"><pre><code class="language-generic">$1</code></pre></div>'); // Generic code block

        } else {
            // Format the response with bold and link tags
            formattedResponse = response
                .replace(/\*(.*?)\*/g, '<b>$1</b>')
                .replace(/(https?:\/\/[^\s]+)/g, '<li><a href="$1" target="_blank" class="ai-link">$1</a></li>');
        }

        resultContent.innerHTML = `<b>${userPrompt}</b><ul>${formattedResponse}</ul>`;
        gsap.to('.generating', { display: 'none', duration: 0 });
        gsap.to(resultContent, { opacity: 1, duration: 0.5 });

        // Save to history
        const historyItem = document.createElement('div');
        historyItem.classList.add('history-item');
        historyItem.innerHTML = `<span class="history-text">${userPrompt}</span><i class="fa-regular fa-trash-can icon delete-icon"></i>`;
        historyPanel.appendChild(historyItem);

        const savedHistory = JSON.parse(localStorage.getItem('searchHistory')) || [];
        savedHistory.push(userPrompt);
        localStorage.setItem('searchHistory', JSON.stringify(savedHistory));
    } catch (error) {
        console.error('Error fetching response:', error);
        resultContent.textContent = 'Sorry, there was an error generating the response.';
    }

    // Clear input field after showing the result
    searchBar.value = '';

    // Close history panel if open
    if (isHistoryOpen) {
        toggleHistory();
    }
}

searchBar.addEventListener('keypress', async (e) => {
    if (e.key === 'Enter' && e.target.value.trim() !== '') {
        const userPrompt = e.target.value.trim();
        await showResult(userPrompt);
    }
});

// Delete history item animation
historyPanel.addEventListener('click', (e) => {
    if (e.target.classList.contains('delete-icon')) {
        const historyItem = e.target.closest('.history-item');
        const itemText = historyItem.querySelector('.history-text').textContent;
        gsap.to(historyItem, {
            opacity: 0,
            x: 20,
            duration: 0.3,
            onComplete: () => {
                historyItem.remove();
                let savedHistory = JSON.parse(localStorage.getItem('searchHistory')) || [];
                savedHistory = savedHistory.filter(item => item !== itemText);
                localStorage.setItem('searchHistory', JSON.stringify(savedHistory));
            }
        });
    }
});

// Show result automatically when history item is clicked
historyPanel.addEventListener('click', async (e) => {
    if (e.target.classList.contains('history-text')) {
        const userPrompt = e.target.textContent;
        searchBar.value = userPrompt;

        // Display the prompt in the input field for 2 seconds
        await new Promise(resolve => setTimeout(resolve, 2000));

        // Show the result automatically
        await showResult(userPrompt);
    }
});

// Microphone functionality
const micIcon = document.querySelector('.mic-icon');
let recognition;

if ('webkitSpeechRecognition' in window) {
    recognition = new webkitSpeechRecognition();
    recognition.continuous = false;
    recognition.lang = 'en-US';

    recognition.onresult = function (event) {
        const transcript = event.results[0][0].transcript;
        searchBar.value = transcript;
    };

    recognition.onerror = function (event) {
        console.error('Speech recognition error:', event.error);
    };
}

micIcon.addEventListener('click', () => {
    if (recognition) {
        gsap.to(micIcon, {
            scale: 1.2,
            duration: 0.2,
            repeat: 1,
            yoyo: true,
            ease: "power2.inOut"
        });

        recognition.start();
    } else {
        console.error('Speech recognition not supported in this browser');
    }
});

// Plus icon reset functionality
const plusIcon = document.querySelector('.fa-plus');

plusIcon.addEventListener('click', () => {
    if (resultBox.style.display === 'block') {
        // Hide result box with smooth animation
        gsap.to(resultBox, {
            opacity: 0,
            y: 20,
            duration: 0.5,
            ease: "power3.inOut",
            onComplete: () => {
                resultBox.style.display = 'none';
                resultContent.innerHTML = '';
                searchBar.value = '';
                // Reset search bar with smooth animation
                gsap.fromTo(searchBar, { opacity: 0, y: -10 }, { opacity: 1, y: 0, duration: 0.5, ease: "power3.out" });
                document.querySelector('.quick-actions').classList.remove('hidden');
                gsap.to('.quick-actions', { opacity: 1, duration: 0.4 });
            }
        });

        // Reset dots animation
        gsap.killTweensOf(dots);
        gsap.to(dots, { opacity: 0, duration: 0 });
    }
});

// Update copy functionality
const copyIcon = document.querySelector('.copy-icon');

copyIcon.addEventListener('click', async () => {
    const resultContent = document.querySelector('.result-content');
    try {
        await navigator.clipboard.writeText(resultContent.innerText);
        
        // Visual feedback
        copyIcon.classList.add('copy-success');
        copyIcon.classList.remove('bi-clipboard');
        copyIcon.classList.add('bi-check2');
        
        // Reset after 1.5 seconds
        setTimeout(() => {
            copyIcon.classList.remove('copy-success');
            copyIcon.classList.remove('bi-check2');
            copyIcon.classList.add('bi-clipboard');
        }, 1500);
    } catch (err) {
        console.error('Failed to copy text:', err);
        copyIcon.style.color = '#dc3545';
        setTimeout(() => {
            copyIcon.style.color = '#4e4e4e';
        }, 1500);
    }
});