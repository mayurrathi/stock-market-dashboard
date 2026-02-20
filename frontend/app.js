/**
 * Stock Market Dashboard - Frontend Application
 */

const API_BASE = '';

// State
let currentSection = 'dashboard';
let startDate = null;
let endDate = null;
let currentShortcut = 'last_day';
let currentTimeframe = 'next_day';
let autoRefreshInterval = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeDateInputs();
    loadDashboardStats();
    loadIndices();
    loadLiveSignals();  // Load Live Signal Feed
    loadAllStarPicks();  // Load All Star section
    loadRecommendations();
    checkTelegramStatus();
    refreshWatchlistCache();  // Initialize watchlist cache for toggle buttons

    setupNavigation();
    setupTimeShortcuts();
    setupTimeframeTabs();
    setupButtons();
    setupForms();
    setupAllStarRefresh();  // Setup All Star refresh button
    setupUniversalCardClicks(); // Unified click handling for all cards
    setupAutoRefresh();     // Setup 32s Auto-Refresh
    initOmnibar();          // Unified Search/Chat
    setupGeminiSave();      // Gemini API key configuration
});


// ===== Initialization =====

function initializeDateInputs() {
    const now = new Date();
    const yesterday = new Date(now - 24 * 60 * 60 * 1000);
    const dateStr = formatDatetimeLocal(now);
    const yesterdayStr = formatDatetimeLocal(yesterday);

    // Populate all date inputs (Signals & News)
    document.querySelectorAll('input[id^="startDate"]').forEach(el => el.value = yesterdayStr);
    document.querySelectorAll('input[id^="endDate"]').forEach(el => el.value = dateStr);

    startDate = yesterday;
    endDate = now;
}

function formatDatetimeLocal(date) {
    const offset = date.getTimezoneOffset();
    const adjusted = new Date(date.getTime() - offset * 60 * 1000);
    return adjusted.toISOString().slice(0, 16);
}

// ===== Navigation =====

function setupNavigation() {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const section = item.dataset.section;
            switchSection(section);
        });
    });
}

function switchSection(section) {
    // Update nav
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.section === section);
    });

    // Update sections
    document.querySelectorAll('.section').forEach(sec => {
        sec.classList.add('hidden');
    });
    const sectionEl = document.getElementById(`${section}-section`);
    if (sectionEl) {
        sectionEl.classList.remove('hidden');
    } else {
        console.warn(`Section not found: ${section}-section`);
    }

    // Update title
    const titles = {
        dashboard: 'Dashboard',
        overview: 'Market Overview',
        watchlist: 'My Watchlist',
        messages: 'Telegram Signals',
        news: 'Market News',
        recommendations: 'Recommendations',
        sources: 'Sources',
        settings: 'Settings',
        ai: 'AI Assistant',
        research: 'Research Console',
        screener: 'Stock Screener'
    };
    const sectionTitleEl = document.getElementById('sectionTitle');
    if (sectionTitleEl) {
        sectionTitleEl.textContent = titles[section] || section;
    }

    currentSection = section;

    // Load section data - ALL tabs should auto-refresh when clicked
    if (section === 'dashboard') {
        loadDashboardStats();
        loadIndices();
        loadLiveSignals();
        loadAllStarPicks();
        loadRecommendations();
    }
    if (section === 'messages') loadMessages();
    if (section === 'news') loadNews();
    if (section === 'recommendations') loadRecommendationsFull();
    if (section === 'sources') loadSources();
    if (section === 'overview') {
        loadMarketOverview();
        setTimeout(() => triggerMarketAnalysis(), 500); // Slight delay to allow UI to render
    }
    if (section === 'watchlist') loadWatchlist();
    if (section === 'allstar') loadAllStarPicksPage();
    if (section === 'exittracker') loadExitTracker();
    if (section === 'settings') loadSettings();
    if (section === 'ai') initAiAssistant();
    if (section === 'research') {
        // Research section is loaded via openResearchForStock or manually
        const input = document.getElementById('researchSearchInput');
        if (input) input.focus();
    }
    // Quant Lab tabs
    if (section === 'patterns') initPatternScout();
    if (section === 'qvm') initQvmEngine();
    if (section === 'concall') initConcallAnalyst();
    if (section === 'mood') loadMarketMood();
}

// ===== AI Assistant Functions =====

async function initAiAssistant() {
    // Load the full AI dashboard
    await loadAiDashboard();

    // Focus the input
    const input = document.getElementById('aiChatInput');
    if (input) input.focus();
}

async function refreshAiDashboard() {
    showToast('Refreshing AI analysis...', 'info');
    await loadAiDashboard();
    showToast('AI Dashboard updated!', 'success');
}

async function loadAiDashboard() {
    try {
        // Fetch all data in parallel
        const [messagesData, newsData, recsData, allstarData] = await Promise.all([
            apiCall('/api/messages?shortcut=last_day').catch(() => ({ messages: [], count: 0 })),
            apiCall('/api/news?shortcut=last_day').catch(() => ({ news: [] })),
            apiCall('/api/recommendations').catch(() => ({ recommendations: {} })),
            apiCall('/api/allstar').catch(() => ({ picks: [] }))
        ]);

        // Count bullish/bearish signals from messages
        let bullishCount = 0;
        let bearishCount = 0;
        const messages = messagesData.messages || [];

        messages.forEach(msg => {
            const text = (msg.text || '').toLowerCase();
            const buyWords = ['buy', 'bullish', 'target', 'breakout', 'long', 'accumulate', 'upside'];
            const sellWords = ['sell', 'bearish', 'short', 'breakdown', 'avoid', 'exit'];

            if (buyWords.some(w => text.includes(w))) bullishCount++;
            if (sellWords.some(w => text.includes(w))) bearishCount++;
        });

        // Update stats
        document.getElementById('aiBullishCount').textContent = bullishCount;
        document.getElementById('aiBearishCount').textContent = bearishCount;
        document.getElementById('aiNewsCount').textContent = newsData.news?.length || 0;
        document.getElementById('aiTelegramCount').textContent = messagesData.count || messages.length;

        // Update Market Mood
        updateMarketMood(bullishCount, bearishCount);

        // Update Top Picks
        const topRecs = recsData.recommendations?.next_day?.slice(0, 6) || allstarData.picks?.slice(0, 6) || [];
        updateAiTopPicks(topRecs);

        // Update Telegram Signals
        updateTelegramSignals(messages.slice(0, 8));

        // Update Purchase Suggestions (high confidence BUY recommendations)
        const allRecs = Object.values(recsData.recommendations || {}).flat();
        const buyRecs = allRecs.filter(r => r.action === 'BUY' && r.confidence > 60).slice(0, 6);
        updatePurchaseSuggestions(buyRecs);

        // Update News Analysis
        updateNewsAnalysis(newsData.news?.slice(0, 6) || []);

    } catch (error) {
        console.error('Failed to load AI dashboard:', error);
        showToast('Failed to load AI dashboard', 'error');
    }
}

function updateMarketMood(bullish, bearish) {
    const total = bullish + bearish;
    const moodEmoji = document.getElementById('moodEmoji');
    const moodLabel = document.getElementById('moodLabel');
    const moodDescription = document.getElementById('moodDescription');
    const moodIndicator = document.getElementById('moodIndicator');

    let ratio = total > 0 ? bullish / total : 0.5;
    let mood, emoji, desc, color;

    if (ratio > 0.7) {
        mood = 'Very Bullish';
        emoji = '🚀';
        desc = 'Strong buying pressure detected. Market sentiment is highly positive.';
        color = '#22c55e';
    } else if (ratio > 0.55) {
        mood = 'Bullish';
        emoji = '📈';
        desc = 'More buyers than sellers. Positive sentiment overall.';
        color = '#22c55e';
    } else if (ratio > 0.45) {
        mood = 'Neutral';
        emoji = '⚖️';
        desc = 'Mixed signals. Market is in consolidation mode.';
        color = '#f59e0b';
    } else if (ratio > 0.3) {
        mood = 'Bearish';
        emoji = '📉';
        desc = 'Selling pressure building. Cautious approach recommended.';
        color = '#ef4444';
    } else {
        mood = 'Very Bearish';
        emoji = '⚠️';
        desc = 'Strong selling pressure. Consider defensive positions.';
        color = '#ef4444';
    }

    if (moodEmoji) moodEmoji.textContent = emoji;
    if (moodLabel) {
        moodLabel.textContent = mood;
        moodLabel.style.color = color;
    }
    if (moodDescription) moodDescription.textContent = desc;
    if (moodIndicator) moodIndicator.style.left = `${ratio * 100}%`;
}

function updateAiTopPicks(picks) {
    const container = document.getElementById('aiTopPicksGrid');
    if (!container) return;

    if (!picks.length) {
        container.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 40px; grid-column: span 3;">No recommendations available</div>';
        return;
    }

    container.innerHTML = picks.map(pick => `
        <div class="ai-pick-card" onclick="showStockDetail('${pick.symbol}')" style="background: var(--bg-tertiary); padding: 16px; border-radius: 8px; cursor: pointer; border: 1px solid var(--border-color); transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.02)'" onmouseout="this.style.transform='scale(1)'">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-weight: 700; font-size: 16px;">${pick.symbol}</span>
                <span style="background: ${pick.action === 'BUY' ? '#22c55e' : pick.action === 'SELL' ? '#ef4444' : '#f59e0b'}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;">${pick.action}</span>
            </div>
            <div style="font-size: 12px; color: var(--text-muted);">${pick.category || 'Stock'}</div>
            <div style="margin-top: 8px;">
                <div style="display: flex; justify-content: space-between; font-size: 11px; color: var(--text-muted); margin-bottom: 4px;">
                    <span>Confidence</span>
                    <span>${Math.round(pick.confidence || 0)}%</span>
                </div>
                <div style="height: 4px; background: var(--bg-secondary); border-radius: 2px;">
                    <div style="height: 100%; width: ${pick.confidence || 0}%; background: ${pick.action === 'BUY' ? '#22c55e' : '#f59e0b'}; border-radius: 2px;"></div>
                </div>
            </div>
        </div>
    `).join('');
}

function updateTelegramSignals(messages) {
    const container = document.getElementById('aiTelegramSignals');
    if (!container) return;

    if (!messages.length) {
        container.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 40px;">No recent Telegram signals</div>';
        return;
    }

    container.innerHTML = messages.map(msg => {
        const text = (msg.text || '').toLowerCase();
        const isBullish = ['buy', 'bullish', 'target', 'breakout'].some(w => text.includes(w));
        const isBearish = ['sell', 'bearish', 'short', 'avoid'].some(w => text.includes(w));
        const sentiment = isBullish ? 'bullish' : isBearish ? 'bearish' : 'neutral';
        const color = sentiment === 'bullish' ? '#22c55e' : sentiment === 'bearish' ? '#ef4444' : '#f59e0b';

        return `
            <div style="padding: 12px; border-bottom: 1px solid var(--border-color); display: flex; gap: 12px; align-items: flex-start;">
                <span class="material-icons" style="font-size: 18px; color: ${color};">${sentiment === 'bullish' ? 'trending_up' : sentiment === 'bearish' ? 'trending_down' : 'remove'}</span>
                <div style="flex: 1;">
                    <div style="font-size: 13px; color: var(--text-primary); line-height: 1.4;">${(msg.text || '').substring(0, 120)}${(msg.text || '').length > 120 ? '...' : ''}</div>
                    <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">${msg.channel_name || 'Telegram'} • ${new Date(msg.created_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}</div>
                </div>
            </div>
        `;
    }).join('');
}

function updatePurchaseSuggestions(recs) {
    const container = document.getElementById('aiPurchaseSuggestions');
    if (!container) return;

    if (!recs.length) {
        container.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 40px;">No strong buy signals at this time</div>';
        return;
    }

    container.innerHTML = recs.map(rec => `
        <div style="padding: 12px; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center;">
            <div>
                <div style="font-weight: 600; color: var(--text-primary);">${rec.symbol}</div>
                <div style="font-size: 12px; color: var(--text-muted);">${rec.timeframe?.replace('_', ' ') || 'Short term'}</div>
            </div>
            <div style="text-align: right;">
                <div style="background: #22c55e; color: white; padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: 600;">BUY</div>
                <div style="font-size: 11px; color: #22c55e; margin-top: 4px;">${Math.round(rec.confidence)}% confidence</div>
            </div>
        </div>
    `).join('');
}

function updateNewsAnalysis(news) {
    const container = document.getElementById('aiNewsAnalysis');
    if (!container) return;

    if (!news.length) {
        container.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 40px; grid-column: span 2;">No news to analyze</div>';
        return;
    }

    container.innerHTML = news.map(article => {
        const sentiment = article.sentiment || 'neutral';
        const color = sentiment === 'positive' ? '#22c55e' : sentiment === 'negative' ? '#ef4444' : '#f59e0b';
        const stocks = article.extracted_stocks?.slice(0, 3).join(', ') || '';

        return `
            <div style="background: var(--bg-tertiary); padding: 16px; border-radius: 8px; border: 1px solid var(--border-color);">
                <div style="display: flex; gap: 8px; align-items: flex-start; margin-bottom: 8px;">
                    <span class="material-icons" style="font-size: 16px; color: ${color};">${sentiment === 'positive' ? 'thumb_up' : sentiment === 'negative' ? 'thumb_down' : 'remove'}</span>
                    <div style="font-size: 13px; font-weight: 500; line-height: 1.4; color: var(--text-primary);">${(article.title || '').substring(0, 80)}${(article.title || '').length > 80 ? '...' : ''}</div>
                </div>
                ${stocks ? `<div style="font-size: 11px; color: var(--accent-primary); margin-bottom: 4px;">📊 Stocks: ${stocks}</div>` : ''}
                <div style="display: flex; justify-content: space-between; font-size: 11px; color: var(--text-muted);">
                    <span>${article.source || 'News'}</span>
                    <span style="color: ${color};">${sentiment.charAt(0).toUpperCase() + sentiment.slice(1)}</span>
                </div>
            </div>
        `;
    }).join('');
}

function handleAiChip(prompt) {
    const input = document.getElementById('aiChatInput');
    if (input) {
        input.value = prompt;
        sendAiChat();
    }
}

async function sendAiChat() {
    const input = document.getElementById('aiChatInput');
    const messagesContainer = document.getElementById('aiChatMessages');

    if (!input || !messagesContainer || !input.value.trim()) return;

    const userMessage = input.value.trim();
    input.value = '';

    // Add user message
    messagesContainer.innerHTML += `
        <div class="ai-message outgoing" style="display: flex; gap: 12px; margin-bottom: 16px; justify-content: flex-end;">
            <p style="background: var(--accent-primary); color: white; padding: 12px 16px; border-radius: 12px; margin: 0; max-width: 80%;">${userMessage}</p>
        </div>
    `;

    // Add loading indicator
    const loadingId = 'ai-loading-' + Date.now();
    messagesContainer.innerHTML += `
        <div id="${loadingId}" class="ai-message incoming" style="display: flex; gap: 12px; margin-bottom: 16px;">
            <span class="material-icons" style="color: var(--accent-primary);">smart_toy</span>
            <p style="background: var(--bg-secondary); padding: 12px 16px; border-radius: 12px; margin: 0;">Thinking...</p>
        </div>
    `;
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    try {
        const response = await apiCall('/api/ai/chat', {
            method: 'POST',
            body: JSON.stringify({ message: userMessage })
        });

        // Remove loading and add response
        document.getElementById(loadingId)?.remove();
        messagesContainer.innerHTML += `
            <div class="ai-message incoming" style="display: flex; gap: 12px; margin-bottom: 16px;">
                <span class="material-icons" style="color: var(--accent-primary);">smart_toy</span>
                <p style="background: var(--bg-secondary); padding: 12px 16px; border-radius: 12px; margin: 0; max-width: 80%;">${response.reply || 'Sorry, I could not process that request.'}</p>
            </div>
        `;
    } catch (error) {
        document.getElementById(loadingId)?.remove();
        messagesContainer.innerHTML += `
            <div class="ai-message incoming" style="display: flex; gap: 12px; margin-bottom: 16px;">
                <span class="material-icons" style="color: var(--accent-primary);">smart_toy</span>
                <p style="background: var(--bg-secondary); padding: 12px 16px; border-radius: 12px; margin: 0; color: #ef4444;">Error: ${error.message || 'Please configure Gemini API key in Settings.'}</p>
            </div>
        `;
    }
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// ===== Time Shortcuts =====

function setupTimeShortcuts() {
    // Handle shortcut buttons (Hr, Day, Week, Month)
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.shortcut-btn');
        if (btn) {
            const container = btn.closest('.time-shortcuts');
            if (container) {
                container.querySelectorAll('.shortcut-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentShortcut = btn.dataset.shortcut;
                refreshCurrentSection();
            }
        }
    });

    // Handle Apply buttons for date ranges
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('applyDateRange')) {
            const section = e.target.closest('.section');
            if (section) {
                const startInput = section.querySelector('input[id^="startDate"]');
                const endInput = section.querySelector('input[id^="endDate"]');

                if (startInput && endInput) {
                    startDate = new Date(startInput.value);
                    endDate = new Date(endInput.value);
                    currentShortcut = null;

                    section.querySelectorAll('.shortcut-btn').forEach(b => b.classList.remove('active'));
                    refreshCurrentSection();
                }
            }
        }
    });
}

function setupAutoRefresh() {
    const toggle = document.getElementById('autoRefreshToggle');
    if (!toggle) return;

    toggle.addEventListener('change', () => {
        if (toggle.checked) {
            console.log('Auto-refresh ENABLED (32s)');
            // Refresh immediately when turned on
            refreshCurrentSection();
            autoRefreshInterval = setInterval(() => {
                console.log('Auto-refreshing current section...');
                refreshCurrentSection();
            }, 32000);
        } else {
            console.log('Auto-refresh DISABLED');
            if (autoRefreshInterval) {
                clearInterval(autoRefreshInterval);
                autoRefreshInterval = null;
            }
        }
    });
}

// Note: refreshCurrentSection is defined at line ~802 as an async function with full section support

// ===== Timeframe Tabs =====

function setupTimeframeTabs() {
    document.querySelectorAll('.timeframe-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.timeframe-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            currentTimeframe = tab.dataset.tf;
            loadRecommendations();
        });
    });
}

// ===== API Calls =====

async function apiCall(endpoint, options = {}) {
    try {
        const url = `${API_BASE}${endpoint}`;
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'API Error');
        }

        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

function getTimeParams() {
    const params = new URLSearchParams();
    if (currentShortcut) {
        params.append('shortcut', currentShortcut);
    } else {
        // Fallback to active section's date inputs
        const activeSectionEl = document.getElementById(`${currentSection}-section`);
        if (activeSectionEl) {
            const sInput = activeSectionEl.querySelector('input[id^="startDate"]');
            const eInput = activeSectionEl.querySelector('input[id^="endDate"]');
            if (sInput?.value && eInput?.value) {
                startDate = new Date(sInput.value);
                endDate = new Date(eInput.value);
            }
        }
        params.append('start_date', startDate.toISOString());
        params.append('end_date', endDate.toISOString());
    }
    return params.toString();
}

// ===== Dashboard =====

async function loadDashboardStats() {
    try {
        const params = currentShortcut ? `shortcut=${currentShortcut}` : '';
        const stats = await apiCall(`/api/dashboard/stats?${params}`);

        document.getElementById('statMessages').textContent = stats.today_messages || 0;
        document.getElementById('statNews').textContent = stats.total_news || 0;
        document.getElementById('statSources').textContent = stats.active_sources || 0;
        document.getElementById('statRecommendations').textContent = stats.total_recommendations || 0;
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

async function loadIndices() {
    try {
        const indices = await apiCall('/api/stocks/indices');

        updateIndexCard('niftyCard', indices.NIFTY50);
        updateIndexCard('sensexCard', indices.SENSEX);
        updateIndexCard('bankniftyCard', indices.BANKNIFTY);
    } catch (error) {
        console.error('Failed to load indices:', error);
    }
}

function updateIndexCard(cardId, data) {
    if (!data) return;

    const card = document.getElementById(cardId);
    const value = card.querySelector('.index-value');
    const change = card.querySelector('.index-change');

    value.textContent = data.price ? data.price.toLocaleString('en-IN', { maximumFractionDigits: 2 }) : '--';

    if (data.change_percent !== null && data.change_percent !== undefined) {
        const sign = data.change_percent >= 0 ? '+' : '';
        change.textContent = `${sign}${data.change_percent.toFixed(2)}%`;
        change.className = `index-change ${data.change_percent >= 0 ? 'positive' : 'negative'}`;
    }

    // Add click handler to open TradingView
    card.style.cursor = 'pointer';
    card.onclick = () => {
        const symbols = {
            'niftyCard': 'NSE:NIFTY',
            'sensexCard': 'BSE:SENSEX',
            'bankniftyCard': 'NSE:BANKNIFTY'
        };
        const symbol = symbols[cardId] || 'NSE:NIFTY';
        window.open(`https://www.tradingview.com/chart/?symbol=${symbol}`, '_blank');
    };
}

// ===== All Star Picks =====

async function loadAllStarPicks(forceRefresh = false) {
    const container = document.getElementById('allstarPicks');
    const timer = document.getElementById('allstarTimer');

    try {
        // Pass force_refresh to API if requested
        const url = forceRefresh ? '/api/allstar?force_refresh=true' : '/api/allstar';
        const data = await apiCall(url);

        if (data.picks && data.picks.length > 0) {
            // Update timer with generated_at info and cache status
            if (data.generated_at || data.valid_until) {
                // Prefer generated_at date, fallback to valid_until (which is end of day)
                const dateStr = data.generated_at || data.valid_until;
                const dateObj = new Date(dateStr);
                const isToday = dateObj.toDateString() === new Date().toDateString();

                const timeStr = dateObj.toLocaleString('en-IN', {
                    hour: '2-digit', minute: '2-digit'
                });

                const dayStr = dateObj.toLocaleString('en-IN', {
                    day: 'numeric', month: 'short'
                });

                // User requested relevant INT time info
                timer.textContent = `Analysis: ${dayStr} • ${timeStr} IST`;
            }

            // Render Absolute Picks (New Section)
            if (data.absolute_picks && data.absolute_picks.length > 0) {
                const absContainer = document.getElementById('absolutePicks');
                if (absContainer) {
                    absContainer.innerHTML = data.absolute_picks.map((pick, index) => {
                        const recommendedPrice = pick.recommended_price || pick.current_price;
                        const currentPrice = pick.current_price || 0;
                        const priceChange = currentPrice - recommendedPrice;
                        const priceChangePct = recommendedPrice ? ((priceChange / recommendedPrice) * 100).toFixed(2) : 0;
                        const isGain = priceChange > 0;
                        const changeColor = isGain ? '#10b981' : (priceChange < 0 ? '#ef4444' : '#94a3b8');
                        const recommendedAt = pick.recommended_at || pick.created_at;
                        const timeStr = recommendedAt ? new Date(recommendedAt).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }) : '';

                        return `
                        <div class="absolute-card" data-symbol="${pick.symbol}" style="cursor: pointer; position: relative;">
                            <button onclick="toggleWatchlist('${pick.symbol}', event)" title="Add to Watchlist" style="position: absolute; top: 8px; right: 8px; width: 28px; height: 28px; border-radius: 50%; border: none; background: rgba(255,255,255,0.1); color: #fbbf24; cursor: pointer; font-size: 14px;">⭐</button>
                            <div class="absolute-badge">Rank #${index + 1}</div>
                            <div class="absolute-header">
                                <div class="absolute-symbol">${pick.symbol}</div>
                                <div class="absolute-price">₹${currentPrice.toLocaleString('en-IN')}</div>
                            </div>
                            <div class="absolute-action-row">
                                <div class="absolute-action ${pick.action.toLowerCase()}">${pick.action}</div>
                                <div class="absolute-confidence">${Math.round(pick.confidence)}% Growth Potential</div>
                            </div>
                            ${recommendedPrice && recommendedPrice !== currentPrice ? `
                            <div style="background: rgba(0,0,0,0.3); padding: 8px; border-radius: 6px; margin: 8px 0; font-size: 12px;">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                    <span style="color: #94a3b8;">Recommended:</span>
                                    <span style="color: var(--text-primary);">₹${recommendedPrice.toLocaleString('en-IN')} ${timeStr ? `@ ${timeStr}` : ''}</span>
                                </div>
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <span style="color: #94a3b8;">Change:</span>
                                    <span style="color: ${changeColor}; font-weight: 700;">
                                        ${isGain ? '+' : ''}₹${Math.abs(priceChange).toFixed(2)} (${isGain ? '+' : ''}${priceChangePct}%)
                                    </span>
                                </div>
                            </div>
                            ` : ''}
                            <div class="absolute-targets">
                                ${pick.target_price ? `<div class="target-val">Target: ₹${pick.target_price.toLocaleString('en-IN')}</div>` : ''}
                                ${pick.stop_loss ? `<div class="sl-val">SL: ₹${pick.stop_loss.toLocaleString('en-IN')}</div>` : ''}
                            </div>
                            <div class="absolute-reason">${pick.reasoning || 'High conviction setup detected.'}</div>
                        </div>
                        `;
                    }).join('');
                }
            } else {
                const absContainer = document.getElementById('absolutePicks');
                if (absContainer) absContainer.innerHTML = '<div class="empty-state"><span>🚀</span><p>No Absolute Picks found.</p></div>';
            }

            container.innerHTML = data.picks.map((pick, index) => `
                <div class="allstar-card ${pick.action.toLowerCase()}" data-symbol="${pick.symbol}" style="cursor: pointer; position: relative;">
                    <button onclick="toggleWatchlist('${pick.symbol}', event)" title="Add to Watchlist" style="position: absolute; top: 8px; right: 8px; width: 28px; height: 28px; border-radius: 50%; border: none; background: rgba(255,255,255,0.1); color: #fbbf24; cursor: pointer; font-size: 14px;">⭐</button>
                    <div class="allstar-rank">#${index + 1}</div>
                    <div class="allstar-main">
                        <div class="allstar-symbol">${pick.symbol}</div>
                        <div class="allstar-name">${pick.name}</div>
                        <div class="allstar-category">${pick.category}</div>
                    </div>
                    <div class="allstar-action ${pick.action.toLowerCase()}">
                        ${pick.action}
                    </div>
                    <div class="allstar-details">
                        <div class="allstar-price">₹${pick.current_price ? pick.current_price.toLocaleString('en-IN') : '--'}</div>
                        <div class="allstar-targets">
                            ${pick.target_price ? `<span class="target">T: ₹${pick.target_price.toLocaleString('en-IN')}</span>` : ''}
                            ${pick.stop_loss ? `<span class="sl">SL: ₹${pick.stop_loss.toLocaleString('en-IN')}</span>` : ''}
                        </div>
                    </div>
                    <div class="allstar-confidence">
                        <div class="confidence-bar">
                            <div class="confidence-fill" style="width: ${pick.confidence}%"></div>
                        </div>
                        <span>${Math.round(pick.confidence)}%</span>
                    </div>
                    ${pick.reasoning ? `<div class="allstar-reasoning">${pick.reasoning}</div>` : ''}
                    ${pick.next_entry_point ? `
                        <div class="entry-point-section" style="margin-top: 12px; padding-top: 12px; border-top: 1px dashed rgba(255,255,255,0.1);">
                            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                                <span style="font-size: 11px; text-transform: uppercase; color: var(--text-muted);">Next Entry</span>
                                <span style="font-size: 14px; font-weight: 700; color: #22c55e;">₹${pick.next_entry_point.toLocaleString('en-IN')}</span>
                                <span style="font-size: 11px; padding: 2px 6px; background: rgba(34,197,94,0.2); color: #22c55e; border-radius: 4px;">-${pick.entry_discount_pct}%</span>
                            </div>
                            <div style="font-size: 11px; color: var(--text-secondary); line-height: 1.4;">${pick.entry_reasoning || ''}</div>
                            ${pick.matches_screens && pick.matches_screens.length > 0 ? `
                                <div style="display: flex; gap: 4px; flex-wrap: wrap; margin-top: 6px;">
                                    ${pick.matches_screens.map(s => `<span style="font-size: 9px; padding: 2px 5px; background: rgba(99,102,241,0.2); color: #a5b4fc; border-radius: 3px;">${s}</span>`).join('')}
                                </div>
                            ` : ''}
                        </div>
                    ` : ''}
                </div>
            `).join('');
        } else {
            container.innerHTML = '<div class="empty-state"><span>📊</span><p>No All Star picks available. Click Refresh to generate.</p></div>';
        }
    } catch (error) {
        console.error('Failed to load All Star picks:', error);

        container.innerHTML = '<div class="empty-state"><span>⚠️</span><p>Failed to load picks</p></div>';
    }
}

// Load All Star Picks for the dedicated page (uses different container IDs)
async function loadAllStarPicksPage(forceRefresh = false) {
    const container = document.getElementById('allstarPicksPage');
    const timer = document.getElementById('allstarTimerPage');

    if (!container) return; // Safety check

    try {
        const url = forceRefresh ? '/api/allstar?force_refresh=true' : '/api/allstar';
        const data = await apiCall(url);

        if (data.picks && data.picks.length > 0) {
            // Update timer
            if (data.generated_at || data.valid_until) {
                const dateStr = data.generated_at || data.valid_until;
                const dateObj = new Date(dateStr);
                const timeStr = dateObj.toLocaleString('en-IN', {
                    hour: '2-digit', minute: '2-digit'
                });
                const dayStr = dateObj.toLocaleString('en-IN', {
                    day: 'numeric', month: 'short'
                });
                if (timer) timer.textContent = `Analysis: ${dayStr} • ${timeStr} IST`;
            }

            container.innerHTML = data.picks.map((pick, index) => `
            <div class="allstar-card ${pick.action.toLowerCase()}" data-symbol="${pick.symbol}" style="cursor: pointer; position: relative;">
                    <button onclick="toggleWatchlist('${pick.symbol}', event)" title="Add to Watchlist" style="position: absolute; top: 8px; right: 8px; width: 28px; height: 28px; border-radius: 50%; border: none; background: rgba(255,255,255,0.1); color: #fbbf24; cursor: pointer; font-size: 14px;">⭐</button>
                    <div class="allstar-rank">#${index + 1}</div>
                    <div class="allstar-main">
                        <div class="allstar-symbol">${pick.symbol}</div>
                        <div class="allstar-name">${pick.name}</div>
                        <div class="allstar-category">${pick.category}</div>
                    </div>
                    <div class="allstar-action ${pick.action.toLowerCase()}">
                        ${pick.action}
                    </div>
                    <div class="allstar-details">
                        <div class="allstar-price">₹${pick.current_price ? pick.current_price.toLocaleString('en-IN') : '--'}</div>
                        <div class="allstar-targets">
                            ${pick.target_price ? `<span class="target">T: ₹${pick.target_price.toLocaleString('en-IN')}</span>` : ''}
                            ${pick.stop_loss ? `<span class="sl">SL: ₹${pick.stop_loss.toLocaleString('en-IN')}</span>` : ''}
                        </div>
                    </div>
                    <div class="allstar-confidence">
                        <div class="confidence-bar">
                            <div class="confidence-fill" style="width: ${pick.confidence}%"></div>
                        </div>
                        <span>${Math.round(pick.confidence)}%</span>
                    </div>
                    ${pick.reasoning ? `<div class="allstar-reasoning">${pick.reasoning}</div>` : ''}
                    ${pick.next_entry_point ? `
                        <div class="entry-point-section" style="margin-top: 12px; padding-top: 12px; border-top: 1px dashed rgba(255,255,255,0.1);">
                            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                                <span style="font-size: 11px; text-transform: uppercase; color: var(--text-muted);">Next Entry</span>
                                <span style="font-size: 14px; font-weight: 700; color: #22c55e;">₹${pick.next_entry_point.toLocaleString('en-IN')}</span>
                                <span style="font-size: 11px; padding: 2px 6px; background: rgba(34,197,94,0.2); color: #22c55e; border-radius: 4px;">-${pick.entry_discount_pct}%</span>
                            </div>
                            <div style="font-size: 11px; color: var(--text-secondary); line-height: 1.4;">${pick.entry_reasoning || ''}</div>
                            ${pick.matches_screens && pick.matches_screens.length > 0 ? `
                                <div style="display: flex; gap: 4px; flex-wrap: wrap; margin-top: 6px;">
                                    ${pick.matches_screens.map(s => `<span style="font-size: 9px; padding: 2px 5px; background: rgba(99,102,241,0.2); color: #a5b4fc; border-radius: 3px;">${s}</span>`).join('')}
                                </div>
                            ` : ''}
                        </div>
                    ` : ''
                }
                </div>
                `).join('');

        } else {
            container.innerHTML = '<div class="empty-state"><span>📊</span><p>No All Star picks available. Click Refresh to generate.</p></div>';
        }
    } catch (error) {
        console.error('Failed to load All Star picks page:', error);
        container.innerHTML = '<div class="empty-state"><span>⚠️</span><p>Failed to load picks</p></div>';
    }
}

// Load Exit Tracker - track historical picks 30 days
async function loadExitTracker() {
    const container = document.getElementById('exitTrackerPicks');
    const timer = document.getElementById('exitTrackerTimer');
    const activeStat = document.getElementById('exitActiveCount');
    const sellStat = document.getElementById('exitSellCount');

    if (!container) return;

    // Show loading
    container.innerHTML = '<div class="loading-state"><span>🔄</span><p>Analyzing portfolio...</p></div>';

    try {
        const data = await apiCall('/api/exit-tracker');

        if (timer && (data.generated_at)) {
            const dateObj = new Date(data.generated_at);
            const timeStr = dateObj.toLocaleString('en-IN', { hour: '2-digit', minute: '2-digit' });
            timer.textContent = `Analysis: Today • ${timeStr} IST`;
        }

        // Update stats
        if (activeStat) activeStat.textContent = data.picks.length;
        if (sellStat) sellStat.textContent = data.sell_count;

        if (data.picks && data.picks.length > 0) {
            container.innerHTML = data.picks.map((pick, index) => {
                const isSell = pick.current_action === 'SELL';
                const actionColor = isSell ? '#ef4444' : '#10b981';
                const bgStyle = isSell ? 'border-left: 3px solid #ef4444;' : 'border-left: 3px solid #10b981;';
                const gainClass = pick.performance_pct >= 0 ? 'text-green' : 'text-red';
                const gainOperator = pick.performance_pct >= 0 ? '+' : '';

                return `
            <div class="allstar-card" data-symbol="${pick.symbol}" style="cursor: pointer; position: relative; ${bgStyle} padding-bottom: 8px;">
                     <div style="position: absolute; top: 10px; right: 10px; font-size: 10px; font-weight: 600; padding: 2px 6px; border-radius: 4px; background: ${isSell ? 'rgba(239,68,68,0.2)' : 'rgba(16,185,129,0.2)'}; color: ${actionColor};">
                        ${pick.current_action}
                     </div>
                     
                    <div class="allstar-main" style="margin-bottom: 8px;">
                        <div class="allstar-symbol" style="font-size: 16px;">${pick.symbol}</div>
                        <div class="allstar-category" style="font-size: 11px;">${pick.category} • Held ${pick.days_held}d</div>
                    </div>
                    
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px; padding: 8px; background: rgba(255,255,255,0.03); border-radius: 6px;">
                        <div>
                            <div style="font-size: 10px; color: var(--text-muted);">Entry</div>
                            <div style="font-size: 13px;">₹${pick.recommended_price?.toLocaleString('en-IN')}</div>
                            <div style="font-size: 10px; color: var(--text-muted);">${pick.recommended_date}</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 10px; color: var(--text-muted);">Current</div>
                            <div style="font-size: 13px;">₹${pick.current_price?.toLocaleString('en-IN')}</div>
                            <div style="font-size: 11px; font-weight: 600;" class="${gainClass}">${gainOperator}${pick.performance_pct}%</div>
                        </div>
                    </div>
                    
                    ${isSell && pick.sell_reason ? `
                    <div style="font-size: 11px; padding: 6px; background: rgba(239,68,68,0.1); border-left: 2px solid #ef4444; color: #fca5a5; margin-top: 4px;">
                        ${pick.sell_reason}
                    </div>
                    ` : ''}
                    
                    ${!isSell && pick.original_target ? `
                    <div style="display: flex; gap: 8px; font-size: 11px; margin-top: 4px; color: var(--text-muted);">
                        <span>T: ₹${pick.original_target}</span>
                        <span>SL: ₹${pick.original_stop_loss}</span>
                    </div>
                    ` : ''
                    }
                </div>
            `;
            }).join('');
        } else {
            container.innerHTML = '<div class="empty-state"><span>📊</span><p>No historical picks available yet. Check back tomorrow!</p></div>';
        }
    } catch (error) {
        console.error('Failed to load Exit Tracker:', error);
        container.innerHTML = '<div class="empty-state"><span>⚠️</span><p>Failed to load portfolio</p></div>';
    }
}

// Pagination State
let currentSignalPage = 1;
let currentNewsPage = 1;

function renderPaginationControls(currentPage, totalPages, type) {
    const fn = type === 'signals' ? 'loadLiveSignals' : 'loadNews';
    return `
            <div class="pagination-controls" style="display: flex; justify-content: center; align-items: center; gap: 16px; margin-top: 24px; padding-top: 16px; border-top: 1px dashed var(--border-color);">
            <button class="btn btn-secondary" ${currentPage <= 1 ? 'disabled style="opacity:0.5; cursor:not-allowed;"' : ''} onclick="${fn}(${currentPage - 1})">
                ← Previous
            </button>
            <span style="color: var(--text-secondary); font-size: 13px; font-weight: 600;">Page ${currentPage} of ${totalPages}</span>
            <button class="btn btn-secondary" ${currentPage >= totalPages ? 'disabled style="opacity:0.5; cursor:not-allowed;"' : ''} onclick="${fn}(${currentPage + 1})">
                Next →
            </button>
        </div>
            `;
}

async function loadLiveSignals(page = 1) {
    currentSignalPage = page;
    const container = document.getElementById('liveSignalFeed');
    const countEl = document.getElementById('liveSignalCount');
    const updatedEl = document.getElementById('liveSignalUpdated');

    if (!container) return;

    try {
        const data = await apiCall(`/api/signals/live?page=${page}&limit=40&days=7`);

        if (data.signals && data.signals.length > 0) {
            countEl.textContent = data.count;
            updatedEl.textContent = `Updated: ${new Date(data.last_updated).toLocaleTimeString('en-IN')} `;

            container.innerHTML = data.signals.map(signal => {
                const actionColors = {
                    'STRONG BUY': { bg: 'rgba(16, 185, 129, 0.2)', color: '#10b981' },
                    'BUY': { bg: 'rgba(52, 211, 153, 0.2)', color: '#34d399' },
                    'HOLD': { bg: 'rgba(251, 191, 36, 0.2)', color: '#fbbf24' },
                    'SELL': { bg: 'rgba(248, 113, 113, 0.2)', color: '#f87171' },
                    'AVOID': { bg: 'rgba(239, 68, 68, 0.2)', color: '#ef4444' }
                };
                const style = actionColors[signal.action] || actionColors['HOLD'];
                const attentionStyle = signal.requires_attention ? 'border: 2px solid var(--accent-primary); animation: pulse 2s infinite;' : '';

                return `
            <div class="signal-card" style="min-width: 280px; background: var(--bg-card); border-radius: 12px; padding: 12px; ${attentionStyle}" data-signal-id="${signal.id || ''}">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <span style="font-size: 11px; color: var(--text-muted);">${signal.channel_name}</span>
                            <div style="display: flex; align-items: center; gap: 6px;">
                                <span style="font-size: 12px; font-weight: 700; padding: 2px 8px; border-radius: 4px; background: ${style.bg}; color: ${style.color};">
                                    ${signal.action}
                                </span>
                            </div>
                        </div>
                        <div class="signal-text-preview" style="font-size: 13px; color: var(--text-secondary); margin-bottom: 8px; line-height: 1.4; max-height: 60px; overflow: hidden; text-overflow: ellipsis;">
                            ${signal.text.length > 150 ? signal.text.substring(0, 150) + '...' : signal.text}
                        </div>
                        <div style="display: flex; gap: 6px; flex-wrap: wrap; align-items: center;">
                            ${signal.stocks.map(s => '<span style="display: inline-flex; align-items: center; gap: 4px;"><span onclick="showStockDetail(\'' + s + '\')" style="cursor: pointer; font-size: 11px; font-weight: 600; padding: 2px 6px; background: var(--accent-primary); color: #fff; border-radius: 4px;">' + s + '</span><button onclick="toggleWatchlist(\'' + s + '\', event)" title="Add ' + s + ' to Watchlist" style="width: 20px; height: 20px; border-radius: 50%; border: none; background: rgba(251, 191, 36, 0.2); color: #fbbf24; cursor: pointer; font-size: 10px;">⭐</button></span>').join('')}
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px; padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.05);">
                            <span style="font-size: 10px; color: var(--text-muted);">
                                ${new Date(signal.timestamp).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })} • ${new Date(signal.timestamp).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
                            </span>
                            <div style="display: flex; gap: 6px;">
                                <button onclick="expandSignal('${encodeURIComponent(JSON.stringify(signal))}')" title="Expand" style="padding: 4px 8px; font-size: 10px; background: rgba(99,102,241,0.2); color: #a5b4fc; border: none; border-radius: 4px; cursor: pointer;">
                                    📖 Expand
                                </button>
                                <button onclick="searchSignalOnGoogle('${encodeURIComponent(signal.text.substring(0, 100))}')" title="Search on Google" style="padding: 4px 8px; font-size: 10px; background: rgba(34,197,94,0.2); color: #22c55e; border: none; border-radius: 4px; cursor: pointer;">
                                    🔍 Google
                                </button>
                            </div>
                        </div>
                    </div>
            `;
            }).join('');


            // Append Pagination
            if (data.total_pages > 1) {
                container.innerHTML += renderPaginationControls(data.page, data.total_pages, 'signals');
            }
        } else {
            countEl.textContent = '0';
            container.innerHTML = '<div class="empty-state" style="flex: 1; text-align: center; padding: 24px; color: var(--text-muted);"><span>📡</span><p>No live signals in the last hour</p></div>';
        }
    } catch (error) {
        console.error('Failed to load live signals:', error);
    }
}

function setupAllStarRefresh() {
    // The previous ID 'refreshAllstar' might be wrong if HTML uses class 'refresh-btn' or different ID.
    // In index.html line 125, it is: <button class="btn btn-icon-round refresh-btn" onclick="refreshCurrentSection()">🔄</button>
    // So 'refreshAllstar' ID might not exist.
    // We should fix 'refreshCurrentSection' instead or ensure the button has the ID.
}

// Global refresh handler called by onclick="refreshCurrentSection()"
async function refreshCurrentSection() {
    const activeSection = document.querySelector('.nav-item.active').dataset.section;
    const btn = document.querySelector('.section:not(.hidden) .refresh-btn');

    if (btn) {
        btn.disabled = true;
        btn.classList.add('spinning'); // Add CSS spin
    }

    try {
        if (activeSection === 'dashboard') {
            // Force refresh to get fresh data when user explicitly clicks refresh
            await loadAllStarPicks(true);
            // Also refresh indices
            await loadIndices();
        } else if (activeSection === 'allstar') {
            await loadAllStarPicksPage(true);
        } else if (activeSection === 'overview') {
            await loadMarketOverview();
        } else if (activeSection === 'news') {
            await loadNews();
        } else if (activeSection === 'messages') {
            await loadLiveSignals();
        } else if (activeSection === 'recommendations') {
            await loadRecommendationsFull();
        } else if (activeSection === 'watchlist') {
            await loadWatchlist();
        } else if (activeSection === 'sources') {
            await loadSources();
        } else if (activeSection === 'exittracker') {
            await loadExitTracker();
        } else if (activeSection === 'mood') {
            await loadMarketMood();
        } else if (activeSection === 'ai') {
            await refreshAiDashboard();
        }
        showToast('Refreshed!', 'success', 0); // Persistent until dismissed
    } catch (e) {
        console.error("Refresh failed", e);
        showToast('Refresh failed', 'error', 0);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.classList.remove('spinning');
        }
    }
}

// Gemini Save Logic
async function setupGeminiSave() {
    const btn = document.getElementById('saveGeminiBtn');
    const input = document.getElementById('geminiKeyInput');

    // Check initial status
    try {
        const config = await apiCall('/api/gemini/config');
        if (config.has_key && input) {
            input.placeholder = "✅ API Key is configured";
        }
    } catch (e) { console.error("Failed to check Gemini status", e); }

    if (btn && input) {
        btn.addEventListener('click', async () => {
            const key = input.value.trim();
            if (!key) return showToast('Please enter a key', 'error');

            btn.disabled = true;
            btn.textContent = 'Saving...';

            try {
                // Correct endpoint and payload matching backend Pydantic model
                await apiCall('/api/gemini/config', {
                    method: 'POST',
                    body: JSON.stringify({
                        api_key: key,
                        model: "gemini-3.0-flash" // Default model
                    })
                });

                showToast('API Key saved successfully!', 'success');
                input.value = ''; // Clear for security
                input.placeholder = "✅ API Key is configured";
            } catch (e) {
                console.error("Failed to save key", e);
                showToast('Failed to save key: ' + e.message, 'error');
            } finally {
                btn.disabled = false;
                btn.textContent = 'Save';
            }
        });
    }
}

// NOTE: setupGeminiSave is now called from the main DOMContentLoaded block

function setupUniversalCardClicks() {
    // Single delegated listener for ALL interactive cards and tags across the dashboard
    document.addEventListener('click', (e) => {
        // Handle cards (All Star, Recommendations, News, Messages)
        const clickable = e.target.closest('.absolute-card, .allstar-card, .rec-card, .news-card, .message-card, .watchlist-card, .stock-tag');
        if (!clickable) return;

        // Skip if clicking a nested button with its own logic
        if (e.target.closest('button')) return;

        let symbol = clickable.dataset.symbol;

        // Fallback checks for different card structures
        if (!symbol) {
            // Try multiple selectors for different card types
            const symbolEl = clickable.querySelector('.absolute-symbol, .allstar-symbol, .rec-symbol, .watchlist-symbol');
            if (symbolEl) {
                symbol = symbolEl.textContent.trim();
            }
        }

        // For stock tags, use the tag's own text content
        if (!symbol && clickable.classList.contains('stock-tag')) {
            symbol = clickable.textContent.trim();
        }

        // Specifically for news/message cards that might have a first extracted stock
        if (!symbol && (clickable.classList.contains('news-card') || clickable.classList.contains('message-card'))) {
            // Find the first stock tag or use the first symbol from the card's data if available
            const firstTag = clickable.querySelector('.stock-tag');
            if (firstTag) symbol = firstTag.textContent.trim();
        }

        if (symbol) {
            showStockDetail(symbol);
        }
    });
}

async function loadRecommendations() {
    try {
        const data = await apiCall(`/api/recommendations?timeframe=${currentTimeframe}`);
        const grid = document.getElementById('recommendationsGrid');

        const recs = data.recommendations[currentTimeframe] || [];

        if (recs.length === 0) {
            grid.innerHTML = `
            <div class="empty-state">
                    <span>🔍</span>
                    <p>No recommendations for this timeframe. Click "Analyze & Recommend" to generate.</p>
                </div>
            `;
            return;
        }

        grid.innerHTML = recs.map(rec => `
            <div class="rec-card" data-symbol="${rec.symbol}" style="cursor: pointer;">
                <div class="rec-header">
                    <span class="rec-symbol">${rec.symbol}</span>
                    <span class="rec-action ${rec.action}">${rec.action}</span>
                </div>
                    <div class="rec-confidence">
                        <div class="confidence-bar">
                            <div class="confidence-fill" style="width: ${rec.confidence}%"></div>
                        </div>
                        <small style="color: var(--text-muted); font-size: 11px;">${(rec.confidence || 0).toFixed(1)}% confidence</small>
                    </div>
                    <div class="rec-reasoning">${rec.reasoning || 'No details available'}</div>
                </div>
            `).join('');

    } catch (error) {
        console.error('Failed to load recommendations:', error);
    }
}

// ===== Messages =====

async function loadMessages() {
    try {
        const params = getTimeParams();
        const data = await apiCall(`/api/messages?${params}&limit=50`);
        const list = document.getElementById('messagesList');

        if (data.messages.length === 0) {
            list.innerHTML = `
            <div class="empty-state">
                    <span>💬</span>
                    <p>No signals in this time range.</p>
                </div>
            `;
            return;
        }

        list.innerHTML = data.messages.map(msg => `
            <div class="message-card" data-symbol="${msg.extracted_stocks?.length ? msg.extracted_stocks[0] : ''}" style="${msg.extracted_stocks?.length ? 'cursor: pointer;' : ''}">
                <div class="message-header">
                    <span class="message-channel">${msg.channel_name || 'Unknown Channel'}</span>
                    <span class="message-time">${formatTime(msg.created_at)}</span>
                </div>
                <div class="message-text">${escapeHtml(msg.text?.substring(0, 500) || '')}</div>
                ${msg.extracted_stocks?.length ? `
                    <div class="message-stocks">
                        ${msg.extracted_stocks.map(s => `<span class="stock-tag" data-symbol="${s}" style="cursor: pointer; transition: all 0.2s;">${s}</span>`).join('')}
                    </div>
                ` : ''
            }
                ${msg.sentiment ? `<span class="sentiment-badge ${msg.sentiment}">${msg.sentiment}</span>` : ''}
            </div>
            `).join('');

    } catch (error) {
        console.error('Failed to load messages:', error);
    }
}

// ===== News =====

async function loadNews(page = 1) {
    currentNewsPage = page;
    try {
        const params = getTimeParams();
        const data = await apiCall(`/api/news?${params}&page=${page}&limit=40`);
        const list = document.getElementById('newsList');

        if (data.news.length === 0) {
            list.innerHTML = `
            <div class="empty-state">
                    <span>📰</span>
                    <p>No news articles in this time range. Click "Fetch News" to load latest.</p>
                </div>
            `;
            return;
        }

        list.innerHTML = data.news.map(item => `
            <div class="news-card" data-symbol="${item.stocks?.length ? item.stocks[0] : ''}" style="${item.stocks?.length ? 'cursor: pointer;' : ''}">
                <div class="news-header">
                    <span class="news-source">${formatSource(item.source)}</span>
                    <span class="news-time">${formatTime(item.published_at)}</span>
                </div>
                <div class="news-title">
                    <a href="${item.link}" target="_blank">${escapeHtml(item.title)}</a>
                </div>
                <div class="news-summary">${escapeHtml(item.summary?.substring(0, 200) || '')}...</div>
                ${item.stocks?.length ? `
                    <div class="message-stocks">
                        ${item.stocks.map(s => `<span class="stock-tag" data-symbol="${s}" style="cursor: pointer;">${s}</span>`).join('')}
                    </div>
                ` : ''
            }
                ${item.sentiment ? `<span class="sentiment-badge ${item.sentiment}">${item.sentiment}</span>` : ''}
            </div>
            `).join('');

        // Append Pagination
        if (data.total_pages > 1) {
            list.innerHTML += renderPaginationControls(data.page, data.total_pages, 'news');
        }

    } catch (error) {
        console.error('Failed to load news:', error);
    }
}

// ===== Full Recommendations =====

async function loadRecommendationsFull() {
    try {
        const data = await apiCall('/api/recommendations');
        const timeframes = ['next_day', 'next_week', 'next_month', '1yr', '2yr', '5yr', '10yr'];

        timeframes.forEach(tf => {
            const container = document.querySelector(`#tf-${tf} .tf-recs`);
            if (!container) return; // Safety check: skip if container doesn't exist

            const recs = data.recommendations[tf] || [];

            if (recs.length === 0) {
                container.innerHTML = '<p style="color: var(--text-muted); text-align: center;">No recommendations</p>';
                return;
            }

            container.innerHTML = recs.slice(0, 5).map(rec => `
                <div class="rec-card" onclick="showRecommendationReasoning('${rec.symbol}', '${tf}', '${rec.action}', ${rec.confidence || 0}, '${(rec.reasoning || 'No reasoning available').replace(/'/g, "\\'")}')" 
                    title="${rec.reasoning || 'Click for details'}"
                    style="cursor: pointer;">
                    <div class="rec-header">
                        <span class="rec-symbol">${rec.symbol}</span>
                        <span class="rec-action ${rec.action}">${rec.action}</span>
                    </div>
                    <div style="font-size: 12px; color: var(--text-muted);">${(rec.confidence || 0).toFixed(1)}% confidence</div>
                    <div class="rec-reasoning-preview" style="font-size: 11px; color: var(--text-secondary); margin-top: 4px; line-height: 1.3; max-height: 32px; overflow: hidden;">
                        ${rec.reasoning ? rec.reasoning.substring(0, 80) + '...' : ''}
                    </div>
                </div>
            `).join('');
        });

    } catch (error) {
        console.error('Failed to load full recommendations:', error);
    }
}

// ===== Sources =====

async function loadSources() {
    try {
        const sources = await apiCall('/api/sources');
        const list = document.getElementById('sourcesList');

        if (sources.length === 0) {
            list.innerHTML = `
            <div class="empty-state">
                    <span>📡</span>
                    <p>No sources configured. Click "Add Source" to add Telegram channels.</p>
                </div>
            `;
            return;
        }

        list.innerHTML = sources.map(source => `
            <div class="source-card">
                <div class="source-header">
                    <span class="source-name">${escapeHtml(source.name)}</span>
                    <span class="source-status ${source.active ? '' : 'inactive'}"></span>
                </div>
                <div class="source-username">${escapeHtml(source.channel_username || source.channel_id)}</div>
                <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 12px;">
                    Last fetched: ${source.last_fetched ? formatTime(source.last_fetched) : 'Never'}
                </div>
                <div class="source-actions">
                    <button class="btn btn-secondary" onclick="fetchSource(${source.id})">Fetch</button>
                    <button class="btn btn-secondary" onclick="deleteSource(${source.id})" style="color: var(--danger);">Delete</button>
                </div>
            </div>
            `).join('');

    } catch (error) {
        console.error('Failed to load sources:', error);
    }
}

async function fetchSource(sourceId) {
    try {
        const result = await apiCall(`/api/sources/${sourceId}/fetch`, { method: 'POST' });
        showToast(`Fetched ${result.messages_fetched} messages!`, 'success');
        loadSources();
        loadDashboardStats();
    } catch (error) {
        showToast('Failed to fetch: ' + error.message, 'error');
    }
}

async function deleteSource(sourceId) {
    if (!confirm('Are you sure you want to delete this source?')) return;

    try {
        await apiCall(`/api/sources/${sourceId}`, { method: 'DELETE' });
        loadSources();
    } catch (error) {
        showToast('Failed to delete: ' + error.message, 'error');
    }
}

// ===== Buttons =====

function setupButtons() {
    document.getElementById('fetchNewsBtn').addEventListener('click', async () => {
        const btn = document.getElementById('fetchNewsBtn');
        btn.disabled = true;
        btn.innerHTML = '<span class="loading"></span> Fetching...';

        try {
            const result = await apiCall('/api/news/fetch', { method: 'POST' });
            showToast(`Fetched ${result.articles_fetched} news articles!`, 'success');
            loadDashboardStats();
            if (currentSection === 'news') loadNews();
        } catch (error) {
            showToast('Failed to fetch news: ' + error.message, 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<span>📰</span> Fetch News';
        }
    });

    document.getElementById('fetchPricesBtn').addEventListener('click', async () => {
        const btn = document.getElementById('fetchPricesBtn');
        btn.disabled = true;
        btn.innerHTML = '<span class="loading"></span> Updating...';

        try {
            const result = await apiCall('/api/stocks/fetch', { method: 'POST' });
            showToast(`Updated ${result.prices_fetched} stock prices!`, 'success');
            loadIndices();
        } catch (error) {
            showToast('Failed to update prices: ' + error.message, 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<span>💹</span> Update Prices';
        }
    });

    document.getElementById('analyzeBtn').addEventListener('click', async () => {
        const btn = document.getElementById('analyzeBtn');
        btn.disabled = true;
        btn.innerHTML = '<span class="loading"></span> Analyzing...';

        try {
            const params = getTimeParams();
            const result = await apiCall(`/api/analyze?${params}`, { method: 'POST' });

            showToast(`Analysis complete! ${result.recommendations.length} recommendations generated.`, 'success');

            loadRecommendations();
            loadDashboardStats();
        } catch (error) {
            showToast('Analysis failed: ' + error.message, 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<span>🔍</span> Analyze & Recommend';
        }
    });

    document.getElementById('refreshNewsBtn')?.addEventListener('click', () => {
        loadNews();
    });
}

// ===== Modals =====

function setupModals() {
    const modal = document.getElementById('addSourceModal');

    document.getElementById('addSourceBtn').addEventListener('click', () => {
        modal.classList.remove('hidden');
    });

    document.getElementById('cancelAddSource').addEventListener('click', () => {
        modal.classList.add('hidden');
    });

    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.add('hidden');
        }
    });
}

// ===== Forms =====

function setupForms() {
    // Add Source Form
    document.getElementById('addSourceForm').addEventListener('submit', async (e) => {
        e.preventDefault();

        const name = document.getElementById('sourceName').value;
        const username = document.getElementById('channelUsername').value;

        try {
            await apiCall('/api/sources', {
                method: 'POST',
                body: JSON.stringify({ name, channel_username: username })
            });

            document.getElementById('addSourceModal').classList.add('hidden');
            document.getElementById('addSourceForm').reset();
            loadSources();
            loadDashboardStats();
        } catch (error) {
            showToast('Failed to add source: ' + error.message, 'error');
        }
    });

    // Telegram Auth
    document.getElementById('sendCodeBtn').addEventListener('click', async () => {
        const apiId = document.getElementById('apiId').value;
        const apiHash = document.getElementById('apiHash').value;
        const phone = document.getElementById('phoneNumber').value;

        if (!apiId || !apiHash || !phone) {
            showToast('Please fill all fields', 'error');
            return;
        }

        try {
            await apiCall('/api/telegram/login', {
                method: 'POST',
                body: JSON.stringify({
                    api_id: parseInt(apiId),
                    api_hash: apiHash,
                    phone: phone
                })
            });

            document.getElementById('verifySection').classList.remove('hidden');
            showToast('Verification code sent to your Telegram!', 'success');
        } catch (error) {
            showToast('Failed to send code: ' + error.message, 'error');
        }
    });

    document.getElementById('verifyCodeBtn').addEventListener('click', async () => {
        const phone = document.getElementById('phoneNumber').value;
        const code = document.getElementById('verifyCode').value;

        if (!code) {
            showToast('Please enter the verification code', 'error');
            return;
        }

        try {
            const result = await apiCall('/api/telegram/verify', {
                method: 'POST',
                body: JSON.stringify({ phone, code })
            });

            if (result.status === 'authenticated') {
                showToast('Telegram connected successfully!', 'success');
                checkTelegramStatus();
            } else if (result.status === '2fa_required') {
                showToast('2FA required. Please enter your 2FA password.', 'error');
            } else {
                showToast('Verification failed: ' + result.message, 'error');
            }
        } catch (error) {
            showToast('Verification failed: ' + error.message, 'error');
        }
    });

    // Message search
    document.getElementById('messageSearch')?.addEventListener('input', debounce(() => {
        loadMessages();
    }, 300));
}

// ===== Telegram Status =====

async function checkTelegramStatus() {
    try {
        const status = await apiCall('/api/telegram/status');
        const statusEl = document.getElementById('telegramStatus');
        const dot = statusEl.querySelector('.status-dot');

        if (status.authorized) {
            dot.className = 'status-dot connected';
            statusEl.querySelector('span:last-child').textContent = 'Telegram: Connected';
        } else {
            dot.className = 'status-dot disconnected';
            statusEl.querySelector('span:last-child').textContent = 'Telegram: Disconnected';
        }
    } catch (error) {
        console.error('Failed to check Telegram status:', error);
    }
}

// ===== Settings Page Load =====

async function loadSettings() {
    // Load and display Telegram credentials (masked for security)
    try {
        const telegramStatus = await apiCall('/api/telegram/status');
        const connectedStatus = document.getElementById('telegramConnectedStatus');
        const authForm = document.getElementById('telegramAuth');

        if (telegramStatus.authorized) {
            // Show connected status, hide auth form
            if (connectedStatus) connectedStatus.classList.remove('hidden');
            if (authForm) authForm.classList.add('hidden');

            // Setup sign out button
            const signOutBtn = document.getElementById('telegramSignOutBtn');
            if (signOutBtn) {
                signOutBtn.onclick = async () => {
                    if (confirm('Are you sure you want to sign out from Telegram? You will need to re-authenticate.')) {
                        try {
                            await apiCall('/api/telegram/logout', { method: 'POST' });
                            showToast('Signed out from Telegram', 'success');
                            // Reload settings to show auth form
                            loadSettings();
                            checkTelegramStatus();
                        } catch (e) {
                            showToast('Failed to sign out', 'error');
                        }
                    }
                };
            }
        } else {
            // Hide connected status, show auth form
            if (connectedStatus) connectedStatus.classList.add('hidden');
            if (authForm) authForm.classList.remove('hidden');
        }
    } catch (e) {
        console.error('Failed to load Telegram settings:', e);
    }


    // Load and display Gemini config
    try {
        const geminiConfig = await apiCall('/api/gemini/config');

        if (geminiConfig.has_key) {
            const geminiInput = document.getElementById('geminiApiKey');
            if (geminiInput) {
                geminiInput.placeholder = '✅ API Key configured';
            }

            // Set model dropdown if available
            if (geminiConfig.model) {
                const modelSelect = document.getElementById('geminiModel');
                if (modelSelect) {
                    // Try to select the matching option
                    const options = Array.from(modelSelect.options);
                    const match = options.find(opt => opt.value === geminiConfig.model);
                    if (match) {
                        modelSelect.value = geminiConfig.model;
                    }
                }
            }
        }
    } catch (e) {
        console.error('Failed to load Gemini settings:', e);
    }

    // Load AI enabled status and setup toggle
    try {
        const systemStatus = await apiCall('/api/system/status');
        const toggle = document.getElementById('aiEnabledToggle');
        const statusText = document.getElementById('aiStatusText');

        if (toggle) {
            toggle.checked = systemStatus.ai_features === true;
            if (statusText) {
                statusText.textContent = toggle.checked ? 'AI Enabled' : 'AI Disabled';
                statusText.style.color = toggle.checked ? 'var(--success)' : 'var(--text-muted)';
            }

            // Add change listener
            toggle.addEventListener('change', async () => {
                try {
                    await apiCall('/api/system/control', {
                        method: 'POST',
                        body: JSON.stringify({
                            system_monitoring: true,  // Keep monitoring enabled
                            ai_features: toggle.checked
                        })
                    });

                    if (statusText) {
                        statusText.textContent = toggle.checked ? 'AI Enabled' : 'AI Disabled';
                        statusText.style.color = toggle.checked ? 'var(--success)' : 'var(--text-muted)';
                    }

                    showToast(toggle.checked ? 'AI Features Enabled' : 'AI Features Disabled', 'success');
                } catch (e) {
                    console.error('Failed to toggle AI:', e);
                    toggle.checked = !toggle.checked;  // Revert on error
                    showToast('Failed to toggle AI', 'error');
                }
            });
        }
    } catch (e) {
        console.error('Failed to load system status:', e);
    }
}

// ===== Market Overview =====

async function loadMarketOverview() {
    const container = document.getElementById('overviewContent');
    container.innerHTML = '<div class="empty-state"><span class="loading"></span><p>Loading market data...</p></div>';

    try {
        const data = await apiCall('/api/market/overview');

        let html = `
            <div class="overview-section">
                <h4>📊 Market Indices</h4>
                <div class="indices-row" style="margin-bottom: 24px;">
                    <div class="index-card nifty">
                        <div class="index-name">NIFTY 50</div>
                        <div class="index-value">${data.indices?.NIFTY50?.price?.toLocaleString('en-IN') || '--'}</div>
                        <div class="index-change ${(data.indices?.NIFTY50?.change_percent || 0) >= 0 ? 'positive' : 'negative'}">
                            ${(data.indices?.NIFTY50?.change_percent || 0) >= 0 ? '+' : ''}${(data.indices?.NIFTY50?.change_percent || 0).toFixed(2)}%
                        </div>
                    </div>
                    <div class="index-card sensex">
                        <div class="index-name">SENSEX</div>
                        <div class="index-value">${data.indices?.SENSEX?.price?.toLocaleString('en-IN') || '--'}</div>
                        <div class="index-change ${(data.indices?.SENSEX?.change_percent || 0) >= 0 ? 'positive' : 'negative'}">
                            ${(data.indices?.SENSEX?.change_percent || 0) >= 0 ? '+' : ''}${(data.indices?.SENSEX?.change_percent || 0).toFixed(2)}%
                        </div>
                    </div>
                    <div class="index-card banknifty">
                        <div class="index-name">BANK NIFTY</div>
                        <div class="index-value">${data.indices?.BANKNIFTY?.price?.toLocaleString('en-IN') || '--'}</div>
                        <div class="index-change ${(data.indices?.BANKNIFTY?.change_percent || 0) >= 0 ? 'positive' : 'negative'}">
                            ${(data.indices?.BANKNIFTY?.change_percent || 0) >= 0 ? '+' : ''}${(data.indices?.BANKNIFTY?.change_percent || 0).toFixed(2)}%
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="overview-section" style="margin-bottom: 24px;">
                <h4>🔥 Top Mentioned Stocks (24hr)</h4>
                <div class="top-stocks-grid">
                    ${data.top_stocks?.map(s => `
                        <div class="stock-tag" style="cursor: pointer;" onclick="showStockDetail('${s.symbol}')">
                            ${s.symbol} <small>(${s.mentions})</small>
                        </div>
                    `).join('') || '<p style="color: var(--text-muted);">No stocks mentioned</p>'}
                </div>
            </div>
            
            <div class="overview-section" style="margin-bottom: 24px;">
                <h4>📈 Sector-wise Analysis</h4>
                <div class="sectors-grid">
                    ${data.sectors?.map(s => `
                        <div class="sector-card" style="background: var(--bg-card); border-radius: 12px; padding: 16px; border: 1px solid var(--border-color);">
                            <div style="font-weight: 700; font-size: 16px; margin-bottom: 8px;">${s.sector}</div>
                            <div style="font-size: 13px; color: var(--text-secondary);">Mentions: ${s.count}</div>
                            <div style="margin-top: 8px; display: flex; gap: 8px; flex-wrap: wrap;">
                                ${s.stocks?.slice(0, 4).map(st => `<span class="stock-tag" onclick="showStockDetail('${st}')" style="font-size: 11px; cursor: pointer;">${st}</span>`).join('')}
                            </div>
                            <div style="margin-top: 8px; font-size: 12px;">
                                <span style="color: var(--success);">+${s.sentiment?.positive || 0}</span> / 
                                <span style="color: var(--danger);">-${s.sentiment?.negative || 0}</span>
                            </div>
                        </div>
                    `).join('') || '<p style="color: var(--text-muted);">No sector data</p>'}
                </div>
            </div>
            
            <div class="overview-section">
                <h4>📰 Latest News</h4>
                <div class="news-list">
                    ${data.latest_news?.map(n => `
                        <div class="news-card">
                            <div class="news-header">
                                <span class="news-source">${formatSource(n.source)}</span>
                                <span class="news-time">${formatTime(n.published_at)}</span>
                            </div>
                            <div class="news-title"><a href="${n.link}" target="_blank">${escapeHtml(n.title)}</a></div>
                            ${n.stocks?.length ? `<div style="margin-top: 8px;">${n.stocks.map(s => `<span class="stock-tag" data-symbol="${s}" style="cursor: pointer;">${s}</span>`).join('')}</div>` : ''}
                        </div>
                    `).join('') || '<p style="color: var(--text-muted);">No news available</p>'}
                </div>
            </div>
        `;

        container.innerHTML = html;

    } catch (error) {
        container.innerHTML = `<div class="empty-state"><span>❌</span><p>Failed to load market overview: ${error.message}</p></div>`;
    }
}

// ===== Watchlist =====

async function refreshWatchlistWithPrices() {
    const container = document.getElementById('watchlistGrid');

    // Show loading state
    container.innerHTML = `
        <div class="empty-state">
            <span class="loading"></span>
            <p>Refreshing prices...</p>
        </div>
    `;

    try {
        const data = await apiCall('/api/watchlist/refresh', { method: 'POST' });

        if (data.stocks.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <span>⭐</span>
                    <p>Your watchlist is empty. Click "+ Add Stock" to add stocks to monitor.</p>
                </div>
            `;
            return;
        }

        renderWatchlistCards(container, data.stocks);

    } catch (error) {
        container.innerHTML = `<div class="empty-state"><span>❌</span><p>Failed to refresh: ${error.message}</p></div>`;
    }
}

async function loadWatchlist() {
    const container = document.getElementById('watchlistGrid');

    try {
        const data = await apiCall('/api/watchlist');

        if (data.stocks.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <span>⭐</span>
                    <p>Your watchlist is empty. Click "+ Add Stock" to add stocks to monitor.</p>
                </div>
            `;
            return;
        }

        renderWatchlistCards(container, data.stocks);

    } catch (error) {
        container.innerHTML = `<div class="empty-state"><span>❌</span><p>Failed to load watchlist: ${error.message}</p></div>`;
    }
}

function renderWatchlistCards(container, stocks) {
    container.innerHTML = `
        <div class="watchlist-cards">
            ${stocks.map(s => `
                <div class="watchlist-card" data-symbol="${s.symbol}" style="cursor: pointer; background: var(--bg-card); border-radius: 12px; padding: 20px; border: 1px solid var(--border-color);">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <div style="font-weight: 800; font-size: 20px;">${s.symbol}</div>
                            <div style="color: var(--text-secondary); font-size: 13px;">${s.name || ''}</div>
                            ${s.sector ? `<div style="color: var(--accent-primary); font-size: 12px; margin-top: 4px;">${s.sector}</div>` : ''}
                        </div>
                        <button class="btn btn-secondary" onclick="event.stopPropagation(); removeFromWatchlist('${s.symbol}')" style="padding: 6px 12px; font-size: 12px;">✕</button>
                    </div>
                    <div style="margin-top: 16px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; text-align: center;">
                        <div>
                            <div style="color: var(--text-muted); font-size: 11px;">CURRENT</div>
                            <div style="font-weight: 700; font-size: 16px;">₹${s.current_price?.toLocaleString('en-IN') || '--'}</div>
                        </div>
                        <div>
                            <div style="color: var(--success); font-size: 11px;">TARGET</div>
                            <div style="font-weight: 700; font-size: 16px; color: var(--success);">₹${s.target_price?.toLocaleString('en-IN') || '--'}</div>
                        </div>
                        <div>
                            <div style="color: var(--danger); font-size: 11px;">STOP LOSS</div>
                            <div style="font-weight: 700; font-size: 16px; color: var(--danger);">₹${s.stop_loss?.toLocaleString('en-IN') || '--'}</div>
                        </div>
                    </div>
                    ${s.notes ? `<div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border-color); font-size: 13px; color: var(--text-secondary);">${escapeHtml(s.notes)}</div>` : ''}
                </div>
            `).join('')}
        </div>
    `;
}

// Show recommendation reasoning in a modal
function showRecommendationReasoning(symbol, timeframe, action, confidence, reasoning) {
    const timeframeLabels = {
        'next_day': 'Next Day',
        'next_week': 'Next Week',
        'next_month': 'Next Month',
        '1yr': '1 Year',
        '2yr': '2 Years',
        '5yr': '5 Years',
        '10yr': '10 Years'
    };

    const actionColors = {
        'BUY': '#22c55e',
        'SELL': '#ef4444',
        'HOLD': '#f59e0b'
    };

    const modalHtml = `
        <div id="reasoningModal" class="modal" style="display: flex;">
            <div class="modal-content" style="max-width: 500px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                    <h3 style="margin: 0;">${symbol} - ${timeframeLabels[timeframe] || timeframe}</h3>
                    <button onclick="document.getElementById('reasoningModal').remove()" style="background: none; border: none; font-size: 24px; cursor: pointer; color: var(--text-primary);">×</button>
                </div>
                <div style="display: flex; gap: 12px; margin-bottom: 16px;">
                    <span style="background: ${actionColors[action] || '#666'}; color: white; padding: 4px 12px; border-radius: 4px; font-weight: 600;">${action}</span>
                    <span style="color: var(--text-muted);">${confidence.toFixed(1)}% confidence</span>
                </div>
                <div style="background: var(--bg-tertiary); padding: 16px; border-radius: 8px; border-left: 3px solid ${actionColors[action] || '#666'};">
                    <h4 style="margin: 0 0 8px 0; color: var(--text-secondary);">📊 Why this recommendation?</h4>
                    <p style="margin: 0; color: var(--text-primary); line-height: 1.6;">${reasoning}</p>
                </div>
                <div style="margin-top: 16px; text-align: right;">
                    <button class="btn btn-primary" onclick="showStockDetail('${symbol}'); document.getElementById('reasoningModal').remove();">
                        View Full Analysis
                    </button>
                </div>
            </div>
        </div>
    `;

    // Remove existing modal if present
    const existing = document.getElementById('reasoningModal');
    if (existing) existing.remove();

    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

// Stock chart instance (for cleanup)
let stockChartInstance = null;

// Expand signal in a modal
function expandSignal(encodedSignal) {
    try {
        const signal = JSON.parse(decodeURIComponent(encodedSignal));

        // Create modal HTML
        const modalHtml = `
            <div id="signalExpandModal" class="modal" style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.8); display: flex; align-items: center; justify-content: center; z-index: 9999;" onclick="if(event.target.id === 'signalExpandModal') document.getElementById('signalExpandModal').remove()">
                <div style="background: var(--bg-secondary); border-radius: 16px; max-width: 600px; width: 90%; max-height: 80vh; overflow-y: auto; padding: 24px; border: 1px solid var(--border-color);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                        <div>
                            <span style="font-size: 11px; color: var(--text-muted);">${signal.channel_name || 'Signal'}</span>
                            <span style="font-size: 12px; font-weight: 700; padding: 2px 8px; border-radius: 4px; background: var(--accent-primary); color: #fff; margin-left: 8px;">${signal.action || 'INFO'}</span>
                        </div>
                        <button onclick="document.getElementById('signalExpandModal').remove()" style="background: none; border: none; color: var(--text-muted); cursor: pointer; font-size: 20px;">✕</button>
                    </div>
                    <div style="font-size: 14px; color: var(--text-primary); line-height: 1.7; margin-bottom: 16px; white-space: pre-wrap;">
                        ${signal.text || 'No content'}
                    </div>
                    ${signal.stocks && signal.stocks.length > 0 ? `
                        <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px;">
                            ${signal.stocks.map(s => '<span onclick="showStockDetail(\'' + s + '\'); document.getElementById(\'signalExpandModal\').remove();" style="cursor: pointer; font-size: 12px; font-weight: 600; padding: 4px 10px; background: var(--accent-primary); color: #fff; border-radius: 6px;">' + s + '</span>').join('')}
                        </div>
                    ` : ''}
                    <div style="display: flex; justify-content: space-between; align-items: center; padding-top: 16px; border-top: 1px solid var(--border-color);">
                        <span style="font-size: 11px; color: var(--text-muted);">
                            ${signal.timestamp ? new Date(signal.timestamp).toLocaleString('en-IN', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : ''}
                        </span>
                        <button onclick="searchSignalOnGoogle('${encodeURIComponent(signal.text ? signal.text.substring(0, 100) : '')}')" style="padding: 8px 16px; background: rgba(34,197,94,0.2); color: #22c55e; border: none; border-radius: 6px; cursor: pointer; font-weight: 600;">
                            🔍 Search on Google
                        </button>
                    </div>
                </div>
            </div>
        `;

        // Remove existing modal if any
        const existing = document.getElementById('signalExpandModal');
        if (existing) existing.remove();

        // Add modal to body
        document.body.insertAdjacentHTML('beforeend', modalHtml);
    } catch (e) {
        console.error('Failed to expand signal:', e);
    }
}

// Search signal content on Google
function searchSignalOnGoogle(encodedText) {
    try {
        const text = decodeURIComponent(encodedText);
        const query = text.replace(/[^a-zA-Z0-9\s]/g, ' ').trim();
        const url = 'https://www.google.com/search?q=' + encodeURIComponent(query + ' stock market india');
        window.open(url, '_blank');
    } catch (e) {
        console.error('Failed to search:', e);
    }
}

async function showStockDetail(symbol) {
    const modal = document.getElementById('stockDetailModal');
    const title = document.getElementById('stockDetailTitle');
    const categoryBadge = document.getElementById('stockCategoryBadge');

    // Show modal with loading state
    title.textContent = `Loading ${symbol}...`;
    categoryBadge.textContent = '';
    modal.classList.remove('hidden');

    try {
        const data = await apiCall(`/api/stock/${symbol}/detail`);

        // Update header
        title.textContent = `${data.symbol} - ${data.name || ''}`;
        categoryBadge.textContent = data.category || '';
        categoryBadge.className = `stock-category-badge ${(data.category || '').toLowerCase().replace(' ', '-')}`;

        // Update price overview
        document.getElementById('stockCurrentPrice').textContent =
            data.current_price ? `₹${data.current_price.toLocaleString('en-IN')}` : '--';

        const changeEl = document.getElementById('stockPriceChange');
        if (data.change_percent !== null) {
            const sign = data.change_percent >= 0 ? '+' : '';
            changeEl.textContent = `${sign}${data.change_percent?.toFixed(2) || 0}%`;
            changeEl.className = `price-change ${data.change_percent >= 0 ? 'positive' : 'negative'}`;
        }

        document.getElementById('stockDayLow').textContent =
            data.low ? `₹${data.low.toLocaleString('en-IN')}` : '--';
        document.getElementById('stockDayHigh').textContent =
            data.high ? `₹${data.high.toLocaleString('en-IN')}` : '--';
        document.getElementById('stockPrevClose').textContent =
            data.prev_close ? `₹${data.prev_close.toLocaleString('en-IN')}` : '--';

        // Update targets
        document.getElementById('stockTarget').textContent =
            data.target_price ? `₹${data.target_price.toLocaleString('en-IN')}` : '--';
        document.getElementById('stockTargetPercent').textContent =
            data.potential_gain ? `+${data.potential_gain}%` : '';
        document.getElementById('stockStopLoss').textContent =
            data.stop_loss ? `₹${data.stop_loss.toLocaleString('en-IN')}` : '--';
        document.getElementById('stockSLPercent').textContent =
            data.potential_loss ? `-${data.potential_loss}%` : '';

        // Render price chart
        renderStockChart(data.chart_data);

        // Render ratios
        renderRatios(data.ratios);

        // Render recommendations
        renderStockRecommendations(data.recommendations);

        // Render Advanced Recommendation
        renderAdvancedRecommendation(data.advanced_recommendation, data.ai_enabled);

        // Render external links
        renderExternalLinks(data.external_links, symbol);

    } catch (error) {
        console.error('Failed to load stock details:', error);
        title.textContent = `Error loading ${symbol}`;
    }
}

function renderStockChart(chartData) {
    const ctx = document.getElementById('stockChart');
    if (!ctx) return;

    // Destroy previous chart if exists
    if (stockChartInstance) {
        stockChartInstance.destroy();
    }

    if (!chartData || !chartData.closes || chartData.closes.length === 0) {
        ctx.parentElement.innerHTML = '<p style="color: var(--text-muted); text-align: center; padding: 20px;">Chart data unavailable</p>';
        return;
    }

    stockChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartData.labels,
            datasets: [{
                label: 'Price',
                data: chartData.closes,
                borderColor: '#8b5cf6',
                backgroundColor: 'rgba(139, 92, 246, 0.1)',
                fill: true,
                tension: 0.3,
                pointRadius: 0,
                pointHoverRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2.5,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#6b7280', maxTicksLimit: 7 }
                },
                y: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: {
                        color: '#6b7280',
                        callback: v => '₹' + v.toLocaleString('en-IN')
                    }
                }
            }
        }
    });
}

function renderRatios(ratios) {
    const grid = document.getElementById('stockRatiosGrid');
    if (!grid || !ratios) return;

    const ratioItems = [
        { key: 'pe_ratio', label: 'P/E Ratio' },
        { key: 'pb_ratio', label: 'P/B Ratio' },
        { key: 'dividend_yield', label: 'Div Yield %' },
        { key: 'roe', label: 'ROE %' },
        { key: 'roce', label: 'ROCE %' },
        { key: 'debt_to_equity', label: 'D/E Ratio' },
        { key: 'eps', label: 'EPS' },
        { key: 'book_value', label: 'Book Value' },
        { key: '52w_high', label: '52W High' },
        { key: '52w_low', label: '52W Low' }
    ];

    grid.innerHTML = ratioItems.map(item => `
        <div class="ratio-item">
            <span class="ratio-label">${item.label}</span>
            <span class="ratio-value">${ratios[item.key] !== null ?
            (item.key.includes('52w') ? '₹' + ratios[item.key].toLocaleString('en-IN') : ratios[item.key])
            : '--'}</span>
        </div>
    `).join('');
}

function renderStockRecommendations(recs) {
    const section = document.getElementById('stockRecsSection');
    const container = document.getElementById('stockRecsList');
    if (!container) return;

    if (!recs || recs.length === 0) {
        if (section) section.style.display = 'none';
        container.innerHTML = '';
        return;
    }

    if (section) section.style.display = 'block';

    container.innerHTML = recs.map(r => `
        <div class="rec-row">
            <span class="rec-timeframe">${r.timeframe.replace('_', ' ')}</span>
            <span class="rec-action ${r.action.toLowerCase()}">${r.action}</span>
            <span class="rec-confidence" style="font-weight: 700; color: var(--text-primary);">${r.confidence?.toFixed(0) || '--'}%</span>
            ${r.reasoning ? `<div class="rec-reasoning">${r.reasoning}</div>` : ''}
        </div>
    `).join('');
}

function renderAdvancedRecommendation(data, aiEnabled = true) {
    const container = document.getElementById('stockAdvancedRec');
    if (!container) return;

    if (!data || !data.overall_signal) {
        container.style.display = 'none';
        return;
    }

    container.style.display = 'block';

    // Update Header based on AI status
    const header = container.querySelector('h4');
    if (header) {
        if (aiEnabled) {
            header.innerHTML = `🤖 Expert AI Analysis <span style="font-size: 11px; padding: 2px 6px; background: var(--bg-secondary); border-radius: 4px; color: var(--text-muted); font-weight: normal;">BETA</span>`;
        } else {
            header.innerHTML = `📊 Technical Analysis <span style="font-size: 11px; padding: 2px 6px; background: var(--bg-secondary); border-radius: 4px; color: var(--text-muted); font-weight: normal;">ALGO</span>`;
        }
    }

    // Header
    const signalBadge = document.getElementById('recSignalBadge');
    const colors = {
        'strong_buy': '#10b981',
        'buy': '#34d399',
        'hold': '#fbbf24',
        'sell': '#f87171',
        'avoid': '#ef4444'
    };
    const color = colors[data.signal_class] || '#6b7280';

    if (signalBadge) {
        signalBadge.textContent = data.overall_signal;
        signalBadge.className = 'signal-badge ' + (data.signal_class || 'hold');
        signalBadge.style.backgroundColor = color;
        signalBadge.style.color = '#fff';
    }

    // Confidence
    const confidenceFill = document.getElementById('recConfidenceFill');
    const confidenceValue = document.getElementById('recConfidenceValue');
    const confVal = data.confidence || 0;
    if (confidenceFill) {
        confidenceFill.style.width = `${confVal}%`;
        confidenceFill.style.backgroundColor = color;
    }
    if (confidenceValue) {
        confidenceValue.textContent = `${confVal.toFixed ? confVal.toFixed(1) : confVal}%`;
    }

    // AI Verdict (New)
    const verdictEl = document.getElementById('recVerdict');
    if (verdictEl && data.ai_verdict) {
        verdictEl.textContent = data.ai_verdict;
    }

    // Rationale
    const rationale = document.getElementById('recRationale');
    if (rationale && data.expert_rationale) {
        rationale.innerHTML = `
            <div style="margin-bottom: 12px;">"${data.expert_rationale}"</div>
            ${data.action_summary ? `<div style="font-weight: 600; color: var(--accent-primary); border-top: 1px solid var(--border-color); padding-top: 8px;">💡 Action: ${data.action_summary}</div>` : ''}
        `;
    } else if (rationale) {
        rationale.innerHTML = '<div style="color: var(--text-muted); font-style: italic;">Analysis data not available for this stock.</div>';
    }

    // Scenarios (New)
    if (data.scenarios) {
        const renderList = (id, items) => {
            const list = document.getElementById(id);
            if (list && items) {
                list.innerHTML = items.map(item => `<li style="margin-bottom: 8px; font-size: 13px; color: var(--text-secondary); display: flex; gap: 8px;"><span style="color: var(--accent-primary);">•</span> ${item}</li>`).join('');
            }
        }
        renderList('recBullList', data.scenarios.bull_case);
        renderList('recBearList', data.scenarios.bear_case);
    }

    // Risk Metrics (New)
    if (data.risk_metrics) {
        const riskContainer = document.getElementById('recRiskMetrics');
        if (riskContainer) {
            const createMetric = (label, value, suffix = '', tooltip = '') => `
                <div style="background: rgba(255,255,255,0.03); padding: 10px; border-radius: 8px;">
                    <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 4px;">${label}</div>
                    <div style="font-size: 14px; font-weight: 600; color: var(--text-primary);">${value}${suffix}</div>
                </div>
             `;

            riskContainer.innerHTML = `
                ${createMetric('Volatility (30D)', data.risk_metrics.volatility_30d, '%')}
                ${createMetric('Beta', data.risk_metrics.beta, 'x')}
                ${createMetric('Max Drawdown', data.risk_metrics.max_drawdown, '%')}
                ${createMetric('VaR (95%)', data.risk_metrics.var_95, '%')}
             `;
        }

        // Add Risk Level Badge to header if exists
        // (Not implemented to keep things clean, accessible in tab)
    }

    // Technical Indicators (NewGrid)
    if (data.technical_indicators) {
        const techContainer = document.getElementById('recTechnicalGrid');
        if (techContainer) {
            const rsi = data.technical_indicators.rsi || 0;
            const rsiSignal = data.technical_indicators.rsi_signal || 'NEUTRAL';
            const rsiColor = rsi < 30 ? '#10b981' : (rsi > 70 ? '#ef4444' : '#fbbf24');

            techContainer.innerHTML = `
                <div style="background: rgba(255,255,255,0.03); padding: 8px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 12px; color: var(--text-muted);">RSI (14)</span>
                    <span style="font-size: 13px; font-weight: 600; color: ${rsiColor};">${rsi}</span>
                </div>
                 <div style="background: rgba(255,255,255,0.03); padding: 8px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 12px; color: var(--text-muted);">Trend</span>
                    <span style="font-size: 13px; font-weight: 600; color: var(--text-primary);">${data.technical_indicators.ma_20_signal || '--'} 20DMA</span>
                </div>
             `;
        }
    }

    // Factor Ratings (New)
    if (data.factor_ratings) {
        const updateFactor = (name, score) => {
            const fill = document.getElementById(`factorFill${name}`);
            const text = document.getElementById(`factorScore${name}`);
            if (fill && text) {
                fill.style.width = `${score}%`;
                text.textContent = score;
                // Color coding
                if (score >= 70) fill.style.backgroundColor = '#10b981'; // Green
                else if (score >= 40) fill.style.backgroundColor = '#fbbf24'; // Yellow
                else fill.style.backgroundColor = '#ef4444'; // Red
            }
        };

        updateFactor('Value', data.factor_ratings.value || 0);
        updateFactor('Growth', data.factor_ratings.growth || 0);
        updateFactor('Safety', data.factor_ratings.safety || 0);
        updateFactor('Quality', data.factor_ratings.quality || 0);
    }

    // Factors
    const factorsList = document.getElementById('recFactorsList');
    if (factorsList && data.key_factors && Array.isArray(data.key_factors)) {
        factorsList.innerHTML = data.key_factors.map(f => {
            const isPos = f.impact === 'positive';
            const textColor = isPos ? '#10b981' : '#ef4444';
            const bg = isPos ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)';
            const border = isPos ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)';

            return `<div class="factor-tag" style="font-size: 11px; padding: 4px 8px; border-radius: 4px; background: ${bg}; color: ${textColor}; border: 1px solid ${border}; white-space: nowrap;">
                ${isPos ? '▲' : '▼'} ${f.factor}
            </div>`;
        }).join('');
    }

    // Timeframes
    const renderTimeframe = (id, tfData) => {
        const el = document.getElementById(id);
        if (!el) return;

        const signalEl = el.querySelector('.tf-signal');
        if (tfData) {
            signalEl.textContent = tfData.signal;
            const tfColor = colors[tfData.signal.toLowerCase().replace(' ', '_')] || '#6b7280';
            signalEl.style.color = tfColor;
            el.style.borderColor = tfColor + '40'; // Low opacity border
        } else {
            signalEl.textContent = '--';
        }
    };

    if (data.timeframe_recommendations) {
        renderTimeframe('tfIntraday', data.timeframe_recommendations.intraday);
        renderTimeframe('tfShortTerm', data.timeframe_recommendations.short_term);
        renderTimeframe('tfMidTerm', data.timeframe_recommendations.medium_term);
        renderTimeframe('tfLongTerm', data.timeframe_recommendations.long_term);
    }
}

function renderExternalLinks(links, symbol) {
    const container = document.getElementById('stockExternalLinks');
    if (!container || !links) return;

    const linkItems = [
        { key: 'screener', label: 'Screener', icon: '📊' },
        { key: 'nse', label: 'NSE', icon: '🏛️' },
        { key: 'bse', label: 'BSE', icon: '🏦' },
        { key: 'moneycontrol', label: 'MoneyControl', icon: '💰' },
        { key: 'tradingview', label: 'TradingView', icon: '📈' }
    ];

    // External links
    let html = linkItems.map(item =>
        links[item.key] ? `<a href="${links[item.key]}" target="_blank" class="external-link-btn">${item.icon} ${item.label}</a>` : ''
    ).join('');

    // Add Research Console link - using window. prefix for reliable global access
    html += `<a href="javascript:void(0)" onclick="window.openResearchForStock('${symbol}')" class="external-link-btn" style="background: var(--accent-gradient); color: #fff;">🔬 Research</a>`;

    container.innerHTML = html;
}

function openResearchForStock(symbol) {
    console.log('[Research] Opening research for stock:', symbol);

    try {
        // Close the modal
        const modal = document.getElementById('stockDetailModal');
        if (modal) modal.classList.add('hidden');

        // Switch to Research section
        switchSection('research');

        // Use setTimeout to ensure DOM is ready after section switch
        setTimeout(() => {
            // Populate the research input and trigger search
            const input = document.getElementById('researchSearchInput');
            console.log('[Research] Input element found:', !!input, 'Symbol:', symbol);
            if (input) {
                input.value = symbol;
                loadResearchData(symbol);
            } else {
                console.error('[Research] Could not find researchSearchInput element');
                showToast('Error: Research input not found', 'error');
            }
        }, 300);  // Increased delay to ensure DOM is ready
    } catch (e) {
        console.error('[Research] Error:', e);
        showToast('Research error: ' + e.message, 'error');
    }
}

// Make globally accessible for onclick handlers
window.openResearchForStock = openResearchForStock;


async function removeFromWatchlist(symbol) {
    if (!confirm(`Remove ${symbol} from watchlist?`)) return;

    try {
        await apiCall(`/api/watchlist/${symbol}`, { method: 'DELETE' });
        watchlistCache.delete(symbol.toUpperCase());
        showToast(`${symbol} removed from watchlist`, 'success', 4000);
        loadWatchlist();
    } catch (error) {
        showToast('Failed to remove: ' + error.message, 'error', 5000);
    }
}

// Cache for watchlist status - refreshed on load
let watchlistCache = new Set();

async function refreshWatchlistCache() {
    try {
        const data = await apiCall('/api/watchlist');
        watchlistCache = new Set((data.stocks || []).map(s => s.symbol.toUpperCase()));
    } catch (error) {
        console.error('Failed to refresh watchlist cache:', error);
    }
}

// Toggle watchlist - add or remove based on current state
async function toggleWatchlist(symbol, event) {
    // Prevent card click from triggering
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }

    const btn = event ? event.currentTarget : null;
    const upperSymbol = symbol.toUpperCase();
    const isInWatchlist = watchlistCache.has(upperSymbol);

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '⏳';
    }

    try {
        if (isInWatchlist) {
            // Remove from watchlist
            await apiCall(`/api/watchlist/${upperSymbol}`, { method: 'DELETE' });
            watchlistCache.delete(upperSymbol);

            if (btn) {
                btn.innerHTML = '⭐';
                btn.style.background = 'rgba(255,255,255,0.1)';
                btn.title = 'Add to Watchlist';
            }
            showToast(`${upperSymbol} removed from watchlist`, 'info', 3000);
        } else {
            // Add to watchlist
            await apiCall('/api/watchlist', {
                method: 'POST',
                body: JSON.stringify({ symbol: upperSymbol })
            });
            watchlistCache.add(upperSymbol);

            if (btn) {
                btn.innerHTML = '✓';
                btn.style.background = '#10b981';
                btn.title = 'In Watchlist - Click to remove';
            }
            showToast(`${upperSymbol} added to watchlist`, 'success', 3000);
        }

        // Refresh watchlist page if visible
        if (currentSection === 'watchlist') {
            loadWatchlist();
        }
    } catch (error) {
        if (btn) {
            btn.innerHTML = isInWatchlist ? '✓' : '⭐';
            btn.disabled = false;
        }
        console.error('Watchlist toggle failed:', error);
        showToast('Failed: ' + error.message, 'error');
    } finally {
        if (btn) btn.disabled = false;
    }
}

// Legacy alias removed - was causing infinite recursion
// toggleWatchlist is already defined above

// Setup watchlist modal handlers
document.addEventListener('DOMContentLoaded', () => {
    // Add to watchlist modal
    const addBtn = document.getElementById('addWatchlistBtn');
    const addModal = document.getElementById('addWatchlistModal');
    const cancelBtn = document.getElementById('cancelWatchlist');

    if (addBtn) addBtn.addEventListener('click', () => addModal.classList.remove('hidden'));
    if (cancelBtn) cancelBtn.addEventListener('click', () => addModal.classList.add('hidden'));
    if (addModal) addModal.addEventListener('click', (e) => { if (e.target === addModal) addModal.classList.add('hidden'); });

    // Stock symbol autocomplete
    const symbolInput = document.getElementById('watchlistSymbol');
    const suggestionsDiv = document.getElementById('stockSuggestions');
    let searchTimeout = null;

    if (symbolInput && suggestionsDiv) {
        symbolInput.addEventListener('input', (e) => {
            const query = e.target.value.trim();

            // Clear previous timeout
            if (searchTimeout) clearTimeout(searchTimeout);

            if (query.length < 1) {
                suggestionsDiv.style.display = 'none';
                return;
            }

            // Debounce search
            searchTimeout = setTimeout(async () => {
                try {
                    const data = await apiCall(`/api/stocks/search?q=${encodeURIComponent(query)}`);

                    if (data.results && data.results.length > 0) {
                        suggestionsDiv.innerHTML = data.results.map(stock => `
                            <div class="stock-suggestion" data-symbol="${stock.symbol}" data-name="${stock.name}" style="padding: 12px 16px; cursor: pointer; border-bottom: 1px solid var(--border-color); transition: background 0.15s;">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <strong style="color: var(--text-primary);">${stock.symbol}</strong>
                                    <span style="font-size: 11px; padding: 2px 8px; background: rgba(139, 92, 246, 0.15); color: var(--accent-secondary); border-radius: 99px;">${stock.sector}</span>
                                </div>
                                <div style="font-size: 13px; color: var(--text-secondary); margin-top: 2px;">${stock.name}</div>
                            </div>
                        `).join('');
                        suggestionsDiv.style.display = 'block';

                        // Add hover effects and click handlers
                        suggestionsDiv.querySelectorAll('.stock-suggestion').forEach(item => {
                            item.addEventListener('mouseenter', () => item.style.background = 'var(--bg-card)');
                            item.addEventListener('mouseleave', () => item.style.background = 'transparent');
                            item.addEventListener('click', () => {
                                symbolInput.value = item.dataset.symbol;
                                suggestionsDiv.style.display = 'none';
                            });
                        });
                    } else {
                        suggestionsDiv.innerHTML = '<div style="padding: 12px 16px; color: var(--text-muted);">No stocks found</div>';
                        suggestionsDiv.style.display = 'block';
                    }
                } catch (error) {
                    console.error('Search error:', error);
                }
            }, 200); // 200ms debounce
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!symbolInput.contains(e.target) && !suggestionsDiv.contains(e.target)) {
                suggestionsDiv.style.display = 'none';
            }
        });

        // Hide dropdown on Escape
        symbolInput.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') suggestionsDiv.style.display = 'none';
        });
    }

    // Add watchlist form
    const form = document.getElementById('addWatchlistForm');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();

            const submitBtn = form.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.textContent = 'Adding...';
            submitBtn.disabled = true;

            const symbol = document.getElementById('watchlistSymbol').value;
            const targetPrice = document.getElementById('watchlistTarget').value;
            const stopLoss = document.getElementById('watchlistStopLoss').value;
            const notes = document.getElementById('watchlistNotes').value;

            try {
                const result = await apiCall('/api/watchlist', {
                    method: 'POST',
                    body: JSON.stringify({
                        symbol,
                        target_price: targetPrice ? parseFloat(targetPrice) : null,
                        stop_loss: stopLoss ? parseFloat(stopLoss) : null,
                        notes: notes || null
                    })
                });

                addModal.classList.add('hidden');
                form.reset();
                loadWatchlist();

                // Show success with auto-calculated info
                showToast(`${symbol.toUpperCase()} added with auto-calculated targets!`, 'success');
            } catch (error) {
                showToast('Failed to add stock: ' + error.message, 'error');
            } finally {
                submitBtn.textContent = originalText;
                submitBtn.disabled = false;
            }
        });
    }


    // Stock detail modal close
    const closeBtn = document.getElementById('closeStockDetail');
    const detailModal = document.getElementById('stockDetailModal');
    if (closeBtn) closeBtn.addEventListener('click', () => detailModal.classList.add('hidden'));
    if (detailModal) detailModal.addEventListener('click', (e) => { if (e.target === detailModal) detailModal.classList.add('hidden'); });

    // Analyze market button
    const analyzeBtn = document.getElementById('analyzeMarketBtn');
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', () => triggerMarketAnalysis());
    }
});

async function triggerMarketAnalysis() {
    const analyzeBtn = document.getElementById('analyzeMarketBtn');
    if (analyzeBtn) {
        analyzeBtn.disabled = true;
        analyzeBtn.innerHTML = '<span class="loading"></span> Analyzing...';
    }

    try {
        showToast('Running comprehensive market analysis...', 'info');
        const result = await apiCall('/api/market/analyze', { method: 'POST' });

        // Show detailed analysis results
        const analysis = result.analysis || {};
        const topStocks = (analysis.top_stocks || []).slice(0, 5).map(s => s[0]).join(', ');
        const messagesAnalyzed = analysis.messages_analyzed || 0;
        const newsAnalyzed = analysis.news_analyzed || 0;
        const recsCount = result.recommendations_count || 0;

        // Build summary message
        let summary = `✅ Analysis Complete!<br>`;
        summary += `📊 ${messagesAnalyzed} messages + ${newsAnalyzed} news analyzed<br>`;
        if (topStocks) {
            summary += `🔥 Trending: ${topStocks}<br>`;
        }
        summary += `💡 ${recsCount} new recommendations generated`;

        showToast(summary, 'success', 8000);

        // Reload the market overview to show updated data
        loadMarketOverview();

        // Also refresh signals if on home page
        if (typeof loadLiveSignals === 'function') {
            loadLiveSignals();
        }

    } catch (error) {
        console.error('Analysis failed:', error);
        showToast('Analysis failed: ' + error.message, 'error');
    } finally {
        if (analyzeBtn) {
            analyzeBtn.disabled = false;
            analyzeBtn.innerHTML = '🔍 Analyze Market';
        }
    }
}

// ===== Utilities =====

function formatTime(isoString) {
    if (!isoString) return '--';
    const date = new Date(isoString);
    return date.toLocaleString('en-IN', {
        day: '2-digit',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatSource(source) {
    const names = {
        economic_times: 'Economic Times',
        economic_times_stocks: 'ET Stocks',
        moneycontrol: 'Moneycontrol'
    };
    return names[source] || source;
}

// ===== UI Helpers =====

function scrollContainer(id, amount) {
    const container = document.getElementById(id);
    if (container) {
        container.scrollBy({
            left: amount,
            behavior: 'smooth'
        });
    }
}

// Back to Top button logic
const backToTopBtn = document.getElementById('backToTop');
if (backToTopBtn) {
    window.addEventListener('scroll', () => {
        if (window.pageYOffset > 300) {
            backToTopBtn.classList.add('visible');
        } else {
            backToTopBtn.classList.remove('visible');
        }
    });

    backToTopBtn.addEventListener('click', () => {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });
}
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}


// ===== PREMIUM FEATURES =====

// Hero Search
document.addEventListener('DOMContentLoaded', () => {
    setupHeroSearch();
    setupScreener();
    setupResearchConsole();
});

// Stock list cache for instant local search
let stockListCache = [];
let stockListLoaded = false;

// Pre-load stock list on first search focus
async function preloadStockList() {
    if (stockListLoaded) return;
    try {
        const response = await fetch(`${API_BASE}/api/stocks/list`);
        if (response.ok) {
            stockListCache = await response.json();
            stockListLoaded = true;
        }
    } catch (e) {
        console.debug('Could not preload stock list:', e);
    }
}

// Highlight matching text in a string
function highlightMatch(text, query) {
    if (!query) return text;
    const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    return text.replace(regex, '<mark class="search-highlight">$1</mark>');
}

function setupHeroSearch() {
    const searchInput = document.getElementById('heroSearchInput');
    const searchResults = document.getElementById('heroSearchResults');

    if (!searchInput) return;

    let selectedIndex = -1;
    let currentResults = [];

    // Pre-load stock list when user focuses the search
    searchInput.addEventListener('focus', preloadStockList);

    // Local search in cache for instant results
    function localSearch(query) {
        if (!query || query.length < 1 || !stockListLoaded) return [];
        const q = query.toLowerCase();
        const qUpper = query.toUpperCase();

        // Priority: exact symbol > starts with > contains in symbol > contains in name
        const results = [];
        const seen = new Set();

        // Exact match
        for (const s of stockListCache) {
            if (s.symbol === qUpper && !seen.has(s.symbol)) {
                results.push({ ...s, sector: s.sector || 'General' });
                seen.add(s.symbol);
            }
        }

        // Symbol starts with
        for (const s of stockListCache) {
            if (s.symbol.startsWith(qUpper) && !seen.has(s.symbol)) {
                results.push({ ...s, sector: s.sector || 'General' });
                seen.add(s.symbol);
                if (results.length >= 8) break;
            }
        }

        // Symbol contains
        if (results.length < 8) {
            for (const s of stockListCache) {
                if (s.symbol.includes(qUpper) && !seen.has(s.symbol)) {
                    results.push({ ...s, sector: s.sector || 'General' });
                    seen.add(s.symbol);
                    if (results.length >= 8) break;
                }
            }
        }

        // Name contains
        if (results.length < 8) {
            for (const s of stockListCache) {
                if (s.name && s.name.toLowerCase().includes(q) && !seen.has(s.symbol)) {
                    results.push({ ...s, sector: s.sector || 'General' });
                    seen.add(s.symbol);
                    if (results.length >= 8) break;
                }
            }
        }

        return results.slice(0, 8);
    }

    function renderResults(results, query) {
        currentResults = results;
        selectedIndex = -1;

        if (results.length > 0) {
            searchResults.innerHTML = results.map((stock, idx) => `
                <div class="search-result-item${idx === selectedIndex ? ' selected' : ''}" data-symbol="${stock.symbol}" data-index="${idx}">
                    <span class="search-result-symbol">${highlightMatch(stock.symbol, query)}</span>
                    <span class="search-result-name">${highlightMatch(stock.name, query)}</span>
                    <span class="search-result-sector">${stock.sector}</span>
                </div>
            `).join('');
            searchResults.classList.add('active');

            // Add click handlers
            searchResults.querySelectorAll('.search-result-item').forEach(item => {
                item.addEventListener('click', () => {
                    const symbol = item.dataset.symbol;
                    searchResults.classList.remove('active');
                    searchInput.value = '';
                    showStockDetail(symbol);
                });
            });
        } else {
            searchResults.innerHTML = '<div class="search-result-item"><span class="search-result-name">No results found</span></div>';
            searchResults.classList.add('active');
        }
    }

    function updateSelection() {
        searchResults.querySelectorAll('.search-result-item').forEach((item, idx) => {
            if (idx === selectedIndex) {
                item.classList.add('selected');
                item.scrollIntoView({ block: 'nearest' });
            } else {
                item.classList.remove('selected');
            }
        });
    }

    // API search with debounce
    const apiSearch = debounce(async (query) => {
        try {
            const response = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(query)}&limit=8`);
            const data = await response.json();
            if (data.results) {
                renderResults(data.results, query);
            }
        } catch (error) {
            console.error('Search error:', error);
        }
    }, 100);

    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.trim();
        if (query.length < 1) {
            searchResults.classList.remove('active');
            return;
        }

        // Instant local search first
        const localResults = localSearch(query);
        if (localResults.length > 0) {
            renderResults(localResults, query);
        }

        // Also fetch from API for more complete results
        apiSearch(query);
    });

    searchInput.addEventListener('keydown', (e) => {
        if (!searchResults.classList.contains('active')) return;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            if (selectedIndex < currentResults.length - 1) {
                selectedIndex++;
                updateSelection();
            }
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            if (selectedIndex > 0) {
                selectedIndex--;
                updateSelection();
            }
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (selectedIndex >= 0 && selectedIndex < currentResults.length) {
                const symbol = currentResults[selectedIndex].symbol;
                searchResults.classList.remove('active');
                searchInput.value = '';
                showStockDetail(symbol);
            } else if (currentResults.length > 0) {
                // Select first result if none selected
                const symbol = currentResults[0].symbol;
                searchResults.classList.remove('active');
                searchInput.value = '';
                showStockDetail(symbol);
            }
        } else if (e.key === 'Escape') {
            searchResults.classList.remove('active');
        }
    });

    // Close on click outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.hero-search')) {
            searchResults.classList.remove('active');
        }
    });
}


// ===== ENHANCED STOCK SCREENER =====

// Cache for screens data
let screensCache = null;
let currentCategoryFilter = 'all';

async function loadScreensData() {
    if (screensCache) return screensCache;
    try {
        const response = await fetch(`${API_BASE}/api/screens`);
        screensCache = await response.json();
        return screensCache;
    } catch (error) {
        console.error('Failed to load screens:', error);
        return null;
    }
}

function setupScreener() {
    // Load screens and populate dropdown
    loadAndPopulateScreenDropdown();

    // Consolidated scan button (on original screener page)
    const consolidatedBtn = document.getElementById('runConsolidatedBtn');
    if (consolidatedBtn) {
        consolidatedBtn.addEventListener('click', runConsolidatedScreening);
    }

    // View toggle
    document.querySelectorAll('.view-toggle-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.view-toggle-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const view = btn.dataset.view;
            document.getElementById('screenerBrowseView').classList.toggle('hidden', view !== 'browse');
            document.getElementById('screenerConsolidatedView').classList.toggle('hidden', view !== 'consolidated');
            document.getElementById('screenDetailPanel').classList.add('hidden');
        });
    });

    // Screen Dropdown change handler
    const screenDropdown = document.getElementById('screenDropdown');
    const runScreenBtn = document.getElementById('runSelectedScreenBtn');

    if (screenDropdown) {
        screenDropdown.addEventListener('change', () => {
            const selectedId = screenDropdown.value;
            if (selectedId && screensCache) {
                const screen = screensCache.screens.find(s => s.id === selectedId);
                if (screen) {
                    showScreenInfo(screen);
                    runScreenBtn.disabled = false;
                }
            } else {
                document.getElementById('screenInfoBox').classList.add('hidden');
                runScreenBtn.disabled = true;
            }
        });
    }

    // Run selected screen button
    if (runScreenBtn) {
        runScreenBtn.addEventListener('click', async () => {
            const screenId = screenDropdown.value;
            if (screenId) {
                await runScreenFromDropdown(screenId);
            }
        });
    }

    // Back button
    const backBtn = document.getElementById('backToScreensBtn');
    if (backBtn) {
        backBtn.addEventListener('click', () => {
            document.getElementById('screenDetailPanel').classList.add('hidden');
            document.getElementById('screenerBrowseView').classList.remove('hidden');
        });
    }

    // Setup All Screens tab
    setupAllScreensTab();
}

async function loadAndPopulateScreenDropdown() {
    const data = await loadScreensData();
    if (!data) return;

    document.getElementById('screenCount').textContent = `${data.total} Screens`;

    // Populate dropdown grouped by category
    const dropdown = document.getElementById('screenDropdown');
    if (!dropdown) return;

    // Group screens by category
    const categories = {};
    data.screens.forEach(screen => {
        const cat = screen.category || 'Other';
        if (!categories[cat]) categories[cat] = [];
        categories[cat].push(screen);
    });

    // Build optgroup HTML
    let html = '<option value="">-- Choose a Screen --</option>';
    Object.keys(categories).sort().forEach(cat => {
        const icon = getCategoryIcon(cat);
        html += `<optgroup label="${icon} ${cat}">`;
        categories[cat].forEach(screen => {
            const recBadge = screen.recommended_for_fresh_entry ? ' ⭐' : '';
            html += `<option value="${screen.id}">${screen.name}${recBadge}</option>`;
        });
        html += '</optgroup>';
    });

    dropdown.innerHTML = html;
}

function showScreenInfo(screen) {
    const infoBox = document.getElementById('screenInfoBox');
    if (!infoBox) return;

    document.getElementById('screenInfoName').textContent = screen.name;
    const catEl = document.getElementById('screenInfoCategory');
    catEl.textContent = `${getCategoryIcon(screen.category)} ${screen.category}`;
    document.getElementById('screenInfoDefinition').textContent = screen.definition || '--';

    // Enhanced summary with difficulty and risk
    const diffColor = screen.difficulty === 'Beginner' ? '#22c55e' : screen.difficulty === 'Intermediate' ? '#f59e0b' : '#ef4444';
    const riskColor = screen.risk_level === 'Low' ? '#22c55e' : screen.risk_level === 'Medium' ? '#f59e0b' : '#ef4444';
    const summaryEl = document.getElementById('screenInfoSummary');
    summaryEl.innerHTML = `${screen.summary || '--'}
        <div style="display: flex; gap: 12px; margin-top: 10px; flex-wrap: wrap;">
            <span class="difficulty-badge" style="background: ${diffColor}20; color: ${diffColor}; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600;">${screen.difficulty || 'Intermediate'}</span>
            <span class="risk-badge" style="background: ${riskColor}20; color: ${riskColor}; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600;">Risk: ${screen.risk_level || 'Medium'}</span>
            ${screen.why_it_matters ? `<span style="color: var(--text-muted); font-size: 12px; font-style: italic;">💡 ${screen.why_it_matters}</span>` : ''}
        </div>`;

    const rating = screen.fresh_entry_rating || 3;
    document.getElementById('screenInfoRating').textContent = '★'.repeat(rating) + '☆'.repeat(5 - rating);

    infoBox.classList.remove('hidden');
}

async function runScreenFromDropdown(screenId) {
    const resultsEl = document.getElementById('screenResultsContainer');
    const runBtn = document.getElementById('runSelectedScreenBtn');

    runBtn.disabled = true;
    runBtn.innerHTML = '⏳ Running...';
    resultsEl.innerHTML = '<div class="empty-state"><span class="loading"></span><p>Fetching real-time data...</p></div>';

    try {
        const response = await fetch(`${API_BASE}/api/screens/${screenId}/run`);
        const data = await response.json();

        if (data.stocks && data.stocks.length > 0) {
            resultsEl.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                    <span style="color: var(--text-secondary);">${data.matches} stocks matched</span>
                    <span style="font-size: 12px; color: var(--text-muted);">Scanned ${data.total_scanned} stocks (${data.live_data_count} live)</span>
                </div>
                <div class="screener-results-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px;">
                    ${data.stocks.map(stock => renderScreenerStockCard(stock)).join('')}
                </div>
            `;
        } else {
            resultsEl.innerHTML = '<div class="empty-state"><span>📋</span><p>No stocks match this screen criteria</p></div>';
        }
    } catch (error) {
        console.error('Screen error:', error);
        resultsEl.innerHTML = '<div class="empty-state"><span>❌</span><p>Error running screen</p></div>';
    } finally {
        runBtn.disabled = false;
        runBtn.innerHTML = '▶️ Run Screen';
    }
}

function setupAllScreensTab() {
    const runAllBtn = document.getElementById('runAllScreensBtn');
    if (runAllBtn) {
        runAllBtn.addEventListener('click', runAllScreensScan);
    }
}

async function runAllScreensScan() {
    const btn = document.getElementById('runAllScreensBtn');
    const progressEl = document.getElementById('allScreensScanProgress');
    const statsEl = document.getElementById('allScreensStats');
    const freshPicksEl = document.getElementById('allScreensFreshPicks');
    const allPicksEl = document.getElementById('allScreensAllPicks');

    // Show progress, hide stats
    btn.disabled = true;
    btn.innerHTML = '⏳ Scanning...';
    progressEl.classList.remove('hidden');
    statsEl.classList.add('hidden');

    // Simulate progress (since API doesn't stream progress)
    let progress = 0;
    const progressText = document.getElementById('allScreensProgressText');
    const progressPercent = document.getElementById('allScreensProgressPercent');
    const progressBar = document.getElementById('allScreensProgressBar');

    const progressInterval = setInterval(() => {
        if (progress < 90) {
            progress += Math.random() * 15;
            progress = Math.min(progress, 90);
            progressBar.style.width = `${progress}%`;
            progressPercent.textContent = `${Math.round(progress)}%`;

            if (progress < 30) progressText.textContent = 'Fetching stock data...';
            else if (progress < 60) progressText.textContent = 'Running screens...';
            else progressText.textContent = 'Aggregating results...';
        }
    }, 500);

    try {
        // Fetch with force_refresh to bypass cache
        const response = await fetch(`${API_BASE}/api/screens/consolidated?force_refresh=true`);
        const data = await response.json();

        clearInterval(progressInterval);
        progressBar.style.width = '100%';
        progressPercent.textContent = '100%';
        progressText.textContent = 'Complete!';

        // Update stats
        setTimeout(() => {
            progressEl.classList.add('hidden');
            statsEl.classList.remove('hidden');

            document.getElementById('allScreensStocksScanned').textContent = data.total_stocks_scanned || 0;
            document.getElementById('allScreensScreensRun').textContent = data.total_screens_run || 0;
            document.getElementById('allScreensMatchingStocks').textContent = data.aggregated_picks?.length || 0;
            document.getElementById('allScreensTimestamp').textContent = new Date().toLocaleTimeString();
        }, 500);

        // Render fresh picks
        if (data.fresh_entry_picks && data.fresh_entry_picks.length > 0) {
            freshPicksEl.innerHTML = data.fresh_entry_picks.map(pick => renderAllScreensCard(pick, true)).join('');
        } else {
            freshPicksEl.innerHTML = '<div class="empty-state" style="grid-column: 1 / -1;"><span>⭐</span><p>No high-confidence picks found</p></div>';
        }

        // Render all picks
        if (data.aggregated_picks && data.aggregated_picks.length > 0) {
            allPicksEl.innerHTML = data.aggregated_picks.map(pick => renderAllScreensCard(pick, false)).join('');
        } else {
            allPicksEl.innerHTML = '<div class="empty-state" style="grid-column: 1 / -1;"><span>📋</span><p>No multi-screen matches found</p></div>';
        }

    } catch (error) {
        console.error('All screens scan error:', error);
        clearInterval(progressInterval);
        progressEl.classList.add('hidden');
        freshPicksEl.innerHTML = '<div class="empty-state" style="grid-column: 1 / -1;"><span>❌</span><p>Error running scan</p></div>';
    } finally {
        btn.disabled = false;
        btn.innerHTML = '⚡ Scan All 50+ Screens';
    }
}

function renderAllScreensCard(pick, isFresh) {
    const ratingStars = '★'.repeat(Math.round(pick.fresh_entry_rating || 0)) + '☆'.repeat(5 - Math.round(pick.fresh_entry_rating || 0));
    const borderColor = isFresh ? 'rgba(34, 197, 94, 0.4)' : 'var(--border-color)';

    return `
        <div class="allscreens-pick-card" onclick="showStockDetail('${pick.symbol}')" style="background: var(--bg-secondary); padding: 16px; border-radius: 12px; border: 1px solid ${borderColor}; cursor: pointer;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                <div>
                    <span style="font-size: 16px; font-weight: 700;">${pick.symbol}</span>
                    <span style="font-size: 12px; color: var(--text-muted); margin-left: 8px;">${pick.name || ''}</span>
                </div>
                <span style="font-size: 12px; background: var(--accent-primary); color: #fff; padding: 2px 8px; border-radius: 4px;">${pick.screens_matched} screens</span>
            </div>
            <div style="display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 8px;">
                ${pick.categories.map(c => `<span style="font-size: 10px; background: var(--bg-tertiary); padding: 2px 6px; border-radius: 4px;">${getCategoryIcon(c)} ${c}</span>`).join('')}
            </div>
            <p style="font-size: 12px; color: var(--text-secondary); margin: 8px 0; line-height: 1.4;">${pick.rationale || ''}</p>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px; font-size: 11px;">
                <span style="color: #f59e0b;">${ratingStars}</span>
                <div style="color: var(--text-muted);">
                    PE: ${pick.fundamentals?.pe || '--'} | ROE: ${pick.fundamentals?.roe ? pick.fundamentals.roe.toFixed(1) + '%' : '--'}
                </div>
            </div>
        </div>
    `;
}

async function loadAndRenderScreens() {
    const data = await loadScreensData();
    if (!data) return;

    document.getElementById('screenCount').textContent = `${data.total} Screens`;

    // Populate glossary if available
    if (data.glossary) {
        populateGlossary(data.glossary);
    }

    // Setup category filter tabs
    setupCategoryFilterTabs();

    // Setup glossary modal
    setupGlossaryModal();
}

function setupCategoryFilterTabs() {
    document.querySelectorAll('.category-tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.category-tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const category = btn.dataset.category;
            currentCategoryFilter = category;
            renderScreensGrid();

            // Also filter dropdown
            filterScreenDropdown(category);
        });
    });
}

function filterScreenDropdown(category) {
    if (!screensCache) return;
    const dropdown = document.getElementById('screenDropdown');
    if (!dropdown) return;

    const screens = screensCache.screens;
    let filtered = screens;
    if (category === 'beginner') {
        filtered = screens.filter(s => s.difficulty === 'Beginner');
    } else if (category !== 'all') {
        filtered = screens.filter(s => s.category === category);
    }

    let html = '<option value="">-- Choose a Screen --</option>';
    const groups = {};
    filtered.forEach(s => {
        if (!groups[s.category]) groups[s.category] = [];
        groups[s.category].push(s);
    });
    Object.entries(groups).forEach(([cat, items]) => {
        html += `<optgroup label="${getCategoryIcon(cat)} ${cat}">`;
        items.forEach(s => {
            const badge = s.difficulty === 'Beginner' ? ' 🌱' : s.difficulty === 'Advanced' ? ' 🔥' : '';
            html += `<option value="${s.id}">${s.name}${badge}</option>`;
        });
        html += '</optgroup>';
    });
    dropdown.innerHTML = html;
}

function setupGlossaryModal() {
    const openBtn = document.getElementById('openGlossaryBtn');
    const closeBtn = document.getElementById('closeGlossaryBtn');
    const modal = document.getElementById('glossaryModal');

    if (openBtn && modal) {
        openBtn.addEventListener('click', () => modal.classList.remove('hidden'));
    }
    if (closeBtn && modal) {
        closeBtn.addEventListener('click', () => modal.classList.add('hidden'));
    }
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.classList.add('hidden');
        });
    }
}

function populateGlossary(glossary) {
    const container = document.getElementById('glossaryContent');
    if (!container || !glossary) return;

    container.innerHTML = Object.entries(glossary).map(([key, item]) => `
        <div class="glossary-item" style="background: var(--bg-secondary); border-radius: 12px; padding: 16px; border: 1px solid var(--border-color);">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                <span style="font-size: 20px;">${item.icon}</span>
                <h4 style="margin: 0; font-size: 15px; font-weight: 700;">${item.name}</h4>
            </div>
            <p style="color: var(--text-primary); font-size: 14px; margin: 0 0 8px 0; line-height: 1.5;">${item.simple}</p>
            <div style="background: var(--bg-tertiary); padding: 10px; border-radius: 8px; margin-bottom: 8px;">
                <span style="font-size: 11px; color: var(--text-muted); text-transform: uppercase;">Example</span>
                <p style="margin: 4px 0 0; font-size: 13px; color: var(--text-secondary);">${item.example}</p>
            </div>
            <div style="display: flex; gap: 12px; font-size: 12px;">
                <span style="color: #22c55e;">✅ Good: ${item.good_range}</span>
                <span style="color: #ef4444;">⚠️ Concern: ${item.warning_range}</span>
            </div>
        </div>
    `).join('');
}

// Color-coded metric rendering with tooltip
function colorMetric(key, value, suffix = '') {
    if (value === null || value === undefined || value === '--') {
        return `<span style="font-weight: 500; color: var(--text-muted);">--</span>`;
    }

    let color = 'var(--text-primary)';
    let tooltipText = '';

    const glossary = screensCache?.glossary || {};
    if (glossary[key]) {
        tooltipText = glossary[key].simple;
    }

    switch (key) {
        case 'pe':
            color = value < 15 ? '#22c55e' : value < 25 ? '#f59e0b' : value < 40 ? '#fb923c' : '#ef4444';
            break;
        case 'roe':
            color = value > 25 ? '#22c55e' : value > 15 ? '#a3e635' : value > 8 ? '#f59e0b' : '#ef4444';
            break;
        case 'roce':
            color = value > 25 ? '#22c55e' : value > 18 ? '#a3e635' : value > 10 ? '#f59e0b' : '#ef4444';
            break;
        case 'de':
            color = value < 0.3 ? '#22c55e' : value < 1 ? '#a3e635' : value < 1.5 ? '#f59e0b' : '#ef4444';
            break;
        case 'pb':
            color = value < 1 ? '#22c55e' : value < 3 ? '#a3e635' : value < 6 ? '#f59e0b' : '#ef4444';
            break;
        case 'div_yield':
            color = value > 3 ? '#22c55e' : value > 1.5 ? '#a3e635' : value > 0 ? '#f59e0b' : 'var(--text-muted)';
            break;
    }

    const displayVal = typeof value === 'number' ? (key === 'de' || key === 'pb' ? value.toFixed(2) : value.toFixed(1)) : value;
    const tooltip = tooltipText ? `title="${tooltipText}"` : '';

    return `<span class="metric-colored" style="font-weight: 600; color: ${color}; cursor: help;" ${tooltip}>${displayVal}${suffix}</span>`;
}

function renderScreenerStockCard(stock) {
    return `
        <div class="screener-card" onclick="showStockDetail('${stock.symbol}')" style="background: var(--bg-secondary); padding: 16px; border-radius: 12px; border: 1px solid var(--border-color); cursor: pointer; transition: transform 0.2s, border-color 0.2s;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                <span style="font-size: 16px; font-weight: 700;">${stock.symbol}</span>
                <span style="font-size: 13px; font-weight: 600; color: ${stock.score >= 75 ? '#22c55e' : stock.score >= 50 ? '#f59e0b' : 'var(--text-muted)'};">Score: ${Math.round(stock.score)}</span>
            </div>
            <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 12px;">${stock.mcap || 'Stock'}</div>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; font-size: 12px;">
                <div class="metric-cell"><span style="color: var(--text-muted);">P/E</span><br>${colorMetric('pe', stock.pe)}</div>
                <div class="metric-cell"><span style="color: var(--text-muted);">ROE</span><br>${colorMetric('roe', stock.roe, '%')}</div>
                <div class="metric-cell"><span style="color: var(--text-muted);">ROCE</span><br>${colorMetric('roce', stock.roce, '%')}</div>
                <div class="metric-cell"><span style="color: var(--text-muted);">D/E</span><br>${colorMetric('de', stock.de)}</div>
                <div class="metric-cell"><span style="color: var(--text-muted);">P/B</span><br>${colorMetric('pb', stock.pb)}</div>
                <div class="metric-cell"><span style="color: var(--text-muted);">Div%</span><br>${colorMetric('div_yield', stock.div_yield, '%')}</div>
            </div>
        </div>
    `;
}

function renderScreensGrid() {
    const grid = document.getElementById('screenerGrid');
    if (!grid || !screensCache) return;

    let screens = screensCache.screens;
    if (currentCategoryFilter === 'beginner') {
        screens = screens.filter(s => s.difficulty === 'Beginner');
    } else if (currentCategoryFilter !== 'all') {
        screens = screens.filter(s => s.category === currentCategoryFilter);
    }

    if (screens.length === 0) {
        grid.innerHTML = '<div class="empty-state"><span>📋</span><p>No screens in this category</p></div>';
        return;
    }

    grid.innerHTML = screens.map(screen => {
        const diffColor = screen.difficulty === 'Beginner' ? '#22c55e' : screen.difficulty === 'Intermediate' ? '#f59e0b' : '#ef4444';
        const riskColor = screen.risk_level === 'Low' ? '#22c55e' : screen.risk_level === 'Medium' ? '#f59e0b' : '#ef4444';
        return `
            <div class="screen-card ${screen.recommended_for_fresh_entry ? 'recommended' : ''}" 
                 data-screen-id="${screen.id}" 
                 onclick="openScreenDetail('${screen.id}')">
                <div class="screen-card-header">
                    <span class="screen-card-name">${screen.name}</span>
                    <div style="display: flex; gap: 6px; align-items: center; flex-wrap: wrap;">
                        <span class="difficulty-pill" style="background: ${diffColor}18; color: ${diffColor}; padding: 2px 8px; border-radius: 12px; font-size: 10px; font-weight: 600;">${screen.difficulty || 'Intermediate'}</span>
                        <span class="risk-pill" style="background: ${riskColor}18; color: ${riskColor}; padding: 2px 8px; border-radius: 12px; font-size: 10px; font-weight: 600;">Risk: ${screen.risk_level || 'Medium'}</span>
                        ${screen.recommended_for_fresh_entry ? '<span class="fresh-badge">⭐</span>' : ''}
                    </div>
                </div>
                <div class="screen-card-category">${getCategoryIcon(screen.category)} ${screen.category}</div>
                <div class="screen-card-definition">${screen.definition}</div>
                ${screen.why_it_matters ? `<div class="screen-card-why" style="font-size: 12px; color: var(--accent-primary); margin-top: 6px; font-style: italic;">💡 ${screen.why_it_matters}</div>` : ''}
                <div class="screen-card-footer">
                    <span class="fresh-rating">Fresh Entry: ${'★'.repeat(screen.fresh_entry_rating)}${'☆'.repeat(5 - screen.fresh_entry_rating)}</span>
                </div>
            </div>
        `;
    }).join('');
}

function getCategoryIcon(category) {
    const icons = {
        'Value': '💰',
        'Growth': '📈',
        'Quality': '💎',
        'Technical': '📊',
        'Thematic': '🏛️',
        'Safety': '🛡️'
    };
    return icons[category] || '📋';
}

async function openScreenDetail(screenId) {
    const data = await loadScreensData();
    const screen = data.screens.find(s => s.id === screenId);
    if (!screen) return;

    // Show detail panel, hide browse view
    document.getElementById('screenerBrowseView').classList.add('hidden');
    document.getElementById('screenDetailPanel').classList.remove('hidden');

    // Populate header
    document.getElementById('screenDetailName').textContent = screen.name;
    document.getElementById('screenDetailDefinition').textContent = screen.definition;
    document.getElementById('screenDetailSummary').textContent = screen.summary;
    document.getElementById('screenDetailMatches').textContent = 'Loading...';

    // Run the screen
    await runScreen(screenId);
}

async function runScreen(screenId) {
    const resultsEl = document.getElementById('screenerResults');

    resultsEl.innerHTML = '<div class="empty-state"><span class="loading"></span><p>Running screen...</p></div>';

    try {
        const response = await fetch(`${API_BASE}/api/screens/${screenId}/run`);
        const data = await response.json();

        document.getElementById('screenDetailMatches').textContent = `${data.matches} matches`;

        if (data.stocks && data.stocks.length > 0) {
            resultsEl.innerHTML = data.stocks.map(stock => `
                <div class="screener-card" data-symbol="${stock.symbol}" onclick="showStockDetail('${stock.symbol}')">
                    <div class="screener-card-header">
                        <span class="screener-card-symbol">${stock.symbol}</span>
                        <span class="screener-card-score ${stock.score >= 75 ? 'high' : stock.score >= 50 ? 'medium' : 'low'}">
                            ${Math.round(stock.score)}
                        </span>
                    </div>
                    <div class="screener-card-name">${stock.mcap || 'Stock'}</div>
                    <div class="screener-card-metrics">
                        <div class="metric-item">
                            <span class="metric-label">P/E</span>
                            <span class="metric-value">${stock.pe || '--'}</span>
                        </div>
                        <div class="metric-item">
                            <span class="metric-label">ROE</span>
                            <span class="metric-value">${stock.roe ? stock.roe.toFixed(1) + '%' : '--'}</span>
                        </div>
                        <div class="metric-item">
                            <span class="metric-label">ROCE</span>
                            <span class="metric-value">${stock.roce ? stock.roce.toFixed(1) + '%' : '--'}</span>
                        </div>
                        <div class="metric-item">
                            <span class="metric-label">D/E</span>
                            <span class="metric-value">${stock.de !== undefined ? stock.de.toFixed(2) : '--'}</span>
                        </div>
                    </div>
                </div>
            `).join('');
        } else {
            resultsEl.innerHTML = '<div class="empty-state"><span>📋</span><p>No stocks match this screen criteria</p></div>';
        }
    } catch (error) {
        console.error('Screen error:', error);
        resultsEl.innerHTML = '<div class="empty-state"><span>❌</span><p>Error running screen</p></div>';
    }
}

async function runConsolidatedScreening() {
    const btn = document.getElementById('runConsolidatedBtn');
    const browseView = document.getElementById('screenerBrowseView');
    const consolidatedView = document.getElementById('screenerConsolidatedView');
    const freshPicksEl = document.getElementById('freshEntryPicks');
    const aggregatedEl = document.getElementById('aggregatedPicksGrid');
    const metaEl = document.getElementById('consolidatedMeta');

    // Switch to consolidated view
    document.querySelectorAll('.view-toggle-btn').forEach(b => b.classList.remove('active'));
    document.querySelector('.view-toggle-btn[data-view="consolidated"]').classList.add('active');
    browseView.classList.add('hidden');
    document.getElementById('screenDetailPanel').classList.add('hidden');
    consolidatedView.classList.remove('hidden');

    // Show loading
    btn.disabled = true;
    btn.innerHTML = '⏳ Scanning...';
    freshPicksEl.innerHTML = '<div class="empty-state"><span class="loading"></span><p>Running 50+ screens...</p></div>';
    aggregatedEl.innerHTML = '';

    try {
        const response = await fetch(`${API_BASE}/api/screens/consolidated`);
        const data = await response.json();

        metaEl.textContent = `Scanned ${data.total_stocks_scanned} stocks across ${data.total_screens_run} screens`;

        // Render fresh entry picks
        if (data.fresh_entry_picks && data.fresh_entry_picks.length > 0) {
            freshPicksEl.innerHTML = data.fresh_entry_picks.map(pick => renderAggregatedCard(pick, true)).join('');
        } else {
            freshPicksEl.innerHTML = '<div class="empty-state"><span>📋</span><p>No high-confidence fresh entry picks found</p></div>';
        }

        // Render all aggregated picks
        if (data.aggregated_picks && data.aggregated_picks.length > 0) {
            aggregatedEl.innerHTML = data.aggregated_picks.map(pick => renderAggregatedCard(pick, false)).join('');
        } else {
            aggregatedEl.innerHTML = '<div class="empty-state"><span>📋</span><p>No multi-screen matches found</p></div>';
        }

    } catch (error) {
        console.error('Consolidated screening error:', error);
        freshPicksEl.innerHTML = '<div class="empty-state"><span>❌</span><p>Error running consolidated screens</p></div>';
    } finally {
        btn.disabled = false;
        btn.innerHTML = '🔥 Scan All Screens';
    }
}

function renderAggregatedCard(pick, isFreshEntry) {
    const ratingStars = '★'.repeat(Math.round(pick.fresh_entry_rating)) + '☆'.repeat(5 - Math.round(pick.fresh_entry_rating));

    return `
        <div class="aggregated-card ${isFreshEntry ? 'fresh-entry' : ''}" onclick="showStockDetail('${pick.symbol}')">
            <div class="aggregated-card-header">
                <div class="card-left">
                    <span class="card-symbol">${pick.symbol}</span>
                    <span class="card-name">${pick.name || pick.symbol}</span>
                </div>
                <div class="card-right">
                    <span class="screens-count">${pick.screens_matched} screens</span>
                    <span class="fresh-rating-mini">${ratingStars}</span>
                </div>
            </div>
            <div class="card-categories">
                ${pick.categories.map(c => `<span class="category-badge">${getCategoryIcon(c)} ${c}</span>`).join('')}
            </div>
            <div class="card-rationale">${pick.rationale}</div>
            <div class="card-screens">
                ${pick.screen_names.slice(0, 4).map(s => `<span class="screen-tag">${s}</span>`).join('')}
                ${pick.screen_names.length > 4 ? `<span class="screen-tag more">+${pick.screen_names.length - 4}</span>` : ''}
            </div>
            <div class="card-fundamentals">
                <span>P/E: ${pick.fundamentals.pe || '--'}</span>
                <span>ROE: ${pick.fundamentals.roe ? pick.fundamentals.roe.toFixed(1) + '%' : '--'}</span>
                <span>ROCE: ${pick.fundamentals.roce ? pick.fundamentals.roce.toFixed(1) + '%' : '--'}</span>
                <span>D/E: ${pick.fundamentals.de !== undefined ? pick.fundamentals.de.toFixed(2) : '--'}</span>
            </div>
        </div>
    `;
}



// ===== RESEARCH CONSOLE =====

function setupResearchConsole() {
    const researchBtn = document.getElementById('researchBtn');
    const researchInput = document.getElementById('researchSearchInput');

    if (!researchBtn || !researchInput) return;

    researchBtn.addEventListener('click', () => {
        const symbol = researchInput.value.trim().toUpperCase();
        if (symbol) {
            loadResearchData(symbol);
        }
    });

    researchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            const symbol = researchInput.value.trim().toUpperCase();
            if (symbol) {
                loadResearchData(symbol);
            }
        }
    });
}

async function loadResearchData(symbol) {
    console.log('[Research] Loading data for:', symbol);

    const consoleEl = document.getElementById('researchConsole');
    const emptyEl = document.getElementById('researchEmpty');
    const input = document.getElementById('researchSearchInput');
    const insightEl = document.getElementById('aiAnalystInsight');

    // Reset UI state
    if (input) input.value = symbol;

    // Show loading state in gauge/insight if element exists
    if (insightEl) {
        insightEl.innerHTML = '<span class="loading"></span> Analyzing market data...';
    }

    // Show console, hide empty state immediately for loading feedback
    if (consoleEl) consoleEl.classList.remove('hidden');
    if (emptyEl) emptyEl.classList.add('hidden');

    try {
        console.log('[Research] Fetching from API...');
        const response = await fetch(`${API_BASE}/api/research/${symbol}`);
        const data = await response.json();

        if (data.symbol) {
            // Show console, hide empty state
            consoleEl.classList.remove('hidden');
            emptyEl.classList.add('hidden');

            // Update header
            document.getElementById('researchSymbol').textContent = data.symbol;
            document.getElementById('researchName').textContent = data.name || data.symbol;
            document.getElementById('researchSector').textContent = data.sector || 'General';

            // Update price
            if (data.stock_info) {
                document.getElementById('researchPrice').textContent =
                    `₹${data.stock_info.current_price?.toLocaleString() || '--'}`;
                const change = data.stock_info.change_percent || 0;
                const changeEl = document.getElementById('researchChange');
                changeEl.textContent = `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`;

                // Color update
                if (change >= 0) {
                    changeEl.style.color = '#22c55e'; // Green
                } else {
                    changeEl.style.color = '#ef4444'; // Red
                }
            }

            // Update gauge
            if (data.expert_recommendation) {
                updateExpertGauge(data.expert_recommendation);
                if (data.expert_recommendation.factors) {
                    updateFactorBars(data.expert_recommendation.factors);
                }
            }

            // Update fundamentals - using correct HTML element IDs
            if (data.fundamentals) {
                setText('statPE', data.fundamentals.pe);
                setText('statPB', data.fundamentals.pb);
                setText('statROE', data.fundamentals.roe ? `${data.fundamentals.roe}%` : null);
                setText('statDiv', data.fundamentals.div_yield ? `${data.fundamentals.div_yield}%` : null);
            }

            // Update additional stats (52W High/Low, Market Cap, Volume)
            if (data.stock_info) {
                setText('stat52WH', data.stock_info['52w_high'] ? `₹${data.stock_info['52w_high'].toLocaleString()}` : '--');
                setText('stat52WL', data.stock_info['52w_low'] ? `₹${data.stock_info['52w_low'].toLocaleString()}` : '--');
                setText('statMCap', data.stock_info.market_cap ? formatMarketCap(data.stock_info.market_cap) : '--');
                setText('statVolume', data.stock_info.volume ? formatVolume(data.stock_info.volume) : '--');
            }

            // Render price chart
            if (data.price_history && data.price_history.length > 0) {
                renderResearchPriceChart(data.price_history);
            }

            // Update AI Insight
            if (data.expert_recommendation && data.expert_recommendation.rationale) {
                document.getElementById('aiAnalystInsight').innerHTML = data.expert_recommendation.rationale;
            } else {
                document.getElementById('aiAnalystInsight').textContent = "AI analysis suggests monitoring this stock based on current technical and fundamental indicators.";
            }

            // Update news
            const newsList = document.getElementById('researchNewsList');
            if (data.recent_news && data.recent_news.length > 0) {
                newsList.innerHTML = data.recent_news.map(n => `
                    <div class="research-news-item" style="padding: 12px 0; border-bottom: 1px solid var(--border-color);">
                        <a href="${n.link}" target="_blank" style="display: block; font-weight: 500; margin-bottom: 4px; color: var(--text-primary); text-decoration: none;">${n.title}</a>
                        <div style="display: flex; justify-content: space-between; font-size: 11px; color: var(--text-muted);">
                            <span>${n.source}</span>
                            <span>${n.sentiment || 'Neutral'}</span>
                        </div>
                    </div>
                `).join('');
            } else {
                newsList.innerHTML = '<p class="text-muted" style="padding: 12px 0;">No recent news found for this stock.</p>';
            }
        }
    } catch (error) {
        console.error('Error loading research data:', error);
        showToast('Failed to load research data: ' + error.message, 'error');
    }
}

function updateExpertGauge(recommendation) {
    const score = recommendation.score || 50;
    const signal = recommendation.signal || 'HOLD';

    // Reset tabs
    document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
    document.getElementById('tabContentRationale').style.display = 'block';

    // Reset tab buttons
    document.querySelectorAll('.analysis-tabs .tab-btn').forEach(btn => {
        btn.classList.remove('active');
        btn.style.background = 'transparent';
        btn.style.color = 'var(--text-secondary)';
    });
    const firstTab = document.querySelector('.analysis-tabs .tab-btn');
    if (firstTab) {
        firstTab.classList.add('active');
        firstTab.style.background = 'var(--bg-card)';
        firstTab.style.color = 'var(--text-primary)';
    }

    // Signal color
    const signalEl = document.getElementById('gaugeSignal');
    if (signal === 'STRONG BUY' || signal === 'BUY') signalEl.style.color = '#22c55e';
    else if (signal === 'STRONG SELL' || signal === 'SELL') signalEl.style.color = '#ef4444';
    else signalEl.style.color = '#f59e0b';

    // Rotation logic: 0 to 100 maps to -90deg to 90deg
    // Formula: (score / 100) * 180 - 90
    const rotation = (score / 100) * 180 - 90;
    const needle = document.getElementById('gaugeNeedle');
    if (needle) {
        needle.style.transform = `rotate(${rotation}deg)`;
    }
}

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value || '--';
}

function formatMarketCap(value) {
    if (value >= 1e12) return `₹${(value / 1e12).toFixed(2)}T`;
    if (value >= 1e9) return `₹${(value / 1e9).toFixed(2)}B`;
    if (value >= 1e7) return `₹${(value / 1e7).toFixed(2)}Cr`;
    if (value >= 1e5) return `₹${(value / 1e5).toFixed(2)}L`;
    return `₹${value.toLocaleString()}`;
}

function formatVolume(value) {
    if (value >= 1e7) return `${(value / 1e7).toFixed(2)}Cr`;
    if (value >= 1e5) return `${(value / 1e5).toFixed(2)}L`;
    if (value >= 1e3) return `${(value / 1e3).toFixed(1)}K`;
    return value.toLocaleString();
}

let researchChartInstance = null;

function renderResearchPriceChart(priceHistory) {
    const ctx = document.getElementById('researchPriceChart');
    if (!ctx) return;

    // Destroy existing chart if present
    if (researchChartInstance) {
        researchChartInstance.destroy();
    }

    const labels = priceHistory.map(p => {
        const d = new Date(p.date);
        return `${d.getDate()}/${d.getMonth() + 1}`;
    });
    const prices = priceHistory.map(p => p.close);

    // Determine trend color
    const startPrice = prices[0];
    const endPrice = prices[prices.length - 1];
    const isUptrend = endPrice >= startPrice;
    const lineColor = isUptrend ? '#22c55e' : '#ef4444';
    const bgColor = isUptrend ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)';

    researchChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Price',
                data: prices,
                borderColor: lineColor,
                backgroundColor: bgColor,
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(0,0,0,0.8)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    callbacks: {
                        label: (ctx) => `₹${ctx.parsed.y.toLocaleString()}`
                    }
                }
            },
            scales: {
                x: {
                    display: true,
                    grid: { display: false },
                    ticks: {
                        color: 'rgba(255,255,255,0.5)',
                        font: { size: 10 },
                        maxRotation: 0,
                        maxTicksLimit: 6
                    }
                },
                y: {
                    display: true,
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: {
                        color: 'rgba(255,255,255,0.5)',
                        font: { size: 10 },
                        callback: (v) => `₹${v.toLocaleString()}`
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}

function updateFactorBars(factors) {
    const factorMap = {
        'value': 'Value',
        'growth': 'Growth',
        'safety': 'Safety',
        'technicals': 'Technicals',
        'sentiment': 'Sentiment',
        'quality': 'Quality'
    };

    for (const [key, label] of Object.entries(factorMap)) {
        const value = factors[key] || 50;
        const barEl = document.getElementById(`factor${label}`);
        const scoreEl = document.getElementById(`factor${label}Score`);

        if (barEl && scoreEl) {
            barEl.style.width = `${value}%`;
            // Color logic
            let colorClass = 'medium';
            if (value >= 70) colorClass = 'high';
            else if (value < 40) colorClass = 'low';

            barEl.className = `factor-bar-fill ${colorClass}`;
            scoreEl.textContent = Math.round(value);
        }
    }
}
function switchAnalysisTab(tabName) {
    // Hide all content
    document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');

    // Show specific content
    // Map tabName to ID
    const map = {
        'rationale': 'tabContentRationale',
        'bull_case': 'tabContentBull',
        'bear_case': 'tabContentBear',
        'risk': 'tabContentRisk'
    };

    const targetId = map[tabName];
    if (targetId) {
        const target = document.getElementById(targetId);
        if (target) target.style.display = 'block';
    }

    // Update buttons
    const buttons = document.querySelectorAll('.analysis-tabs .tab-btn');
    buttons.forEach(btn => {
        // Simple text check or attribute check could work, but using index reliance is risky
        // Let's assume order matches or text includes key words
        const text = btn.textContent.toLowerCase();
        let active = false;

        if (tabName === 'rationale' && text.includes('rationale')) active = true;
        if (tabName === 'bull_case' && text.includes('bull')) active = true;
        if (tabName === 'bear_case' && text.includes('bear')) active = true;
        if (tabName === 'risk' && text.includes('risk')) active = true;

        if (active) {
            btn.classList.add('active');
            btn.style.background = 'var(--bg-card)';
            btn.style.color = 'var(--text-primary)';
        } else {
            btn.classList.remove('active');
            btn.style.background = 'transparent';
            btn.style.color = 'var(--text-secondary)';
        }
    });
}

// ===== Gemini AI Settings =====

async function updateAssistantUI() {
    try {
        const data = await apiCall('/api/gemini/config');

        // Update Sidebar
        const navItem = document.querySelector('.nav-item[data-section="ai"]');
        if (navItem) {
            const icon = navItem.querySelector('.material-icons');
            const text = navItem.querySelector('span:last-child'); // Using last-child for text

            if (data.has_key && data.ai_enabled) {
                if (icon) icon.textContent = 'smart_toy';
                if (text) text.textContent = 'AI Assistant';
                navItem.title = "Chat with Gemini AI";

                // Update Embedded Chat UI
                const chatHeader = document.querySelector('.ai-chat-compact h4');
                if (chatHeader) {
                    chatHeader.innerHTML = '<span class="material-icons" style="color: var(--accent-primary);">smart_toy</span> Ask AI Assistant';
                }
                const chatInput = document.getElementById('aiChatInput');
                if (chatInput) chatInput.placeholder = "e.g., Should I buy RELIANCE today? or Analyze TCS...";

            } else {
                if (icon) icon.textContent = 'travel_explore';
                if (text) text.textContent = 'Smart Search';
                navItem.title = "Google Search Assistant";

                // Update Embedded Chat UI
                const chatHeader = document.querySelector('.ai-chat-compact h4');
                if (chatHeader) {
                    chatHeader.innerHTML = '<span class="material-icons" style="color: var(--accent-primary);">travel_explore</span> Smart Search';
                }
                const chatInput = document.getElementById('aiChatInput');
                if (chatInput) chatInput.placeholder = "Search for market news, stock details, or company analysis...";
            }
        }
    } catch (e) {
        console.warn('Assistant UI update failed:', e);
    }
}

async function loadGeminiConfig() {
    try {
        const data = await apiCall('/api/gemini/config');
        if (data.model) {
            const modelSelect = document.getElementById('geminiModel');
            if (modelSelect) modelSelect.value = data.model;
        }
        if (data.has_key) {
            const statusEl = document.getElementById('geminiSaveStatus');
            if (statusEl) statusEl.textContent = '✓ API key configured';
        }
    } catch (e) {
        console.log('Gemini config not loaded:', e);
    }
}

async function saveGeminiConfig() {
    const apiKey = document.getElementById('geminiApiKey').value;
    const model = document.getElementById('geminiModel').value;
    const statusEl = document.getElementById('geminiSaveStatus');

    if (!apiKey) {
        statusEl.textContent = '⚠️ Please enter an API key';
        return;
    }

    statusEl.textContent = 'Saving...';

    try {
        await apiCall('/api/gemini/config', {
            method: 'POST',
            body: JSON.stringify({ api_key: apiKey, model: model })
        });
        statusEl.textContent = '✓ Saved successfully!';
        document.getElementById('geminiApiKey').value = ''; // Clear for security

        // Update UI immediately (Sidebar etc)
        await updateAssistantUI();
    } catch (e) {
        statusEl.textContent = '❌ Failed to save';
    }
}

// Setup Gemini save button
document.addEventListener('DOMContentLoaded', () => {
    const saveBtn = document.getElementById('saveGeminiBtn');
    if (saveBtn) saveBtn.addEventListener('click', saveGeminiConfig);

    // Load current config when settings section is shown
    const settingsNav = document.querySelector('[data-section="settings"]');
    if (settingsNav) {
        settingsNav.addEventListener('click', loadGeminiConfig);
    }

    // Initialize Assistant Icon on load
    updateAssistantUI();
});

// ===== AI Chatbot Logic =====
document.addEventListener('DOMContentLoaded', () => {
    const chatbotToggler = document.querySelector(".chatbot-toggler");
    const closeBtn = document.querySelector(".close-btn");
    const chatbox = document.querySelector(".chatbox");
    const chatInput = document.querySelector(".chat-input textarea");
    const sendChatBtn = document.querySelector(".chat-input span");

    if (!chatbotToggler) return; // Guard clause if elements missing

    let userMessage = null;
    const inputInitHeight = chatInput.scrollHeight;

    const createChatLi = (message, className) => {
        const chatLi = document.createElement("li");
        chatLi.classList.add("chat", className);
        let chatContent = className === "outgoing" ? `< p ></p > ` : ` < span class="material-icons" > smart_toy</span > <p></p>`;
        chatLi.innerHTML = chatContent;
        chatLi.querySelector("p").innerText = message;
        return chatLi;
    }

    const generateResponse = async (chatElement) => {
        const API_URL = "/api/chat";
        const messageElement = chatElement.querySelector("p");

        try {
            const response = await apiCall(API_URL, {
                method: "POST",
                body: JSON.stringify({ message: userMessage })
            });

            messageElement.innerText = response.response;
        } catch (error) {
            messageElement.classList.add("error");
            messageElement.innerText = "Oops! Something went wrong. Make sure API key is set.";
        } finally {
            chatbox.scrollTo(0, chatbox.scrollHeight);
        }
    }

    const handleChat = () => {
        userMessage = chatInput.value.trim();
        if (!userMessage) return;

        chatInput.value = "";
        chatInput.style.height = `${inputInitHeight} px`;

        chatbox.appendChild(createChatLi(userMessage, "outgoing"));
        chatbox.scrollTo(0, chatbox.scrollHeight);

        const incomingChatLi = createChatLi("Thinking...", "incoming");
        chatbox.appendChild(incomingChatLi);
        chatbox.scrollTo(0, chatbox.scrollHeight);

        generateResponse(incomingChatLi);
    }

    // Initialize global handler for suggestion chips
    window.handleChip = (message) => {
        const chatInput = document.querySelector(".chat-input textarea");
        if (chatInput) {
            chatInput.value = message;
            // Trigger the handleChat logic
            // We need to access the variables from this scope, or trigger click
            const sendBtn = document.querySelector(".chat-input span");
            if (sendBtn) sendBtn.click();
        }
    }

    chatInput.addEventListener("input", () => {
        chatInput.style.height = `${inputInitHeight} px`;
        chatInput.style.height = `${chatInput.scrollHeight} px`;
    });

    chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey && window.innerWidth > 800) {
            e.preventDefault();
            handleChat();
        }
    });

    sendChatBtn.addEventListener("click", handleChat);
    closeBtn.addEventListener("click", () => document.body.classList.remove("show-chatbot"));
    chatbotToggler.addEventListener("click", () => document.body.classList.toggle("show-chatbot"));
});

// ===== System Controls Logic =====
async function initSystemControls() {
    const sysToggle = document.getElementById('systemToggle');
    const aiToggle = document.getElementById('aiToggle');

    if (!sysToggle || !aiToggle) return;

    // Load initial status
    try {
        const status = await apiCall('/api/system/status');
        sysToggle.checked = status.system_monitoring;
        aiToggle.checked = status.ai_features;
    } catch (e) {
        console.error("Failed to load system status:", e);
    }

    // Handle changes
    const updateControl = async () => {
        try {
            await apiCall('/api/system/control', {
                method: 'POST',
                body: JSON.stringify({
                    system_monitoring: sysToggle.checked,
                    ai_features: aiToggle.checked
                })
            });
            showToast('System settings updated', 'success', 3000);
        } catch (e) {
            console.error("Failed to update system status:", e);
            showToast('Failed to update settings', 'error');
            // Revert on failure
            try {
                const status = await apiCall('/api/system/status');
                sysToggle.checked = status.system_monitoring;
                aiToggle.checked = status.ai_features;
            } catch (err) { }
        }
    };

    sysToggle.addEventListener('change', updateControl);
    aiToggle.addEventListener('change', updateControl);
}

document.addEventListener('DOMContentLoaded', initSystemControls);

// Simple Toast Notification
function showToast(message, type = 'info', duration = 4000) {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    // Flex container for content and close button
    toast.style.display = 'flex';
    toast.style.alignItems = 'center';
    toast.style.justifyContent = 'space-between';
    toast.style.gap = '12px';

    toast.innerHTML = `
        <span>${message}</span>
        <button onclick="this.parentElement.remove()" style="background:none; border:none; color:inherit; font-size:18px; cursor:pointer; padding:0; line-height:1; opacity:0.8;">&times;</button>
    `;

    // Add toast styles dynamically if not present
    if (!document.getElementById('toast-style')) {
        const style = document.createElement('div'); // Using div to avoid hydration issues if any, acts as container for style
        style.innerHTML = `
        <style id="toast-style">
            .toast {
                position: fixed;
                top: 20px;
                right: 20px;
                background: #333;
                color: white;
                padding: 12px 20px;
                border-radius: 8px;
                z-index: 9999;
                animation: slideInToast 0.3s ease-out;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                font-size: 14px;
                min-width: 250px;
                max-width: 400px;
            }
            .toast.success { background: #10B981; }
            .toast.error { background: #EF4444; }
            .toast.info { background: #3B82F6; }
            
            @keyframes slideInToast {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
        </style>`;
        document.head.appendChild(style.firstElementChild);
    }

    document.body.appendChild(toast);

    // Auto remove if duration > 0
    if (duration > 0) {
        setTimeout(() => {
            if (document.body.contains(toast)) {
                toast.style.opacity = '0';
                toast.style.transform = 'translateY(-20px)';
                toast.style.transition = 'all 0.3s';
                setTimeout(() => {
                    if (document.body.contains(toast)) toast.remove();
                }, 300);
            }
        }, duration);
    }
}

// ===== Omnibar Logic (Search + Chat) =====
let availableStocks = [];

async function initOmnibar() {
    const input = document.getElementById('omnibarInput');
    const datalist = document.getElementById('stockSuggestions');
    if (!input) return;

    // Fetch stock list for autocomplete
    try {
        const response = await apiCall('/api/stocks/list');
        if (Array.isArray(response)) {
            availableStocks = response;
            if (datalist) {
                datalist.innerHTML = response.map(s =>
                    `<option value="${s.symbol}">${s.name}</option>`
                ).join('');
            }
        }
    } catch (e) {
        console.error("Failed to fetch stock list", e);
    }

    // Handle Enter key
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            handleOmnibarSubmit(input.value);
        }
    });

    // Handle shortcuts (Cmd/Ctrl + K)
    document.addEventListener('keydown', (e) => {
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
            e.preventDefault();
            input.focus();
        }
    });
}

function handleOmnibarSubmit(query) {
    if (!query) return;
    const cleanQuery = query.trim().toUpperCase();

    // Check if it's a stock symbol match (Symbol or 'Symbol Name')
    // We check if the input starts with a known symbol
    const stockMatch = availableStocks.find(s =>
        cleanQuery === s.symbol ||
        cleanQuery.startsWith(s.symbol + " ") ||
        s.name.toUpperCase().includes(cleanQuery) // Basic fuzzy
    );

    // Exact symbol match check
    const exactMatch = availableStocks.find(s => s.symbol === cleanQuery);

    // If it looks like a symbol (3-10 chars, no spaces) or exact match
    const isSymbolLike = /^[A-Z0-9]{3,10}$/.test(cleanQuery);

    if (exactMatch || (isSymbolLike && !query.includes(' '))) {
        // It is likely a stock -> Open Analysis
        const symbol = exactMatch ? exactMatch.symbol : cleanQuery;
        showStockDetail(symbol);
    } else {
        // Treat as Chat Question
        toggleChat(true); // Open chat window

        // Send message to chat
        const chatInput = document.getElementById('chatInput');
        if (chatInput) {
            chatInput.value = query; // Set value
            // Trigger send button click
            // We need a small delay to ensure chat window open animation
            setTimeout(() => {
                const sendBtn = document.getElementById('sendChatBtn');
                if (sendBtn) sendBtn.click();
            }, 100);
        }
    }
}

// ============== Quant Lab Functions ==============

// Pattern Scout
function initPatternScout() {
    const btn = document.getElementById('patternScoutBtn');
    const input = document.getElementById('patternScoutInput');

    if (btn && !btn.hasListener) {
        btn.hasListener = true;
        btn.addEventListener('click', () => analyzePatterns(input.value));
    }
    if (input && !input.hasListener) {
        input.hasListener = true;
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') analyzePatterns(input.value);
        });
        input.focus();
    }
}

async function analyzePatterns(symbol) {
    if (!symbol) return showToast('Enter a stock symbol', 'error');

    const container = document.getElementById('patternScoutResults');
    container.innerHTML = '<div class="empty-state"><span class="loading"></span><p>Analyzing patterns for ' + symbol.toUpperCase() + '...</p></div>';

    try {
        const data = await apiCall(`/api/quant/patterns/${symbol.toUpperCase()}`);

        if (data.error) {
            container.innerHTML = `<div class="empty-state"><span style="font-size:48px">⚠️</span><p>${data.error}</p></div>`;
            return;
        }

        // Determine overall verdict for beginners
        const signal = (data.overall_signal || '').toLowerCase();
        let verdictEmoji, verdictText, verdictColor, verdictAdvice;
        if (signal.includes('bullish') || signal.includes('buy')) {
            verdictEmoji = '🟢'; verdictColor = '#22c55e';
            verdictText = 'Bullish — Upward momentum detected';
            verdictAdvice = 'Technical indicators suggest this stock has positive momentum. Consider researching fundamentals before buying.';
        } else if (signal.includes('bearish') || signal.includes('sell')) {
            verdictEmoji = '🔴'; verdictColor = '#ef4444';
            verdictText = 'Bearish — Downward pressure detected';
            verdictAdvice = 'Technical indicators suggest caution. Wait for momentum to improve or check if fundamentals justify holding.';
        } else {
            verdictEmoji = '🟡'; verdictColor = '#f59e0b';
            verdictText = 'Neutral — No strong signal';
            verdictAdvice = 'The stock is consolidating. Watch for a breakout above resistance or breakdown below support.';
        }

        // RSI interpretation
        const rsi = data.momentum?.rsi;
        let rsiColor = 'var(--text-primary)', rsiMeaning = '';
        if (rsi) {
            if (rsi > 70) { rsiColor = '#ef4444'; rsiMeaning = '⚠️ Overbought — the stock has risen too fast. It may pull back. Not ideal to buy now.'; }
            else if (rsi > 60) { rsiColor = '#fb923c'; rsiMeaning = '📈 Strong momentum — trending up but not extreme. Watch for reversal signs.'; }
            else if (rsi >= 40) { rsiColor = '#22c55e'; rsiMeaning = '✅ Healthy range — the stock is in a balanced zone. Good time to consider entry.'; }
            else if (rsi >= 30) { rsiColor = '#f59e0b'; rsiMeaning = '📉 Weak momentum — losing steam. Could be a bargain or a falling knife.'; }
            else { rsiColor = '#22c55e'; rsiMeaning = '🟢 Oversold — the stock has fallen too much. Potential bounce-back opportunity!'; }
        }

        // RS interpretation
        const rsVal = data.relative_strength?.rs_value;
        let rsColor = 'var(--text-primary)', rsMeaning = '';
        if (rsVal) {
            if (rsVal > 120) { rsColor = '#22c55e'; rsMeaning = '💪 Beating the market significantly! This stock is a relative outperformer.'; }
            else if (rsVal > 100) { rsColor = '#a3e635'; rsMeaning = '📈 Outperforming the market slightly. Positive sign.'; }
            else if (rsVal > 80) { rsColor = '#f59e0b'; rsMeaning = '📉 Underperforming the market slightly. Watch closely.'; }
            else { rsColor = '#ef4444'; rsMeaning = '⚠️ Significantly lagging the market. Investigate why before investing.'; }
        }

        let html = `
        <div class="quant-results">
            <!-- Beginner Verdict Card -->
            <div class="beginner-verdict-card" style="background: ${verdictColor}10; border: 1px solid ${verdictColor}40; border-radius: 16px; padding: 20px; margin-bottom: 24px;">
                <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 12px;">
                    <span style="font-size: 40px;">${verdictEmoji}</span>
                    <div>
                        <h3 style="margin: 0; font-size: 20px; font-weight: 700;">${data.symbol}</h3>
                        <span style="color: ${verdictColor}; font-weight: 600; font-size: 16px;">${verdictText}</span>
                    </div>
                </div>
                <p style="color: var(--text-secondary); font-size: 14px; margin: 0; line-height: 1.6;">💡 <strong>What this means for you:</strong> ${verdictAdvice}</p>
            </div>
            
            <div class="quant-grid">
                <!-- Relative Strength -->
                <div class="settings-card">
                    <h4>📊 Relative Strength (vs NIFTY)</h4>
                    <div class="metric-large" style="color: ${rsColor}">${rsVal || 'N/A'}</div>
                    <p class="metric-label">${data.relative_strength?.rs_rating || ''}</p>
                    <div class="beginner-explain" style="background: var(--bg-tertiary); padding: 10px; border-radius: 8px; margin-top: 10px;">
                        <p style="font-size: 12px; color: var(--text-muted); margin: 0 0 4px 0;">📖 <strong>What is this?</strong> Compares how this stock moved vs the overall market (NIFTY 50). Above 100 = beating the market.</p>
                        ${rsMeaning ? `<p style="font-size: 13px; margin: 0; color: var(--text-secondary);">${rsMeaning}</p>` : ''}
                    </div>
                </div>
                
                <!-- Momentum -->
                <div class="settings-card">
                    <h4>📈 Momentum Indicators</h4>
                    <div class="metric-row">
                        <span>RSI (14):</span>
                        <strong style="color: ${rsiColor}">${rsi || 'N/A'} (${data.momentum?.rsi_zone || ''})</strong>
                    </div>
                    <div class="metric-row">
                        <span>MACD Trend:</span>
                        <strong class="${data.momentum?.macd_trend === 'Bullish' ? 'text-green' : 'text-red'}">${data.momentum?.macd_trend || 'N/A'}</strong>
                    </div>
                    <div class="beginner-explain" style="background: var(--bg-tertiary); padding: 10px; border-radius: 8px; margin-top: 10px;">
                        <p style="font-size: 12px; color: var(--text-muted); margin: 0 0 4px 0;">📖 <strong>RSI</strong> = Relative Strength Index. Like a speedometer: below 30 = oversold (potential buy), above 70 = overbought (potential sell).</p>
                        ${rsiMeaning ? `<p style="font-size: 13px; margin: 0; color: var(--text-secondary);">${rsiMeaning}</p>` : ''}
                        <p style="font-size: 12px; color: var(--text-muted); margin: 8px 0 0 0;">📖 <strong>MACD</strong> = Shows if the trend is changing direction. Bullish = price starting to rise. Bearish = price starting to fall.</p>
                    </div>
                </div>
            </div>
            
            <!-- Detected Patterns -->
            <div class="settings-card" style="margin-top: 16px;">
                <h4>🔍 Detected Patterns (${data.patterns?.length || 0})</h4>
                ${data.patterns?.length ? data.patterns.map(p => `
                    <div class="pattern-item ${p.type}" style="padding: 12px; background: var(--bg-tertiary); border-radius: 8px; margin-bottom: 8px; border-left: 3px solid ${p.type === 'bullish' ? '#22c55e' : p.type === 'bearish' ? '#ef4444' : '#f59e0b'};">
                        <div class="pattern-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                            <span class="pattern-name" style="font-weight: 700;">${p.pattern}</span>
                            <span class="badge ${p.type}" style="padding: 2px 10px; border-radius: 12px; font-size: 11px; background: ${p.type === 'bullish' ? '#22c55e20' : p.type === 'bearish' ? '#ef444420' : '#f59e0b20'}; color: ${p.type === 'bullish' ? '#22c55e' : p.type === 'bearish' ? '#ef4444' : '#f59e0b'};">${p.reliability}</span>
                        </div>
                        <p style="color: var(--text-secondary); font-size: 13px; margin: 0 0 6px 0;">${p.description}</p>
                        <p style="font-size: 13px; margin: 0;"><strong>👉 Action:</strong> ${p.action}</p>
                    </div>
                `).join('') : '<div style="padding: 16px; text-align: center; color: var(--text-muted);">No patterns detected in recent data. The stock may be in a quiet phase — check back later.</div>'}
            </div>
            
            ${data.summary ? `<p class="summary-text" style="background: var(--bg-tertiary); padding: 16px; border-radius: 12px; border-left: 3px solid var(--accent-primary); margin-top: 16px; font-size: 14px; color: var(--text-secondary); line-height: 1.6;">📝 ${data.summary}</p>` : ''}
        </div>`;

        container.innerHTML = html;

    } catch (e) {
        container.innerHTML = `<div class="empty-state"><span style="font-size:48px">❌</span><p>Error: ${e.message}</p><p style="color: var(--text-muted); font-size: 12px; margin-top: 8px;">Try a different stock symbol or check your internet connection.</p></div>`;
    }
}

// QVM Engine
function initQvmEngine() {
    const btn = document.getElementById('qvmAnalyzeBtn');
    const input = document.getElementById('qvmInput');

    if (btn && !btn.hasListener) {
        btn.hasListener = true;
        btn.addEventListener('click', () => analyzeQvm(input.value));
    }
    if (input && !input.hasListener) {
        input.hasListener = true;
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') analyzeQvm(input.value);
        });
        input.focus();
    }
}

async function analyzeQvm(symbol) {
    if (!symbol) return showToast('Enter a stock symbol', 'error');

    const container = document.getElementById('qvmResults');
    container.innerHTML = '<div class="empty-state"><span class="loading"></span><p>Calculating QVM scores for ' + symbol.toUpperCase() + '...</p></div>';

    try {
        const data = await apiCall(`/api/quant/qvm/${symbol.toUpperCase()}`);

        if (data.error) {
            container.innerHTML = `<div class="empty-state"><span style="font-size:48px">⚠️</span><p>${data.error}</p></div>`;
            return;
        }

        const inv = data.investability || {};
        const iScore = inv.score || 0;

        // Beginner-friendly verdict
        let verdictEmoji, verdictColor, verdictText, verdictAdvice;
        if (iScore >= 80) {
            verdictEmoji = '🟢'; verdictColor = '#22c55e';
            verdictText = 'Excellent — Strong on all fronts';
            verdictAdvice = 'This stock scores well on quality, value, and momentum. Worth serious research for your portfolio.';
        } else if (iScore >= 60) {
            verdictEmoji = '🟡'; verdictColor = '#a3e635';
            verdictText = 'Good — Solid pick with some concerns';
            verdictAdvice = 'Check which dimension is weak (Q, V, or M). If quality is high but valuation is low, it might be overpriced.';
        } else if (iScore >= 40) {
            verdictEmoji = '🟠'; verdictColor = '#f59e0b';
            verdictText = 'Fair — Needs deeper research';
            verdictAdvice = 'Mixed signals. Dig deeper into the weak areas before investing. Consider waiting for better entry.';
        } else {
            verdictEmoji = '🔴'; verdictColor = '#ef4444';
            verdictText = 'Weak — Proceed with caution';
            verdictAdvice = 'Multiple red flags detected. This stock needs significant improvement before it becomes investable.';
        }

        // Score color helper
        const scoreColor = (s, max = 10) => {
            const pct = (s / max) * 100;
            return pct >= 70 ? '#22c55e' : pct >= 50 ? '#f59e0b' : '#ef4444';
        };

        // Score label helper
        const scoreLabel = (s) => {
            if (s >= 8) return 'Excellent';
            if (s >= 6) return 'Good';
            if (s >= 4) return 'Fair';
            if (s >= 2) return 'Weak';
            return 'Poor';
        };

        // Score explanation helper
        const qExplain = (s) => s >= 7 ? 'Well-managed company with strong fundamentals 👍' : s >= 4 ? 'Decent management, room for improvement' : 'Weak fundamentals — high risk ⚠️';
        const vExplain = (s) => s >= 7 ? 'Attractively priced — good value for money 💰' : s >= 4 ? 'Fairly priced — not cheap, not expensive' : 'Overvalued — price seems too high ⚠️';
        const mExplain = (s) => s >= 7 ? 'Strong uptrend — stock is gaining momentum 🚀' : s >= 4 ? 'Sideways movement — no clear direction' : 'Downtrend — losing momentum 📉';

        const qScore = data.quality?.score || 0;
        const vScore = data.valuation?.score || 0;
        const mScore = data.momentum?.score || 0;

        let html = `
        <div class="quant-results">
            <!-- Verdict Card -->
            <div style="background: ${verdictColor}10; border: 1px solid ${verdictColor}40; border-radius: 16px; padding: 20px; margin-bottom: 24px;">
                <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 12px;">
                    <div style="position: relative; width: 80px; height: 80px;">
                        <svg viewBox="0 0 36 36" style="width: 80px; height: 80px; transform: rotate(-90deg);">
                            <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="var(--bg-tertiary)" stroke-width="3" />
                            <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="${verdictColor}" stroke-width="3" stroke-dasharray="${iScore}, 100" stroke-linecap="round" />
                        </svg>
                        <div style="position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; font-size: 22px; font-weight: 800; color: ${verdictColor};">${iScore}</div>
                    </div>
                    <div>
                        <h3 style="margin: 0; font-size: 20px; font-weight: 700;">${data.symbol} <span style="font-weight: 400; font-size: 14px; color: var(--text-muted);">— ${data.name || ''}</span></h3>
                        <span style="color: ${verdictColor}; font-weight: 600; font-size: 16px;">${verdictEmoji} ${verdictText}</span>
                        ${data.sector ? `<p style="color: var(--text-muted); font-size: 12px; margin: 4px 0 0 0;">${data.sector} · ${data.industry || ''}</p>` : ''}
                    </div>
                </div>
                <p style="color: var(--text-secondary); font-size: 14px; margin: 0; line-height: 1.6;">💡 <strong>What to do:</strong> ${verdictAdvice}</p>
            </div>
            
            <div class="quant-grid" style="margin-top: 0;">
                <!-- Quality -->
                <div class="settings-card">
                    <h4>✨ Quality <span style="float: right; color: ${scoreColor(qScore)}; font-size: 18px; font-weight: 800;">${qScore}/10</span></h4>
                    <div style="height: 8px; background: var(--bg-tertiary); border-radius: 4px; overflow: hidden; margin-bottom: 8px;">
                        <div style="height: 100%; width: ${qScore * 10}%; background: ${scoreColor(qScore)}; border-radius: 4px; transition: width 0.8s ease;"></div>
                    </div>
                    <p style="font-size: 13px; font-weight: 600; color: ${scoreColor(qScore)}; margin: 0 0 8px 0;">${scoreLabel(qScore)} — ${qExplain(qScore)}</p>
                    <ul class="breakdown-list" style="font-size: 12px; color: var(--text-muted);">
                        ${data.quality?.breakdown?.map(b => `<li>${b}</li>`).join('') || ''}
                    </ul>
                </div>
                
                <!-- Valuation -->
                <div class="settings-card">
                    <h4>💰 Valuation <span style="float: right; color: ${scoreColor(vScore)}; font-size: 18px; font-weight: 800;">${vScore}/10</span></h4>
                    <div style="height: 8px; background: var(--bg-tertiary); border-radius: 4px; overflow: hidden; margin-bottom: 8px;">
                        <div style="height: 100%; width: ${vScore * 10}%; background: ${scoreColor(vScore)}; border-radius: 4px; transition: width 0.8s ease;"></div>
                    </div>
                    <p style="font-size: 13px; font-weight: 600; color: ${scoreColor(vScore)}; margin: 0 0 8px 0;">${scoreLabel(vScore)} — ${vExplain(vScore)}</p>
                    <ul class="breakdown-list" style="font-size: 12px; color: var(--text-muted);">
                        ${data.valuation?.breakdown?.map(b => `<li>${b}</li>`).join('') || ''}
                    </ul>
                </div>
                
                <!-- Momentum -->
                <div class="settings-card">
                    <h4>🚀 Momentum <span style="float: right; color: ${scoreColor(mScore)}; font-size: 18px; font-weight: 800;">${mScore}/10</span></h4>
                    <div style="height: 8px; background: var(--bg-tertiary); border-radius: 4px; overflow: hidden; margin-bottom: 8px;">
                        <div style="height: 100%; width: ${mScore * 10}%; background: ${scoreColor(mScore)}; border-radius: 4px; transition: width 0.8s ease;"></div>
                    </div>
                    <p style="font-size: 13px; font-weight: 600; color: ${scoreColor(mScore)}; margin: 0 0 8px 0;">${scoreLabel(mScore)} — ${mExplain(mScore)}</p>
                    <ul class="breakdown-list" style="font-size: 12px; color: var(--text-muted);">
                        ${data.momentum?.breakdown?.map(b => `<li>${b}</li>`).join('') || ''}
                    </ul>
                </div>
            </div>
            
            ${data.summary ? `<p style="background: var(--bg-tertiary); padding: 16px; border-radius: 12px; border-left: 3px solid var(--accent-primary); margin-top: 16px; font-size: 14px; color: var(--text-secondary); line-height: 1.6;">📝 ${data.summary}</p>` : ''}
            ${data.data_note ? `<p style="color: var(--warning); font-size: 12px; margin-top: 12px; padding: 8px; background: rgba(255,165,0,0.1); border-radius: 6px;">⚠️ ${data.data_note}</p>` : ''}
        </div>`;

        container.innerHTML = html;

    } catch (e) {
        container.innerHTML = `<div class="empty-state"><span style="font-size:48px">❌</span><p>Error: ${e.message}</p><p style="color: var(--text-muted); font-size: 12px; margin-top: 8px;">Try a different stock symbol or check your internet connection.</p></div>`;
    }
}

// Con-Call Analyst
function initConcallAnalyst() {
    const btn = document.getElementById('concallAnalyzeBtn');

    if (btn && !btn.hasListener) {
        btn.hasListener = true;
        btn.addEventListener('click', analyzeConcall);
    }
}

async function analyzeConcall() {
    const fileInput = document.getElementById('concallFileInput');
    const statusEl = document.getElementById('concallStatus');
    const resultsEl = document.getElementById('concallResults');

    if (!fileInput.files.length) {
        showToast('Please select a PDF file', 'error');
        return;
    }

    const file = fileInput.files[0];
    statusEl.textContent = '⏳ Uploading and analyzing... This may take 30-60 seconds.';
    resultsEl.innerHTML = '';

    try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${API_BASE}/api/quant/analyze-pdf`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            statusEl.textContent = '❌ Error: ' + (data.detail || 'Analysis failed');
            return;
        }

        statusEl.textContent = '✅ Analysis complete!';

        // Render analysis results
        const analysis = data.analysis || {};
        let html = `
        <div class="concall-results">
            <div class="settings-card">
                <h4>📊 Earnings Call Analysis</h4>
                <p style="color: var(--text-muted);">Analyzed ${data.text_length?.toLocaleString() || '?'} characters</p>
            </div>
            
            <div class="settings-card">
                <h4>🚀 Growth Drivers</h4>
                <ul>${(analysis.growth_drivers || analysis['Growth Drivers'] || []).map(d => `<li>${d}</li>`).join('') || '<li>No data extracted</li>'}</ul>
            </div>
            
            <div class="settings-card">
                <h4>⚠️ Headwinds & Risks</h4>
                <ul>${(analysis.headwinds || analysis['Headwinds & Risks'] || []).map(d => `<li>${d}</li>`).join('') || '<li>No data extracted</li>'}</ul>
            </div>
            
            <div class="settings-card">
                <h4>🔍 Management Integrity Check</h4>
                <ul>${(analysis.management_integrity || analysis['Management Integrity Check'] || []).map(d => `<li>${d}</li>`).join('') || '<li>No data extracted</li>'}</ul>
            </div>
            
            ${analysis.analyst_summary || analysis['Analyst Summary'] ? `
            <div class="settings-card">
                <h4>📝 Analyst Summary</h4>
                <p>${analysis.analyst_summary || analysis['Analyst Summary']}</p>
            </div>` : ''}
        </div>`;

        resultsEl.innerHTML = html;

    } catch (e) {
        statusEl.textContent = '❌ Error: ' + e.message;
    }
}

// Market Mood
async function loadMarketMood() {
    const container = document.getElementById('marketMoodContent');
    container.innerHTML = '<div class="empty-state"><span class="loading"></span><p>Loading market mood...</p></div>';

    try {
        const data = await apiCall('/api/quant/market-mood');

        const fg = data.fear_greed_index || {};
        const score = fg.score || 50;
        const zone = fg.zone || 'Neutral';

        // Color and action based on zone
        let zoneColor = '#f59e0b', actionText = '', actionEmoji = '😐';
        if (zone.includes('Extreme Greed')) { zoneColor = '#22c55e'; actionEmoji = '🤑'; actionText = 'Market is euphoric. Be extra cautious — prices may be inflated. Avoid FOMO buying. Lock in profits on winners.'; }
        else if (zone.includes('Greed')) { zoneColor = '#a3e635'; actionEmoji = '😊'; actionText = 'Market is optimistic. Stay invested but avoid adding at high prices. Watch for signs of overheating.'; }
        else if (zone.includes('Extreme Fear')) { zoneColor = '#ef4444'; actionEmoji = '😰'; actionText = 'Maximum fear! Quality stocks are likely available at a discount. If you have cash, this is historically a great buying opportunity.'; }
        else if (zone.includes('Fear')) { zoneColor = '#fb923c'; actionEmoji = '😟'; actionText = 'Market is nervous. Good time to build a watchlist of quality stocks. Start small positions — don\'t go all in.'; }
        else { actionText = 'Market is balanced. Follow your research and invest based on fundamentals. No need to rush.'; }

        let html = `
        <div class="market-mood-container">
            <!-- Main Gauge -->
            <div style="text-align: center; margin-bottom: 24px;">
                <div style="position: relative; width: 160px; height: 160px; margin: 0 auto;">
                    <svg viewBox="0 0 36 36" style="width: 160px; height: 160px; transform: rotate(-90deg);">
                        <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="var(--bg-tertiary)" stroke-width="2.5" />
                        <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="${zoneColor}" stroke-width="2.5" stroke-dasharray="${score}, 100" stroke-linecap="round" />
                    </svg>
                    <div style="position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center;">
                        <span style="font-size: 42px; font-weight: 800; color: ${zoneColor};">${score}</span>
                        <span style="font-size: 11px; color: var(--text-muted);">/ 100</span>
                    </div>
                </div>
                <div style="margin-top: 12px;">
                    <span style="font-size: 28px;">${actionEmoji}</span>
                    <h3 style="color: ${zoneColor}; margin: 4px 0 0 0; font-size: 18px; font-weight: 700;">${zone}</h3>
                </div>
            </div>
            
            <!-- Action Card -->
            <div style="background: ${zoneColor}10; border: 1px solid ${zoneColor}40; border-radius: 16px; padding: 16px 20px; margin-bottom: 24px;">
                <p style="margin: 0; font-size: 14px; line-height: 1.6;">
                    <strong>👉 What should you do?</strong> ${actionText}
                </p>
            </div>

            ${fg.interpretation ? `<p style="color: var(--text-secondary); font-size: 14px; text-align: center; margin-bottom: 20px;">${fg.interpretation}</p>` : ''}
            
            <div class="quant-grid">
                <!-- VIX -->
                <div class="settings-card">
                    <h4>📊 India VIX</h4>
                    <div class="metric-large">${fg.components?.vix?.value || data.vix_data?.current || 'N/A'}</div>
                    <div style="height: 6px; background: var(--bg-tertiary); border-radius: 3px; overflow: hidden; margin: 8px 0;">
                        <div style="height: 100%; width: ${Math.min((fg.components?.vix?.score || 0), 100)}%; background: var(--accent-primary); border-radius: 3px;"></div>
                    </div>
                    <p style="font-size: 12px; color: var(--text-muted);">Score: ${fg.components?.vix?.score || 0}/100 (Weight: 40%)</p>
                    <div style="background: var(--bg-tertiary); padding: 8px; border-radius: 6px; margin-top: 8px;">
                        <p style="font-size: 12px; color: var(--text-muted); margin: 0;">📖 <strong>VIX</strong> = Volatility Index. Measures how "scared" the market is. Low VIX (below 15) = calm market. High VIX (above 25) = panic mode.</p>
                    </div>
                </div>
                
                <!-- Momentum -->
                <div class="settings-card">
                    <h4>📈 NIFTY Momentum</h4>
                    <div class="metric-large">${fg.components?.momentum?.roc_14 ? fg.components.momentum.roc_14 + '%' : 'N/A'}</div>
                    <p style="margin: 4px 0;">RSI: ${fg.components?.momentum?.rsi || 'N/A'}</p>
                    <div style="height: 6px; background: var(--bg-tertiary); border-radius: 3px; overflow: hidden; margin: 8px 0;">
                        <div style="height: 100%; width: ${Math.min((fg.components?.momentum?.score || 0), 100)}%; background: var(--accent-primary); border-radius: 3px;"></div>
                    </div>
                    <p style="font-size: 12px; color: var(--text-muted);">Score: ${fg.components?.momentum?.score || 0}/100 (Weight: 30%)</p>
                    <div style="background: var(--bg-tertiary); padding: 8px; border-radius: 6px; margin-top: 8px;">
                        <p style="font-size: 12px; color: var(--text-muted); margin: 0;">📖 <strong>Momentum</strong> = How fast NIFTY is moving. Positive % = market going up. Negative % = market going down.</p>
                    </div>
                </div>
                
                <!-- Breadth -->
                <div class="settings-card">
                    <h4>🎯 Market Breadth</h4>
                    <div class="metric-large">${fg.components?.breadth?.trend || 'N/A'}</div>
                    <div style="height: 6px; background: var(--bg-tertiary); border-radius: 3px; overflow: hidden; margin: 8px 0;">
                        <div style="height: 100%; width: ${Math.min((fg.components?.breadth?.score || 0), 100)}%; background: var(--accent-primary); border-radius: 3px;"></div>
                    </div>
                    <p style="font-size: 12px; color: var(--text-muted);">Score: ${fg.components?.breadth?.score || 0}/100 (Weight: 30%)</p>
                    <div style="background: var(--bg-tertiary); padding: 8px; border-radius: 6px; margin-top: 8px;">
                        <p style="font-size: 12px; color: var(--text-muted); margin: 0;">📖 <strong>Breadth</strong> = Are most stocks going up, or just a few? Positive breadth = broad rally (healthy). Negative = narrow rally (risky).</p>
                    </div>
                </div>
            </div>
            
            <p style="text-align: center; margin-top: 16px; color: var(--text-muted); font-size: 12px;">Last updated: ${new Date().toLocaleTimeString('en-IN')}</p>
        </div>`;

        container.innerHTML = html;

    } catch (e) {
        container.innerHTML = `<div class="empty-state"><span style="font-size:48px">❌</span><p>Error: ${e.message}</p><p style="color: var(--text-muted); font-size: 12px; margin-top: 8px;">Market mood data may be temporarily unavailable. Try refreshing.</p></div>`;
    }
}

// ===== Demo Con-Call Analysis =====
function showDemoConcallAnalysis() {
    const container = document.getElementById('concallResults');
    container.innerHTML = `
    <div class="concall-results" style="animation: fadeIn 0.4s ease;">
        <div style="background: linear-gradient(135deg, rgba(139,92,246,0.1), rgba(99,102,241,0.1)); border: 1px solid rgba(139,92,246,0.3); border-radius: 16px; padding: 16px 20px; margin-bottom: 20px;">
            <p style="margin: 0; font-size: 13px; color: var(--text-secondary);">📋 <strong>Sample Analysis</strong> — This is a demo using pre-analyzed data from a real con-call. Upload your own PDF to get a custom analysis.</p>
        </div>
        
        <div class="settings-card">
            <h4>📊 Earnings Call Analysis — Infosys Q3 FY25</h4>
            <p style="color: var(--text-muted);">Analyzed 45,230 characters from transcript</p>
        </div>
        
        <div class="settings-card" style="border-left: 3px solid #22c55e;">
            <h4>🚀 Growth Drivers</h4>
            <div style="background: var(--bg-tertiary); padding: 8px; border-radius: 6px; margin-bottom: 8px;">
                <p style="font-size: 12px; color: var(--text-muted); margin: 0;">📖 <strong>What are Growth Drivers?</strong> These are the positive factors fueling the company's growth. More drivers = more potential upside.</p>
            </div>
            <ul>
                <li>Large deal wins of $3.2B in Q3, highest in 8 quarters — indicates strong client confidence</li>
                <li>AI-led revenue growing at 45% YoY — well-positioned for the AI transformation wave</li>
                <li>Margin expansion of 80bps driven by pyramid optimization and automation</li>
                <li>European market showing recovery with 12% QoQ growth in financial services vertical</li>
                <li>Cloud migration pipeline remains robust at $1.8B — recurring revenue visibility</li>
            </ul>
        </div>
        
        <div class="settings-card" style="border-left: 3px solid #f59e0b;">
            <h4>⚠️ Headwinds & Risks</h4>
            <div style="background: var(--bg-tertiary); padding: 8px; border-radius: 6px; margin-bottom: 8px;">
                <p style="font-size: 12px; color: var(--text-muted); margin: 0;">📖 <strong>What are Headwinds?</strong> These are challenges or risks that could slow the company's growth. More headwinds = more caution needed.</p>
            </div>
            <ul>
                <li>Retail & CPG vertical declined 5% — discretionary spending under pressure</li>
                <li>Visa delays impacting onsite delivery in North America</li>
                <li>Currency headwinds from strong USD may impact reported margins by 40-60bps</li>
                <li>Rising subcontracting costs partially offsetting operational improvements</li>
            </ul>
        </div>
        
        <div class="settings-card" style="border-left: 3px solid #ef4444;">
            <h4>🔍 Management Integrity Check</h4>
            <div style="background: var(--bg-tertiary); padding: 8px; border-radius: 6px; margin-bottom: 8px;">
                <p style="font-size: 12px; color: var(--text-muted); margin: 0;">📖 <strong>What is this?</strong> We check if management is being transparent. Warning signs include vague answers, deflecting tough questions, or changing metrics to look better.</p>
            </div>
            <ul>
                <li>✅ Management provided specific numbers for deal pipeline and AI revenue — transparent</li>
                <li>✅ Guidance maintained at 4-7% in constant currency — no sudden revisions</li>
                <li>⚠️ Attrition question was answered vaguely — "we're comfortable with current levels"</li>
                <li>✅ CEO directly addressed margin concerns with specific cost levers</li>
            </ul>
        </div>
        
        <div class="settings-card" style="border-left: 3px solid var(--accent-primary);">
            <h4>📝 Analyst Summary</h4>
            <p>Overall, Infosys demonstrated strong execution with record deal wins and improving margins. The AI services segment is a significant growth lever. Key risks are confined to select verticals (Retail) and macro factors (currency). Management appears transparent with specific guidance. <strong>Verdict:</strong> Positive outlook for medium-term investors.</p>
        </div>
    </div>`;
    showToast('Sample analysis loaded! Upload your own PDF for custom results.', 'info');
}

// ===== Smart Search Chip Handler =====
function fillAndSendAiChat(query) {
    const input = document.getElementById('aiChatInput');
    if (input) {
        input.value = query;
        sendAiChat();
        // Hide chips after use
        const chips = document.getElementById('aiQueryChips');
        if (chips) chips.style.display = 'none';
    }
}

// ===== Live Performance Tracking =====
async function loadLivePerformance() {
    try {
        const data = await apiCall('/api/picks/live-performance');

        const section = document.getElementById('performanceSection');
        const grid = document.getElementById('performanceGrid');

        if (!data.active || data.picks.length === 0) {
            section.style.display = 'none';
            return;
        }

        section.style.display = 'block';

        grid.innerHTML = data.picks.map(pick => {
            const isGain = pick.change_pct > 0;
            const colorClass = isGain ? 'gain' : 'loss';
            const arrow = isGain ? '↑' : '↓';

            return `
                <div class="performance-card ${colorClass}" data-symbol="${pick.symbol}">
                    <div class="perf-symbol">${pick.symbol}</div>
                    <div class="perf-action">${pick.action}</div>
                    <div class="perf-prices">
                        <div class="perf-price-row">
                            <span class="label">Recommended:</span>
                            <span class="value">₹${pick.recommended_price.toLocaleString('en-IN')}</span>
                        </div>
                        <div class="perf-price-row">
                            <span class="label">Current:</span>
                            <span class="value">₹${pick.current_price.toLocaleString('en-IN')}</span>
                        </div>
                    </div>
                    <div class="perf-change ${colorClass}">
                        <span class="change-amount">${arrow} ${isGain ? '+' : ''}₹${Math.abs(pick.change).toLocaleString('en-IN')}</span>
                        <span class="change-pct">(${isGain ? '+' : ''}${pick.change_pct.toFixed(2)}%)</span>
                    </div>
                    <div class="perf-time">
                        Recommended: ${new Date(pick.recommended_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
                    </div>
                </div>
            `;
        }).join('');

        setupUniversalCardClicks(); // Enable clicks on performance cards

    } catch (error) {
        console.error('Failed to load performance:', error);
    }
}

// Auto-refresh during market hours (every 30 seconds)
function startPerformanceMonitoring() {
    // Initial load
    loadLivePerformance();

    // Refresh every 30 seconds during market hours (9:15 AM - 3:30 PM IST)
    setInterval(() => {
        const now = new Date();
        const hour = now.getHours();
        const minutes = now.getMinutes();

        // Check if in trading hours (9:15 AM - 3:30 PM) - approximate for browser timezone
        if ((hour === 9 && minutes >= 15) || (hour > 9 && hour < 15) || (hour === 15 && minutes <= 30)) {
            loadLivePerformance();
        }
    }, 30000); // 30 seconds
}

// Start monitoring when page loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', startPerformanceMonitoring);
} else {
    startPerformanceMonitoring();
}
