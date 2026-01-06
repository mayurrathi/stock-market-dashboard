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
    loadAllStarPicks();  // Load All Star section
    loadRecommendations();
    checkTelegramStatus();

    setupNavigation();
    setupTimeShortcuts();
    setupTimeframeTabs();
    setupButtons();
    setupForms();
    setupAllStarRefresh();  // Setup All Star refresh button
    setupUniversalCardClicks(); // Unified click handling for all cards
    setupAutoRefresh();     // Setup 32s Auto-Refresh
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
    document.getElementById(`${section}-section`).classList.remove('hidden');

    // Update title
    const titles = {
        dashboard: 'Dashboard',
        overview: 'Market Overview',
        watchlist: 'My Watchlist',
        messages: 'Telegram Signals',
        news: 'Market News',
        recommendations: 'Recommendations',
        sources: 'Sources',
        settings: 'Settings'
    };
    document.getElementById('sectionTitle').textContent = titles[section] || section;

    currentSection = section;

    // Load section data
    if (section === 'messages') loadMessages();
    if (section === 'news') loadNews();
    if (section === 'recommendations') loadRecommendationsFull();
    if (section === 'sources') loadSources();
    if (section === 'overview') loadMarketOverview();
    if (section === 'watchlist') loadWatchlist();
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

function refreshCurrentSection() {
    if (currentSection === 'dashboard') {
        loadDashboardStats();
        loadRecommendations();
        loadAllStarPicks();
        // Also trigger a background analysis for the shortcut for better recommendations
        if (currentShortcut) {
            apiCall('/api/analyze', {
                method: 'POST',
                body: JSON.stringify({ shortcut: currentShortcut })
            }).then(() => loadRecommendations());
        }
    } else if (currentSection === 'messages') {
        loadMessages();
    } else if (currentSection === 'news') {
        loadNews();
    } else if (currentSection === 'overview') {
        loadMarketOverview();
    } else if (currentSection === 'watchlist') {
        loadWatchlist();
    } else if (currentSection === 'recommendations') {
        loadRecommendationsFull();
    } else if (currentSection === 'sources') {
        loadSources();
    }
}

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
}

// ===== All Star Picks =====

async function loadAllStarPicks() {
    const container = document.getElementById('allstarPicks');
    const timer = document.getElementById('allstarTimer');

    try {
        const data = await apiCall('/api/allstar');

        if (data.picks && data.picks.length > 0) {
            // Update timer
            if (data.valid_until) {
                const validDate = new Date(data.valid_until);
                timer.textContent = `Valid until ${validDate.toLocaleString('en-IN', {
                    hour: '2-digit', minute: '2-digit', day: 'numeric', month: 'short'
                })}`;
            }

            container.innerHTML = data.picks.map((pick, index) => `
                <div class="allstar-card ${pick.action.toLowerCase()}" data-symbol="${pick.symbol}" style="cursor: pointer;">
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

function setupAllStarRefresh() {
    const btn = document.getElementById('refreshAllstar');
    if (btn) {
        btn.addEventListener('click', async () => {
            btn.disabled = true;
            btn.textContent = '⏳ Refreshing...';

            try {
                // Force refresh by analyzing market first
                await apiCall('/api/analyze?shortcut=last_day', { method: 'POST' });

                // Remove cached picks (they will regenerate)
                await loadAllStarPicks();
            } catch (error) {
                console.error('Failed to refresh:', error);
            } finally {
                btn.disabled = false;
                btn.textContent = '🔄 Refresh';
            }
        });
    }
}

function setupUniversalCardClicks() {
    // Single delegated listener for ALL interactive cards and tags across the dashboard
    document.addEventListener('click', (e) => {
        // Handle cards (All Star, Recommendations, News, Messages)
        const clickable = e.target.closest('.allstar-card, .rec-card, .news-card, .message-card, .watchlist-card, .stock-tag');
        if (!clickable) return;

        // Skip if clicking a nested button with its own logic
        if (e.target.closest('button')) return;

        let symbol = clickable.dataset.symbol;

        // Fallback checks for different card structures
        if (!symbol) {
            // Try multiple selectors for different card types
            const symbolEl = clickable.querySelector('.allstar-symbol, .rec-symbol, .watchlist-symbol');
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
                        <small style="color: var(--text-muted); font-size: 11px;">${rec.confidence.toFixed(1)}% confidence</small>
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

async function loadNews() {
    try {
        const params = getTimeParams();
        const data = await apiCall(`/api/news?${params}&limit=30`);
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
            const recs = data.recommendations[tf] || [];

            if (recs.length === 0) {
                container.innerHTML = '<p style="color: var(--text-muted); text-align: center;">No recommendations</p>';
                return;
            }

            container.innerHTML = recs.slice(0, 5).map(rec => `
                <div class="rec-card" onclick="showStockDetail('${rec.symbol}')" style="cursor: pointer;">
                    <div class="rec-header">
                        <span class="rec-symbol">${rec.symbol}</span>
                        <span class="rec-action ${rec.action}">${rec.action}</span>
                    </div>
                    <div style="font-size: 12px; color: var(--text-muted);">${rec.confidence.toFixed(1)}% confidence</div>
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
        alert(`Fetched ${result.messages_fetched} messages!`);
        loadSources();
        loadDashboardStats();
    } catch (error) {
        alert('Failed to fetch: ' + error.message);
    }
}

async function deleteSource(sourceId) {
    if (!confirm('Are you sure you want to delete this source?')) return;

    try {
        await apiCall(`/api/sources/${sourceId}`, { method: 'DELETE' });
        loadSources();
    } catch (error) {
        alert('Failed to delete: ' + error.message);
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
            alert(`Fetched ${result.articles_fetched} news articles!`);
            loadDashboardStats();
            if (currentSection === 'news') loadNews();
        } catch (error) {
            alert('Failed to fetch news: ' + error.message);
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
            alert(`Updated ${result.prices_fetched} stock prices!`);
            loadIndices();
        } catch (error) {
            alert('Failed to update prices: ' + error.message);
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

            alert(`Analysis complete!\nMessages analyzed: ${result.analysis.messages_analyzed}\nNews analyzed: ${result.analysis.news_analyzed}\nRecommendations generated: ${result.recommendations.length}`);

            loadRecommendations();
            loadDashboardStats();
        } catch (error) {
            alert('Analysis failed: ' + error.message);
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
            alert('Failed to add source: ' + error.message);
        }
    });

    // Telegram Auth
    document.getElementById('sendCodeBtn').addEventListener('click', async () => {
        const apiId = document.getElementById('apiId').value;
        const apiHash = document.getElementById('apiHash').value;
        const phone = document.getElementById('phoneNumber').value;

        if (!apiId || !apiHash || !phone) {
            alert('Please fill all fields');
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
            alert('Verification code sent to your Telegram!');
        } catch (error) {
            alert('Failed to send code: ' + error.message);
        }
    });

    document.getElementById('verifyCodeBtn').addEventListener('click', async () => {
        const phone = document.getElementById('phoneNumber').value;
        const code = document.getElementById('verifyCode').value;

        if (!code) {
            alert('Please enter the verification code');
            return;
        }

        try {
            const result = await apiCall('/api/telegram/verify', {
                method: 'POST',
                body: JSON.stringify({ phone, code })
            });

            if (result.status === 'authenticated') {
                alert('Telegram connected successfully!');
                checkTelegramStatus();
            } else if (result.status === '2fa_required') {
                alert('2FA required. Please enter your 2FA password.');
            } else {
                alert('Verification failed: ' + result.message);
            }
        } catch (error) {
            alert('Verification failed: ' + error.message);
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

        container.innerHTML = `
            <div class="watchlist-cards">
                ${data.stocks.map(s => `
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

    } catch (error) {
        container.innerHTML = `<div class="empty-state"><span>❌</span><p>Failed to load watchlist: ${error.message}</p></div>`;
    }
}

// Stock chart instance (for cleanup)
let stockChartInstance = null;

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
    const container = document.getElementById('stockRecsList');
    if (!container) return;

    if (!recs || recs.length === 0) {
        container.innerHTML = `
            <div style="padding: 16px; background: rgba(255, 255, 255, 0.03); border-radius: 8px; border: 1px dashed var(--border-color);">
                <p style="color: var(--text-muted); font-size: 13px; margin: 0;">
                    💡 No AI recommendations currently available for this stock. 
                    This usually happens if there hasn't been enough recent news coverage or Telegram signals for a detailed analysis.
                </p>
                <button class="btn btn-secondary" onclick="refreshCurrentSection()" style="margin-top: 12px; font-size: 12px; padding: 4px 12px;">🔍 Analyze Market News</button>
            </div>
        `;
        return;
    }

    container.innerHTML = recs.map(r => `
        <div class="rec-row">
            <span class="rec-timeframe">${r.timeframe.replace('_', ' ')}</span>
            <span class="rec-action ${r.action.toLowerCase()}">${r.action}</span>
            <span class="rec-confidence" style="font-weight: 700; color: var(--text-primary);">${r.confidence?.toFixed(0) || '--'}%</span>
            ${r.reasoning ? `<div class="rec-reasoning">${r.reasoning}</div>` : ''}
        </div>
    `).join('');
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

    container.innerHTML = linkItems.map(item =>
        links[item.key] ? `<a href="${links[item.key]}" target="_blank" class="external-link-btn">${item.icon} ${item.label}</a>` : ''
    ).join('');
}


async function removeFromWatchlist(symbol) {
    if (!confirm(`Remove ${symbol} from watchlist?`)) return;

    try {
        await apiCall(`/api/watchlist/${symbol}`, { method: 'DELETE' });
        loadWatchlist();
    } catch (error) {
        alert('Failed to remove: ' + error.message);
    }
}

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
                if (result.auto_calculated) {
                    alert(`${symbol.toUpperCase()} added!\n\nAuto-calculated:\nTarget: ₹${result.target_price}\nStop Loss: ₹${result.stop_loss}`);
                }
            } catch (error) {
                alert('Failed to add stock: ' + error.message);
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
        analyzeBtn.addEventListener('click', async () => {
            analyzeBtn.disabled = true;
            analyzeBtn.innerHTML = '<span class="loading"></span> Analyzing...';

            try {
                const result = await apiCall('/api/market/analyze', { method: 'POST' });
                alert(result.message);
                loadMarketOverview();
            } catch (error) {
                alert('Analysis failed: ' + error.message);
            } finally {
                analyzeBtn.disabled = false;
                analyzeBtn.innerHTML = '🔍 Analyze Market';
            }
        });
    }
});

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

