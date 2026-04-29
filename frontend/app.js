/**
 * ScheduleLink - Frontend Application v2.1.0
 * Production-ready SPA with hash-based routing
 * 
 * Key Features:
 * - Public booking pages (NO auth required)
 * - Protected dashboard routes (auth required)
 * - Robust error handling
 * - Professional UI/UX
 * 
 * CRITICAL: Public routes NEVER check auth status
 */

// API URL - always point to the Render backend API (Vercel is static-only)
const API_URL = 'https://schedulelink-app.onrender.com';

// ============== Subscription Tier Helpers ==============
function getTierName(status) {
    const tierMap = {
        'pro_plus': 'Pro+',
        'pro': 'Pro',
        'free': 'Free'
    };
    return tierMap[status] || 'Free';
}

function getTierDisplay(isPaid, status) {
    if (isPaid) {
        const name = getTierName(status);
        if (name === 'Pro+') return '<span class="subscription-badge pro-plus">✨ Pro+</span>';
        if (name === 'Pro') return '<span class="subscription-badge pro">✨ Pro</span>';
    }
    return '<span class="subscription-badge free">Free</span>';
}

function showUpgradeBanner() {
    // Check sessionStorage for just-upgraded flag (set after successful Stripe return)
    const justUpgraded = sessionStorage.getItem('just_upgraded');
    const tier = sessionStorage.getItem('upgraded_tier') || 'Pro';
    if (justUpgraded === 'true') {
        sessionStorage.removeItem('just_upgraded');
        sessionStorage.removeItem('upgraded_tier');
        return `<div class="alert alert-success upgrade-banner">
            <strong>🎉 Welcome to ${tier}!</strong> Your upgrade is complete. Enjoy your new features!
        </div>`;
    }
    return '';
}

// ============== State ==============
let state = {
    user: null,
    token: localStorage.getItem('schedulelink_token'),
    currentView: 'loading',
    config: null,
    selectedBookingsDate: null,
    bookingsCalendarMonth: new Date().getMonth(),
    bookingsCalendarYear: new Date().getFullYear()
};

// ============== API Client ==============
async function api(endpoint, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };
    
    if (state.token) {
        headers['Authorization'] = `Bearer ${state.token}`;
    }
    
    try {
        const response = await fetch(`${API_URL}${endpoint}`, {
            ...options,
            headers
        });
        
        // Handle 401 only for protected endpoints
        if (response.status === 401 && !endpoint.startsWith('/api/public') && !endpoint.startsWith('/api/cancel')) {
            logout();
            throw new Error('Session expired. Please log in again.');
        }
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Request failed');
        }
        
        return data;
    } catch (err) {
        if (err.name === 'TypeError' && err.message.includes('fetch')) {
            throw new Error('Unable to connect to server. Please try again.');
        }
        throw err;
    }
}

// ============== Auth ==============
function setToken(token) {
    state.token = token;
    localStorage.setItem('schedulelink_token', token);
}

function logout() {
    state.token = null;
    state.user = null;
    localStorage.removeItem('schedulelink_token');
    navigate('login');
}

async function checkAuth() {
    if (!state.token) return false;
    
    try {
        state.user = await api('/api/auth/me');
        return true;
    } catch (e) {
        state.token = null;
        localStorage.removeItem('schedulelink_token');
        return false;
    }
}

// ============== Router ==============
function navigate(view, params = {}) {
    const hash = Object.keys(params).length 
        ? `#/${view}?${new URLSearchParams(params)}`
        : `#/${view}`;
    window.location.hash = hash;
}

function parseHash() {
    const hash = window.location.hash.slice(2) || '';
    const [path, queryString] = hash.split('?');
    const params = new URLSearchParams(queryString || '');
    return { path: path || '', params };
}

async function router() {
    const { path, params } = parseHash();
    const app = document.getElementById('app');
    
    // PUBLIC ROUTES - NO AUTH CHECK EVER
    // These routes must work for anonymous visitors
    
    if (path === 'login') {
        app.innerHTML = renderLogin();
        return;
    }
    
    if (path === 'register') {
        app.innerHTML = renderRegister();
        return;
    }
    
    if (path.startsWith('book/')) {
        const username = path.split('/')[1];
        if (username) {
            await renderBookingPage(username);
            return;
        }
    }
    
    if (path.startsWith('cancel/')) {
        const token = path.split('/')[1];
        if (token) {
            await renderCancelPage(token);
            return;
        }
    }
    
    // Default to login/dashboard based on auth
    if (!path) {
        if (state.token) {
            const isAuth = await checkAuth();
            if (isAuth) {
                navigate('dashboard');
                return;
            }
        }
        navigate('login');
        return;
    }
    
    // PROTECTED ROUTES - AUTH REQUIRED
    const isAuth = await checkAuth();
    if (!isAuth) {
        navigate('login');
        return;
    }
    
    // Render layout with content
    let content = '';
    
    switch (path) {
        case 'dashboard':
            content = await renderDashboard();
            break;
        case 'bookings':
            content = await renderBookings();
            break;
        case 'settings':
            content = await renderSettings(params);
            break;
        default:
            content = await renderDashboard();
    }
    
    app.innerHTML = renderLayout(content, path);
}

// ============== Layout ==============
function renderLayout(content, activePath) {
    const badge = getTierDisplay(state.user?.subscription_status && state.user?.subscription_status !== 'free', state.user?.subscription_status);
    
    return `
        <header class="header">
            <div class="container header-content">
                <a href="#/dashboard" class="logo">📅 ScheduleLink</a>
                <nav class="nav">
                    <a href="#/dashboard" class="${activePath === 'dashboard' ? 'active' : ''}">Dashboard</a>
                    <a href="#/bookings" class="${activePath === 'bookings' ? 'active' : ''}">Bookings</a>
                    <a href="#/settings" class="${activePath === 'settings' ? 'active' : ''}">Settings</a>
                </nav>
                <div class="user-menu">
                    ${badge}
                    <span class="user-name">${state.user?.full_name || state.user?.email}</span>
                    <button class="btn btn-secondary btn-sm" onclick="logout()">Logout</button>
                </div>
            </div>
        </header>
        <main class="container">
            ${content}
        </main>
    `;
}

// ============== Login Page ==============
function renderPublicHeader(active) {
    return `
        <header class="public-header">
            <div class="container public-header-content">
                <a href="#/" class="public-logo">📅 ScheduleLink</a>
                <div class="public-header-actions">
                    ${active === 'login' 
                        ? '<a href="#/register" class="btn-sign-up">Create Account</a>'
                        : '<a href="#/login" class="btn-sign-in-landing">Sign In</a>'
                    }
                </div>
            </div>
        </header>
    `;
}

function renderLogin() {
    setTimeout(() => {
        document.getElementById('login-form')?.addEventListener('submit', handleLogin);
    }, 0);
    
    return `
        ${renderPublicHeader('login')}
        <div class="auth-page">
            <div class="auth-card">
                <div class="auth-logo">
                    <h1>📅 ScheduleLink</h1>
                    <p>Simple scheduling for busy people</p>
                </div>
                
                <form id="login-form">
                    <div id="login-error" class="alert alert-error" style="display: none;"></div>
                    
                    <div class="form-group">
                        <label class="form-label">Email</label>
                        <input type="email" name="email" class="form-input" placeholder="you@example.com" required>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Password</label>
                        <input type="password" name="password" class="form-input" placeholder="••••••••" required>
                    </div>
                    
                    <button type="submit" class="btn btn-primary btn-lg" style="width: 100%;">
                        Sign In
                    </button>
                </form>
                
                <div class="auth-footer">
                    Don't have an account? <a href="#/register">Create one</a>
                </div>
            </div>
        </div>
    `;
}

async function handleLogin(e) {
    e.preventDefault();
    const form = e.target;
    const errorEl = document.getElementById('login-error');
    const btn = form.querySelector('button[type="submit"]');
    
    btn.disabled = true;
    btn.textContent = 'Signing in...';
    errorEl.style.display = 'none';
    
    try {
        const data = await api('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify({
                email: form.email.value,
                password: form.password.value
            })
        });
        
        setToken(data.access_token);
        navigate('dashboard');
    } catch (err) {
        errorEl.textContent = err.message;
        errorEl.style.display = 'block';
        btn.disabled = false;
        btn.textContent = 'Sign In';
    }
}

// ============== Register Page ==============
function renderRegister() {
    setTimeout(() => {
        document.getElementById('register-form')?.addEventListener('submit', handleRegister);
    }, 0);
    
    return `
        ${renderPublicHeader('register')}
        <div class="auth-page">
            <div class="auth-card">
                <div class="auth-logo">
                    <h1>📅 ScheduleLink</h1>
                    <p>Create your scheduling page</p>
                </div>
                
                <form id="register-form">
                    <div id="register-error" class="alert alert-error" style="display: none;"></div>
                    
                    <div class="form-group">
                        <label class="form-label">Full Name</label>
                        <input type="text" name="full_name" class="form-input" placeholder="John Smith">
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Email</label>
                        <input type="email" name="email" class="form-input" placeholder="you@example.com" required>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Username</label>
                        <input type="text" name="username" class="form-input" required 
                               pattern="[a-z0-9-]+" placeholder="john-smith" 
                               oninput="this.value = this.value.toLowerCase().replace(/[^a-z0-9-]/g, '')">
                        <p class="form-hint">Your booking link: ${window.location.origin}/#/book/<strong>your-username</strong></p>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Password</label>
                        <input type="password" name="password" class="form-input" placeholder="••••••••" required minlength="6">
                        <p class="form-hint">At least 6 characters</p>
                    </div>
                    
                    <button type="submit" class="btn btn-primary btn-lg" style="width: 100%;">
                        Create Account
                    </button>
                </form>
                
                <div class="auth-footer">
                    Already have an account? <a href="#/login">Sign in</a>
                </div>
            </div>
        </div>
    `;
}

async function handleRegister(e) {
    e.preventDefault();
    const form = e.target;
    const errorEl = document.getElementById('register-error');
    const btn = form.querySelector('button[type="submit"]');
    
    btn.disabled = true;
    btn.textContent = 'Creating account...';
    errorEl.style.display = 'none';
    
    try {
        const data = await api('/api/auth/register', {
            method: 'POST',
            body: JSON.stringify({
                email: form.email.value,
                password: form.password.value,
                username: form.username.value.toLowerCase(),
                full_name: form.full_name.value || null
            })
        });
        
        setToken(data.access_token);
        navigate('dashboard');
    } catch (err) {
        errorEl.textContent = err.message;
        errorEl.style.display = 'block';
        btn.disabled = false;
        btn.textContent = 'Create Account';
    }
}

// ============== Dashboard ==============
async function renderDashboard() {
    let bookings = [];
    try {
        bookings = await api('/api/bookings/upcoming');
    } catch (e) {
        console.error('Failed to load bookings:', e);
    }
    
    const bookingLink = `${window.location.origin}/#/book/${state.user.username}`;
    const tierName = getTierName(state.user.subscription_status);
    const upgradeBanner = showUpgradeBanner();
    
    return `
        <div class="dashboard">
            ${upgradeBanner}
            <div class="dashboard-header">
                <h1>Welcome back, ${state.user.full_name || state.user.username}!</h1>
                <p>Manage your bookings and availability</p>
            </div>
            
            <div class="booking-link-card">
                <h3>Your Booking Link</h3>
                <div class="booking-link-wrapper">
                    <input type="text" value="${bookingLink}" readonly id="booking-link-input">
                    <button class="booking-link-copy" onclick="copyBookingLink()">📋 Copy</button>
                </div>
            </div>
            
            <div class="google-status ${state.user.google_connected ? 'connected' : 'disconnected'}">
                ${state.user.google_connected 
                    ? '✓ Google Calendar connected — bookings sync automatically' 
                    : '⚠ Google Calendar not connected'}
                <a href="#/settings">
                    ${state.user.google_connected ? 'Manage' : 'Connect'}
                </a>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="label">Upcoming Meetings</div>
                    <div class="value">${bookings.length}</div>
                </div>
                <div class="stat-card">
                    <div class="label">Meeting Duration</div>
                    <div class="value">${state.user.meeting_duration}m</div>
                </div>
                <div class="stat-card">
                    <div class="label">Current Plan</div>
                    <div class="value plan-value">${tierName}</div>
                </div>
            </div>
            
            ${state.user.subscription_status && state.user.subscription_status !== 'free' ? `
                <div class="card plan-card">
                    <div class="plan-card-content">
                        <span class="plan-card-icon">✨</span>
                        <div>
                            <h3 class="card-title">${tierName} Member</h3>
                            <p style="color: var(--text-secondary); margin-top: 4px;">You're all set! Enjoy unlimited bookings and all ${tierName} features.</p>
                        </div>
                    </div>
                </div>
            ` : `
                <div class="card" style="background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(139, 92, 246, 0.1)); border-color: var(--primary);">
                    <h3 class="card-title">✨ Upgrade to Pro</h3>
                    <p style="margin-bottom: 20px; color: var(--text-secondary);">
                        Get unlimited bookings, priority support, and help us keep ScheduleLink running.
                    </p>
                    <ul style="margin-bottom: 24px; color: var(--text-secondary); list-style: none;">
                        <li style="margin-bottom: 8px;">✓ Unlimited bookings</li>
                        <li style="margin-bottom: 8px;">✓ 7-day free trial</li>
                        <li style="margin-bottom: 8px;">✓ Priority email support</li>
                        <li>✓ Cancel anytime</li>
                    </ul>
                    <button class="btn btn-primary btn-lg" onclick="upgradeToPro()">Upgrade Now — $5/month</button>
                </div>
            `}
            
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">Upcoming Meetings</h3>
                    <a href="#/bookings" class="btn btn-secondary btn-sm">View All</a>
                </div>
                
                ${bookings.length === 0 
                    ? '<div class="empty-state"><p>No upcoming meetings. Share your booking link to get started!</p></div>'
                    : bookings.slice(0, 5).map(b => renderBookingItem(b)).join('')
                }
            </div>
        </div>
    `;
}

function renderBookingItem(booking) {
    const start = new Date(booking.start_time);
    const dateStr = start.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
    const timeStr = start.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
    
    return `
        <div class="booking-item">
            <div class="booking-info">
                <h4>${escapeHtml(booking.client_name)}</h4>
                <p>${escapeHtml(booking.client_email)}</p>
            </div>
            <div class="booking-time">
                <div class="date">${dateStr}</div>
                <div class="time">${timeStr}</div>
            </div>
        </div>
    `;
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function copyBookingLink() {
    const input = document.getElementById('booking-link-input');
    input.select();
    input.setSelectionRange(0, 99999);
    
    navigator.clipboard.writeText(input.value).then(() => {
        const btn = input.nextElementSibling;
        btn.textContent = '✓ Copied!';
        setTimeout(() => { btn.textContent = '📋 Copy'; }, 2000);
    });
}

// ============== Bookings Page ==============
async function renderBookings() {
    let bookings = [];
    try {
        bookings = await api('/api/bookings');
    } catch (e) {
        console.error('Failed to load bookings:', e);
    }
    
    const month = state.bookingsCalendarMonth;
    const year = state.bookingsCalendarYear;
    const selectedDate = state.selectedBookingsDate;
    
    const filteredBookings = selectedDate
        ? bookings.filter(b => {
            const d = new Date(b.start_time).toISOString().split('T')[0];
            return d === selectedDate;
        })
        : bookings;
    
    const monthName = new Date(year, month).toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
    
    return `
        <div class="dashboard">
            <div class="dashboard-header">
                <h1>Your Bookings</h1>
                <p>View and manage all your meetings</p>
            </div>
            
            <div class="card">
                <div class="bookings-calendar-nav">
                    <button class="btn btn-sm btn-secondary" onclick="prevBookingsMonth()">&#8249;</button>
                    <span class="bookings-calendar-month">${monthName}</span>
                    <button class="btn btn-sm btn-secondary" onclick="nextBookingsMonth()">&#8250;</button>
                </div>
                ${renderBookingsCalendar(bookings, month, year, selectedDate)}
            </div>
            
            <div class="bookings-list-section">
                <div class="bookings-list-header">
                    <h3>${selectedDate ? formatDateLong(selectedDate) : 'All Bookings'}</h3>
                    ${selectedDate ? '<button class="btn btn-sm btn-secondary" onclick="clearBookingsDate()">Show all</button>' : ''}
                </div>
                <div class="card">
                    ${filteredBookings.length === 0 
                        ? '<div class="empty-state"><p>No bookings' + (selectedDate ? ' on this date' : '') + '.</p></div>'
                        : filteredBookings.map(b => renderBookingItemFull(b)).join('')
                    }
                </div>
            </div>
        </div>
    `;
}

function renderBookingsCalendar(bookings, month, year, selectedDate) {
    const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const startOffset = firstDay.getDay();
    const totalDays = lastDay.getDate();
    
    // Build a set of dates that have bookings
    const datesWithBookings = new Set(
        bookings.map(b => new Date(b.start_time).toISOString().split('T')[0])
    );
    
    let html = `<div class="calendar-grid">`;
    html += days.map(d => `<div class="calendar-header">${d}</div>`).join('');
    
    // Empty cells before first day
    for (let i = 0; i < startOffset; i++) {
        html += '<div class="calendar-day disabled"></div>';
    }
    
    // Days of the month
    for (let d = 1; d <= totalDays; d++) {
        const date = new Date(year, month, d);
        const dateStr = date.toISOString().split('T')[0];
        const hasBookings = datesWithBookings.has(dateStr);
        const isSelected = selectedDate === dateStr;
        const isToday = new Date().toISOString().split('T')[0] === dateStr;
        
        let className = 'calendar-day';
        if (isSelected) className += ' selected';
        else if (hasBookings) className += ' has-bookings';
        if (isToday) className += ' today';
        if (!hasBookings) className += ' disabled';
        
        const onClick = hasBookings ? `onclick="selectBookingsDate('${dateStr}')"` : '';
        html += `<div class="${className}" ${onClick}>${d}</div>`;
    }
    
    // Fill remaining cells
    const totalCells = startOffset + totalDays;
    const remaining = (7 - (totalCells % 7)) % 7;
    for (let i = 0; i < remaining; i++) {
        html += '<div class="calendar-day disabled"></div>';
    }
    
    html += '</div>';
    return html;
}

function selectBookingsDate(dateStr) {
    state.selectedBookingsDate = state.selectedBookingsDate === dateStr ? null : dateStr;
    document.getElementById('app').innerHTML = renderLayout(renderBookings(), 'bookings');
}

function prevBookingsMonth() {
    let m = state.bookingsCalendarMonth - 1;
    let y = state.bookingsCalendarYear;
    if (m < 0) { m = 11; y--; }
    state.bookingsCalendarMonth = m;
    state.bookingsCalendarYear = y;
    state.selectedBookingsDate = null;
    document.getElementById('app').innerHTML = renderLayout(renderBookings(), 'bookings');
}

function nextBookingsMonth() {
    let m = state.bookingsCalendarMonth + 1;
    let y = state.bookingsCalendarYear;
    if (m > 11) { m = 0; y++; }
    state.bookingsCalendarMonth = m;
    state.bookingsCalendarYear = y;
    state.selectedBookingsDate = null;
    document.getElementById('app').innerHTML = renderLayout(renderBookings(), 'bookings');
}

function clearBookingsDate() {
    state.selectedBookingsDate = null;
    document.getElementById('app').innerHTML = renderLayout(renderBookings(), 'bookings');
}

function formatDateLong(dateStr) {
    const d = new Date(dateStr + 'T00:00:00');
    return d.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
}

function renderBookingItemFull(booking) {
    const start = new Date(booking.start_time);
    const dateStr = start.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
    const timeStr = start.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
    const isCancelled = booking.status === 'cancelled';
    const isPast = start < new Date();
    
    return `
        <div class="booking-item" style="${isCancelled ? 'opacity: 0.5;' : ''}">
            <div class="booking-info">
                <h4>${escapeHtml(booking.client_name)} ${isCancelled ? '<span style="color: var(--danger);">(Cancelled)</span>' : ''}</h4>
                <p>${escapeHtml(booking.client_email)}${booking.client_phone ? ' • ' + escapeHtml(booking.client_phone) : ''}</p>
                ${booking.notes ? `<p style="margin-top: 8px; font-style: italic; color: var(--text-muted);">"${escapeHtml(booking.notes)}"</p>` : ''}
            </div>
            <div class="booking-time">
                <div class="date">${dateStr}</div>
                <div class="time">${timeStr}</div>
                ${!isCancelled && !isPast 
                    ? `<button class="btn btn-danger btn-sm" style="margin-top: 12px;" onclick="cancelBooking(${booking.id})">Cancel</button>`
                    : ''
                }
            </div>
        </div>
    `;
}

async function cancelBooking(id) {
    if (!confirm('Are you sure you want to cancel this booking? The client will be notified.')) return;
    
    try {
        await api(`/api/bookings/${id}`, { method: 'DELETE' });
        router(); // Refresh
    } catch (err) {
        alert('Failed to cancel booking: ' + err.message);
    }
}

// ============== Settings Page ==============
async function renderSettings(params) {
    let workingHours = [];
    try {
        workingHours = await api('/api/working-hours');
    } catch (e) {
        console.error('Failed to load working hours:', e);
    }
    
    const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    
    // Check for tier param from Stripe return (for immediate tier detection)
    const tierParam = params.get('tier');
    if (tierParam) {
        sessionStorage.setItem('just_upgraded', 'true');
        sessionStorage.setItem('upgraded_tier', tierParam === 'pro_plus' ? 'Pro+' : 'Pro');
    }
    
    // Refresh user data on settings load to get latest subscription status
    try {
        state.user = await api('/api/auth/me');
    } catch (e) {}
    
    const tierName = getTierName(state.user.subscription_status);
    const isProPlus = tierName === 'Pro+';
    const isPro = tierName === 'Pro';
    const isPaid = state.user.subscription_status && state.user.subscription_status !== 'free';
    
    let alerts = '';
    if (params.get('google') === 'connected') {
        alerts = '<div class="alert alert-success">✓ Google Calendar connected successfully!</div>';
    } else if (params.get('google') === 'error') {
        alerts = '<div class="alert alert-error">Failed to connect Google Calendar. Please try again.</div>';
    }
    if (params.get('billing') === 'success') {
        const upgradedTier = params.get('tier') === 'pro_plus' ? 'Pro+' : 'Pro';
        alerts = `<div class="alert alert-success upgrade-success-banner">
            <strong>🎉 Welcome to ${upgradedTier}!</strong> Your upgrade is complete. You now have access to all ${upgradedTier} features!
        </div>`;
    } else if (params.get('billing') === 'cancelled') {
        alerts = '<div class="alert alert-info">Checkout was cancelled. You can upgrade anytime.</div>';
    }
    
    setTimeout(() => {
        document.getElementById('settings-form')?.addEventListener('submit', handleSettingsSave);
        document.getElementById('working-hours-form')?.addEventListener('submit', handleWorkingHoursSave);
    }, 0);
    
    return `
        <div class="dashboard">
            <div class="dashboard-header">
                <h1>Settings</h1>
                <p>Configure your scheduling preferences</p>
            </div>
            
            ${alerts}
            
            <div class="card">
                <h3 class="card-title">Profile</h3>
                <form id="settings-form">
                    <div class="form-group">
                        <label class="form-label">Full Name</label>
                        <input type="text" name="full_name" class="form-input" value="${escapeHtml(state.user.full_name || '')}" placeholder="Your name">
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Meeting Duration</label>
                        <select name="meeting_duration" class="form-select">
                            <option value="15" ${state.user.meeting_duration === 15 ? 'selected' : ''}>15 minutes</option>
                            <option value="30" ${state.user.meeting_duration === 30 ? 'selected' : ''}>30 minutes</option>
                            <option value="45" ${state.user.meeting_duration === 45 ? 'selected' : ''}>45 minutes</option>
                            <option value="60" ${state.user.meeting_duration === 60 ? 'selected' : ''}>60 minutes</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Buffer Between Meetings</label>
                        <select name="buffer_time" class="form-select">
                            <option value="0" ${state.user.buffer_time === 0 ? 'selected' : ''}>No buffer</option>
                            <option value="5" ${state.user.buffer_time === 5 ? 'selected' : ''}>5 minutes</option>
                            <option value="10" ${state.user.buffer_time === 10 ? 'selected' : ''}>10 minutes</option>
                            <option value="15" ${state.user.buffer_time === 15 ? 'selected' : ''}>15 minutes</option>
                            <option value="30" ${state.user.buffer_time === 30 ? 'selected' : ''}>30 minutes</option>
                        </select>
                    </div>
                    
                    <button type="submit" class="btn btn-primary">Save Profile</button>
                </form>
            </div>
            
            <div class="card">
                <h3 class="card-title">Google Calendar</h3>
                ${state.user.google_connected 
                    ? `
                        <div class="google-status connected" style="margin-bottom: 16px;">
                            ✓ Connected to Google Calendar
                        </div>
                        <p style="margin-bottom: 16px; color: var(--text-muted);">
                            Your bookings automatically sync to your calendar and show your real availability.
                        </p>
                        <button class="btn btn-secondary" onclick="disconnectGoogle()">Disconnect</button>
                    `
                    : `
                        <p style="margin-bottom: 16px; color: var(--text-muted);">
                            Connect your Google Calendar to automatically show your real availability and create events for bookings.
                        </p>
                        <button class="btn btn-primary" onclick="connectGoogle()">Connect Google Calendar</button>
                    `
                }
            </div>
            
            <div class="card">
                <h3 class="card-title">Working Hours</h3>
                <p style="margin-bottom: 20px; color: var(--text-muted);">Set when you're available for bookings</p>
                <form id="working-hours-form">
                    <div class="working-hours">
                        ${days.map((day, i) => {
                            const wh = workingHours.find(h => h.day_of_week === i) || { start_time: '09:00', end_time: '17:00', is_enabled: false };
                            return `
                                <div class="day-row">
                                    <div class="day-toggle">
                                        <input type="checkbox" id="enabled_${i}" name="enabled_${i}" ${wh.is_enabled ? 'checked' : ''}>
                                        <label for="enabled_${i}">${day}</label>
                                    </div>
                                    <div class="time-inputs">
                                        <input type="time" name="start_${i}" value="${wh.start_time}">
                                        <span>to</span>
                                        <input type="time" name="end_${i}" value="${wh.end_time}">
                                    </div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                    <button type="submit" class="btn btn-primary" style="margin-top: 24px;">Save Working Hours</button>
                </form>
            </div>
            
            ${!isPaid ? `
                <div class="card" style="background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(139, 92, 246, 0.1)); border-color: var(--primary);">
                    <h3 class="card-title">✨ Upgrade to Pro</h3>
                    <p style="margin-bottom: 20px; color: var(--text-secondary);">
                        Get unlimited bookings, priority support, and help us keep ScheduleLink running.
                    </p>
                    <ul style="margin-bottom: 24px; color: var(--text-secondary); list-style: none;">
                        <li style="margin-bottom: 8px;">✓ Unlimited bookings</li>
                        <li style="margin-bottom: 8px;">✓ 7-day free trial</li>
                        <li style="margin-bottom: 8px;">✓ Priority email support</li>
                        <li>✓ Cancel anytime</li>
                    </ul>
                    <button class="btn btn-primary btn-lg" onclick="upgradeToPro()">Upgrade Now — $5/month</button>
                </div>
            ` : isProPlus ? `
                <div class="card">
                    <h3 class="card-title">✨ Pro+ Subscription</h3>
                    <div class="google-status connected" style="margin-bottom: 16px;">
                        ✓ You're on the <strong>Pro+</strong> plan — the best ScheduleLink has to offer!
                    </div>
                    <p style="color: var(--text-secondary); margin-bottom: 16px;">You have access to all features. Manage your subscription below.</p>
                    <button class="btn btn-secondary" onclick="manageBilling()">Manage Billing</button>
                </div>
            ` : `
                <div class="card">
                    <h3 class="card-title">✨ Pro Subscription</h3>
                    <div class="google-status connected" style="margin-bottom: 16px;">
                        ✓ You're on the <strong>Pro</strong> plan
                    </div>
                    <p style="color: var(--text-secondary); margin-bottom: 16px;">
                        Want more? Upgrade to <strong>Pro+</strong> for additional features.
                    </p>
                    <button class="btn btn-primary" onclick="upgradeToProPlus()">Upgrade to Pro+</button>
                    <button class="btn btn-secondary" style="margin-left: 12px;" onclick="manageBilling()">Manage Billing</button>
                </div>
            `}
        </div>
    `;
}

async function handleSettingsSave(e) {
    e.preventDefault();
    const form = e.target;
    const btn = form.querySelector('button[type="submit"]');
    
    btn.disabled = true;
    btn.textContent = 'Saving...';
    
    try {
        await api('/api/settings', {
            method: 'PATCH',
            body: JSON.stringify({
                full_name: form.full_name.value,
                meeting_duration: parseInt(form.meeting_duration.value),
                buffer_time: parseInt(form.buffer_time.value)
            })
        });
        
        state.user = await api('/api/auth/me');
        btn.textContent = '✓ Saved!';
        setTimeout(() => { btn.textContent = 'Save Profile'; btn.disabled = false; }, 2000);
    } catch (err) {
        alert('Failed to save: ' + err.message);
        btn.disabled = false;
        btn.textContent = 'Save Profile';
    }
}

async function handleWorkingHoursSave(e) {
    e.preventDefault();
    const form = e.target;
    const btn = form.querySelector('button[type="submit"]');
    
    btn.disabled = true;
    btn.textContent = 'Saving...';
    
    const hours = [];
    for (let i = 0; i < 7; i++) {
        hours.push({
            day_of_week: i,
            start_time: form[`start_${i}`].value,
            end_time: form[`end_${i}`].value,
            is_enabled: form[`enabled_${i}`].checked
        });
    }
    
    try {
        await api('/api/working-hours', {
            method: 'PUT',
            body: JSON.stringify(hours)
        });
        btn.textContent = '✓ Saved!';
        setTimeout(() => { btn.textContent = 'Save Working Hours'; btn.disabled = false; }, 2000);
    } catch (err) {
        alert('Failed to save: ' + err.message);
        btn.disabled = false;
        btn.textContent = 'Save Working Hours';
    }
}

async function connectGoogle() {
    try {
        const data = await api('/api/auth/google');
        window.location.href = data.auth_url;
    } catch (err) {
        alert('Failed to start Google auth: ' + err.message);
    }
}

async function disconnectGoogle() {
    if (!confirm('Disconnect Google Calendar? Your bookings will no longer sync.')) return;
    
    try {
        await api('/api/auth/google/disconnect', { method: 'POST' });
        state.user = await api('/api/auth/me');
        router();
    } catch (err) {
        alert('Failed to disconnect: ' + err.message);
    }
}

async function upgradeToPro() {
    try {
        const data = await api('/api/billing/checkout');
        // Set flag so dashboard shows welcome banner on return
        sessionStorage.setItem('just_upgraded', 'true');
        sessionStorage.setItem('upgraded_tier', 'Pro');
        window.location.href = data.checkout_url;
    } catch (err) {
        alert('Billing not available: ' + err.message);
    }
}

async function upgradeToProPlus() {
    try {
        const data = await api('/api/billing/checkout', {
            method: 'POST',
            body: JSON.stringify({ tier: 'pro_plus' })
        });
        sessionStorage.setItem('just_upgraded', 'true');
        sessionStorage.setItem('upgraded_tier', 'Pro+');
        window.location.href = data.checkout_url;
    } catch (err) {
        alert('Billing not available: ' + err.message);
    }
}

async function manageBilling() {
    try {
        const data = await api('/api/billing/portal');
        window.location.href = data.portal_url;
    } catch (err) {
        alert('Failed to open billing portal: ' + err.message);
    }
}

// ============== Public Booking Page ==============
let bookingState = {
    profile: null,
    availability: [],
    selectedDate: null,
    selectedSlot: null
};

async function renderBookingPage(username) {
    const app = document.getElementById('app');
    
    app.innerHTML = '<div class="loading">Loading booking page...</div>';
    
    try {
        // Fetch public profile - NO AUTH HEADER
        const profileRes = await fetch(`${API_URL}/api/public/${encodeURIComponent(username)}`);
        if (!profileRes.ok) {
            const errorData = await profileRes.json().catch(() => ({}));
            throw new Error(errorData.detail || 'User not found');
        }
        bookingState.profile = await profileRes.json();
        
        // Get availability for next 14 days - NO AUTH HEADER
        const today = new Date();
        const endDate = new Date(today);
        endDate.setDate(endDate.getDate() + 14);
        
        const startStr = today.toISOString().split('T')[0];
        const endStr = endDate.toISOString().split('T')[0];
        
        const availRes = await fetch(`${API_URL}/api/public/${encodeURIComponent(username)}/availability?start_date=${startStr}&end_date=${endStr}`);
        const availData = await availRes.json();
        bookingState.availability = availData.availability || [];
        
        // Reset selection
        bookingState.selectedDate = null;
        bookingState.selectedSlot = null;
        
        app.innerHTML = renderBookingUI();
        
    } catch (err) {
        app.innerHTML = `
            <div class="auth-page">
                <div class="auth-card">
                    <div class="auth-logo">
                        <h1>📅 ScheduleLink</h1>
                    </div>
                    <div class="alert alert-error">User "${escapeHtml(username)}" not found</div>
                    <p style="text-align: center; color: var(--text-muted);">
                        The scheduling page you're looking for doesn't exist.
                    </p>
                    <a href="#/login" class="btn btn-primary" style="width: 100%; margin-top: 24px;">Go to Login</a>
                </div>
            </div>
        `;
    }
}

function renderBookingUI() {
    const { profile, availability, selectedDate, selectedSlot } = bookingState;
    const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    
    const datesWithSlots = new Set(
        availability.filter(d => d.slots.length > 0).map(d => d.date)
    );
    
    const dayAvail = selectedDate 
        ? availability.find(d => d.date === selectedDate)
        : null;
    const slots = dayAvail?.slots || [];
    
    setTimeout(() => {
        document.getElementById('booking-form')?.addEventListener('submit', handleBookingSubmit);
    }, 0);
    
    return `
        <div class="booking-page">
            <div class="booking-container">
                <div class="host-info">
                    <h1>Book a meeting with ${escapeHtml(profile.full_name || profile.username)}</h1>
                    <p>${profile.meeting_duration} minute meeting</p>
                </div>
                
                <div class="card">
                    <h3 class="card-title">Select a Date</h3>
                    <div class="calendar-grid">
                        ${days.map(d => `<div class="calendar-header">${d}</div>`).join('')}
                        ${renderCalendarDays(datesWithSlots)}
                    </div>
                </div>
                
                ${selectedDate ? `
                    <div class="card">
                        <h3 class="card-title">Select a Time — ${formatDateLong(selectedDate)}</h3>
                        ${slots.length === 0 
                            ? '<div class="empty-state"><p>No available times on this date</p></div>'
                            : `<div class="time-slots">
                                ${slots.map(s => {
                                    const time = new Date(s.start).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
                                    const isSelected = selectedSlot?.start === s.start;
                                    return `<div class="time-slot ${isSelected ? 'selected' : ''}" onclick="selectSlot('${s.start}', '${s.end}')">${time}</div>`;
                                }).join('')}
                              </div>`
                        }
                    </div>
                ` : ''}
                
                ${selectedSlot ? `
                    <div class="card">
                        <h3 class="card-title">Your Details</h3>
                        <form id="booking-form">
                            <div class="form-group">
                                <label class="form-label">Name *</label>
                                <input type="text" name="client_name" class="form-input" placeholder="Your name" required>
                            </div>
                            
                            <div class="form-group">
                                <label class="form-label">Email *</label>
                                <input type="email" name="client_email" class="form-input" placeholder="you@example.com" required>
                            </div>
                            
                            <div class="form-group">
                                <label class="form-label">Phone (optional)</label>
                                <input type="tel" name="client_phone" class="form-input" placeholder="+1 (555) 123-4567">
                            </div>
                            
                            <div class="form-group">
                                <label class="form-label">Notes (optional)</label>
                                <textarea name="notes" class="form-textarea" placeholder="Anything you'd like to discuss..."></textarea>
                            </div>
                            
                            <button type="submit" class="btn btn-primary btn-lg" style="width: 100%;">
                                Confirm Booking
                            </button>
                        </form>
                    </div>
                ` : ''}
            </div>
        </div>
    `;
}

function renderCalendarDays(datesWithSlots) {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    let html = '';
    const firstDayOffset = today.getDay();
    
    // Add empty cells for days before today
    for (let i = 0; i < firstDayOffset; i++) {
        html += '<div class="calendar-day disabled"></div>';
    }
    
    // Add 14 days starting from today
    for (let d = 0; d < 14; d++) {
        const date = new Date(today);
        date.setDate(today.getDate() + d);
        const dateStr = date.toISOString().split('T')[0];
        const dayNum = date.getDate();
        
        const hasSlots = datesWithSlots.has(dateStr);
        const isSelected = bookingState.selectedDate === dateStr;
        
        let className = 'calendar-day';
        if (isSelected) className += ' selected';
        else if (hasSlots) className += ' has-slots';
        if (!hasSlots) className += ' disabled';
        
        const onClick = hasSlots ? `onclick="selectDate('${dateStr}')"` : '';
        html += `<div class="${className}" ${onClick}>${dayNum}</div>`;
    }
    
    // Fill remaining cells in the last row
    const totalCells = firstDayOffset + 14;
    const remaining = (7 - (totalCells % 7)) % 7;
    for (let i = 0; i < remaining; i++) {
        html += '<div class="calendar-day disabled"></div>';
    }
    
    return html;
}

function selectDate(dateStr) {
    bookingState.selectedDate = dateStr;
    bookingState.selectedSlot = null;
    document.getElementById('app').innerHTML = renderBookingUI();
}

function selectSlot(start, end) {
    bookingState.selectedSlot = { start, end };
    document.getElementById('app').innerHTML = renderBookingUI();
}

async function handleBookingSubmit(e) {
    e.preventDefault();
    const form = e.target;
    const username = bookingState.profile.username;
    const btn = form.querySelector('button[type="submit"]');
    
    btn.disabled = true;
    btn.textContent = 'Booking...';
    
    try {
        // NO AUTH HEADER for public booking
        const response = await fetch(`${API_URL}/api/public/${encodeURIComponent(username)}/book`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                client_name: form.client_name.value,
                client_email: form.client_email.value,
                client_phone: form.client_phone.value || null,
                start_time: bookingState.selectedSlot.start,
                notes: form.notes.value || null
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Booking failed');
        }
        
        showBookingConfirmation(data);
        
    } catch (err) {
        alert(err.message);
        btn.disabled = false;
        btn.textContent = 'Confirm Booking';
    }
}

function showBookingConfirmation(booking) {
    const start = new Date(booking.start_time);
    const dateStr = start.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
    const timeStr = start.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
    
    document.getElementById('app').innerHTML = `
        <div class="booking-page">
            <div class="booking-container">
                <div class="confirmation">
                    <div class="confirmation-icon">✓</div>
                    <h1>Booking Confirmed!</h1>
                    <p>You're all set. A confirmation email has been sent to ${escapeHtml(booking.client_email)}.</p>
                    
                    <div class="confirmation-details">
                        <p><strong>Meeting with:</strong> ${escapeHtml(bookingState.profile.full_name || bookingState.profile.username)}</p>
                        <p><strong>Date:</strong> ${dateStr}</p>
                        <p><strong>Time:</strong> ${timeStr}</p>
                        <p><strong>Duration:</strong> ${bookingState.profile.meeting_duration} minutes</p>
                    </div>
                    
                    <a href="#/" class="btn btn-primary">Done</a>
                </div>
            </div>
        </div>
    `;
}

function formatDateLong(dateStr) {
    const date = new Date(dateStr + 'T12:00:00');
    return date.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
}

// ============== Cancel Page ==============
async function renderCancelPage(token) {
    const app = document.getElementById('app');
    app.innerHTML = '<div class="loading">Loading...</div>';
    
    try {
        // NO AUTH HEADER for public cancellation
        const response = await fetch(`${API_URL}/api/cancel/${encodeURIComponent(token)}`);
        if (!response.ok) throw new Error('Booking not found or already cancelled');
        
        const booking = await response.json();
        const start = new Date(booking.start_time);
        const dateStr = start.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
        const timeStr = start.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
        
        app.innerHTML = `
            <div class="auth-page">
                <div class="auth-card">
                    <div class="auth-logo">
                        <h1>📅 ScheduleLink</h1>
                        <p>Cancel your booking</p>
                    </div>
                    <div id="cancel-content">
                        <div class="confirmation-details" style="margin: 0 0 24px;">
                            <p><strong>Meeting with:</strong> ${escapeHtml(booking.host_name)}</p>
                            <p><strong>Date:</strong> ${dateStr}</p>
                            <p><strong>Time:</strong> ${timeStr}</p>
                        </div>
                        <p style="text-align: center; color: var(--text-muted); margin-bottom: 24px;">Are you sure you want to cancel?</p>
                        <button class="btn btn-danger btn-lg" style="width: 100%;" onclick="confirmCancel('${token}')">Cancel Meeting</button>
                        <a href="#/" class="btn btn-secondary" style="width: 100%; margin-top: 12px; display: block; text-align: center;">Keep Meeting</a>
                    </div>
                </div>
            </div>
        `;
    } catch (err) {
        app.innerHTML = `
            <div class="auth-page">
                <div class="auth-card">
                    <div class="auth-logo"><h1>📅 ScheduleLink</h1></div>
                    <div class="alert alert-error">${escapeHtml(err.message)}</div>
                    <a href="#/" class="btn btn-primary" style="width: 100%; margin-top: 16px;">Go Home</a>
                </div>
            </div>
        `;
    }
}

async function confirmCancel(token) {
    const content = document.getElementById('cancel-content');
    try {
        // NO AUTH HEADER for public cancellation
        const response = await fetch(`${API_URL}/api/cancel/${encodeURIComponent(token)}`, { method: 'POST' });
        if (!response.ok) throw new Error('Failed to cancel booking');
        content.innerHTML = `
            <div class="alert alert-success" style="margin-bottom: 24px;">✓ Meeting cancelled successfully</div>
            <p style="text-align: center; color: var(--text-muted);">Both you and the host have been notified.</p>
            <a href="#/" class="btn btn-primary" style="width: 100%; margin-top: 24px;">Done</a>
        `;
    } catch (err) {
        alert('Failed to cancel: ' + err.message);
    }
}

// ============== Initialize ==============
window.addEventListener('hashchange', router);
window.addEventListener('load', router);

// Expose functions to window for onclick handlers
window.logout = logout;
window.copyBookingLink = copyBookingLink;
window.cancelBooking = cancelBooking;
window.connectGoogle = connectGoogle;
window.disconnectGoogle = disconnectGoogle;
window.upgradeToPro = upgradeToPro;
window.upgradeToProPlus = upgradeToProPlus;
window.manageBilling = manageBilling;
window.selectDate = selectDate;
window.selectSlot = selectSlot;
window.confirmCancel = confirmCancel;