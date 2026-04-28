/**
 * ScheduleLink - Single Page Application
 * Production-ready multi-tenant scheduling platform
 */

// ============== Configuration ==============
const API_BASE = 'https://schedulelink-app.onrender.com';
let stripePublishableKey = '';

// ============== State ==============
const state = {
    user: null,
    token: localStorage.getItem('schedulelink_token'),
    workingHours: [],
    bookings: [],
    subscriptionStatus: null
};

// ============== API Helpers ==============
async function api(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };
    
    if (state.token) {
        headers['Authorization'] = `Bearer ${state.token}`;
    }
    
    const response = await fetch(url, {
        ...options,
        headers
    });
    
    if (response.status === 401) {
        // Token expired or invalid
        if (!options.noLogout) {
            logout();
        }
        return null;
    }
    
    const data = await response.json();
    
    if (!response.ok) {
        let msg = 'An error occurred';
        if (data.detail) {
            if (typeof data.detail === 'string') {
                msg = data.detail;
            } else if (Array.isArray(data.detail)) {
                // Pydantic validation error array — extract human-readable messages
                msg = data.detail.map(e => {
                    if (typeof e === 'string') return e;
                    if (e.msg) return e.msg;
                    if (e.loc) return `Field '${e.loc[e.loc.length-1]}': ${e.msg || e.type}`;
                    return JSON.stringify(e);
                }).join('; ');
            } else if (typeof data.detail === 'object') {
                msg = JSON.stringify(data.detail);
            }
        }
        throw new Error(msg);
    }
    
    return data;
}

// ============== Auth Functions ==============
async function login(email, password) {
    const data = await api('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password })
    });
    
    if (data && data.access_token) {
        state.token = data.access_token;
        localStorage.setItem('schedulelink_token', data.access_token);
        // Load user in background - don't let failures block navigation
        await loadUserSafe();
        navigate('#/dashboard');
    } else {
        throw new Error('Login failed: No access token received');
    }
}

async function register(email, password, full_name, username) {
    const data = await api('/api/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, password, full_name, username })
    });
    
    if (data && data.access_token) {
        state.token = data.access_token;
        localStorage.setItem('schedulelink_token', data.access_token);
        // Load user in background - don't let failures block navigation
        await loadUserSafe();
        navigate('#/dashboard');
    } else {
        throw new Error('Registration failed: No access token received');
    }
}

function logout() {
    state.token = null;
    state.user = null;
    localStorage.removeItem('schedulelink_token');
    navigate('#/login');
}

async function loadUser() {
    if (!state.token) return;
    
    try {
        state.user = await api('/api/auth/me');
    } catch (e) {
        logout();
    }
}

// Safe version of loadUser that doesn't logout on failure
// Used during login/register when we know the token is valid
async function loadUserSafe() {
    if (!state.token) return;
    
    try {
        state.user = await api('/api/auth/me');
    } catch (e) {
        // Don't logout - the token might still be valid
        // User data will load on next navigation
        console.warn('Failed to load user data:', e.message);
    }
}

// ============== Navigation ==============
function navigate(hash) {
    window.location.hash = hash;
}

function getRoute() {
    const hash = window.location.hash || '#/';
    return hash.slice(1); // Remove #
}

function getQueryParams() {
    return new URLSearchParams(window.location.hash.split('?')[1] || '');
}

// ============== Rendering ==============
async function render() {
    const app = document.getElementById('app');
    const route = getRoute();
    const params = getQueryParams();
    
    // STRIPE RETURN HANDLING — run before auth check
    // If user just returned from Stripe, show the result even if auth is momentarily unavailable
    const billingStatus = params.get('billing');
    if (billingStatus === 'success' || billingStatus === 'cancelled') {
        // User just returned from Stripe — show the result even if auth is momentarily
        // unavailable. Use noLogout so a bad token doesn't force a redirect to login.
        if (state.token) {
            try {
                state.user = await api('/api/auth/me', { noLogout: true });
            } catch(e) {
                // Don't logout — just show what we can without user data
            }
        }
        // Render settings with the billing param (shows success/cancel banner)
        // Even if auth failed, show the settings page with the banner
        await renderSettings(app, params);
        return;
    }
    
    // Auth required routes
    const authRoutes = ['/dashboard', '/settings', '/bookings'];
    const isAuthRoute = authRoutes.some(r => route.startsWith(r));
    
    if (isAuthRoute && !state.token) {
        navigate('#/login');
        return;
    }
    
    // Route matching
    if (route === '/' || route === '') {
        app.innerHTML = renderLanding();
    } else if (route === '/login') {
        app.innerHTML = renderLogin();
    } else if (route === '/register') {
        app.innerHTML = renderRegister();
    } else if (route === '/forgot-password') {
        app.innerHTML = renderForgotPassword();
    } else if (route.startsWith('/reset-password')) {
        const token = new URLSearchParams(window.location.hash.split('?')[1] || '').get('token') || '';
        app.innerHTML = renderResetPassword(token);
    } else if (route === '/dashboard') {
        renderDashboard(app);
    } else if (route === '/settings') {
        await renderSettings(app, params);
    } else if (route === '/bookings') {
        renderBookings(app);
    } else {
        app.innerHTML = render404();
    }
}

// ============== Page Renderers ==============

function renderLanding() {
    return `
        <header class="header">
            <div class="container header-content">
                <a href="#/" class="logo"><span>Schedule</span>Link</a>
                <nav class="nav">
                    ${state.token ? `
                        <a href="#/dashboard" class="nav-link">Dashboard</a>
                        <a href="#" class="nav-link" onclick="logout(); return false;">Logout</a>
                    ` : `
                        <a href="#/login" class="nav-link">Login</a>
                        <a href="#/register" class="btn btn-primary btn-sm">Get Started</a>
                    `}
                </nav>
            </div>
        </header>
        <main class="main">
            <div class="container">
                <div style="text-align: center; padding: 4rem 0;">
                    <h1 style="font-size: 3rem; margin-bottom: 1.5rem;">
                        Schedule Meetings<br><span style="color: var(--accent)">Effortlessly</span>
                    </h1>
                    <p style="font-size: 1.25rem; color: var(--text-muted); max-width: 600px; margin: 0 auto 2rem;">
                        Create your personal booking page in minutes. Let clients schedule meetings with you automatically.
                    </p>
                    <a href="#/register" class="btn btn-primary btn-lg">Start Free Trial</a>
                    <p style="margin-top: 1rem; color: var(--text-dim);">Free tier includes 5 bookings/month • Upgrade from $5/mo</p>
                </div>
                
                <div class="stats" style="margin-top: 4rem;">
                    <div class="stat-card">
                        <div class="stat-value">📅</div>
                        <div class="stat-label" style="font-size: 1rem; margin-top: 1rem;">Easy Scheduling</div>
                        <p style="margin-top: 0.5rem;">Share your booking link. Clients pick a time. Done.</p>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">📧</div>
                        <div class="stat-label" style="font-size: 1rem; margin-top: 1rem;">Email Confirmations</div>
                        <p style="margin-top: 0.5rem;">Automatic emails to you and your clients.</p>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">📆</div>
                        <div class="stat-label" style="font-size: 1rem; margin-top: 1rem;">Google Calendar Sync</div>
                        <p style="margin-top: 0.5rem;">Events automatically added to your calendar.</p>
                    </div>
                </div>
            </div>
        </main>
    `;
}

function renderLogin() {
    return `
        <div class="auth-page">
            <div class="auth-card">
                <div class="auth-brand">
                    <a href="#/" class="auth-brand-logo">
                        <div class="auth-brand-icon">
                            <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
                                <rect x="3" y="4" width="18" height="18" rx="3" stroke="#e8956a" stroke-width="1.75"/>
                                <path d="M3 10h18" stroke="#e8956a" stroke-width="1.75"/>
                                <path d="M8 2v4M16 2v4" stroke="#e8956a" stroke-width="1.75" stroke-linecap="round"/>
                                <circle cx="8" cy="14.5" r="1.5" fill="#e8956a"/>
                                <circle cx="12" cy="14.5" r="1.5" fill="#e8956a"/>
                                <circle cx="16" cy="14.5" r="1.5" fill="#e8956a"/>
                            </svg>
                        </div>
                    </a>
                    <h1 class="auth-welcome">Welcome back</h1>
                    <p class="auth-tagline">Sign in to manage your bookings</p>
                </div>
                <div id="login-error" class="alert-error hidden">
                    <span style="font-size:1.1rem;">&#9888;</span>
                    <span id="login-error-text"></span>
                </div>
                <form id="login-form" onsubmit="handleLogin(event)">
                    <div class="form-group">
                        <label class="form-label">
                            <span class="label-icon">&#128231;</span> Email address
                        </label>
                        <input type="email" name="email" class="form-input" placeholder="you@example.com" required autofocus>
                    </div>
                    <div class="form-group">
                        <label class="form-label">
                            <span class="label-icon">&#128274;</span> Password
                        </label>
                        <input type="password" name="password" class="form-input" placeholder="Your password" required>
                    </div>
                    <button type="submit" class="btn-primary" id="login-btn">
                        <span>Sign In</span>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                            <path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </button>
                </form>
                <div class="auth-trust">
                    <div class="auth-trust-item">
                        <span class="trust-icon">&#128274;</span>
                        <span>Secure sign-in</span>
                    </div>
                    <div class="auth-trust-item">
                        <span class="trust-icon">&#128171;</span>
                        <span>Your data is safe</span>
                    </div>
                </div>
                <div class="auth-footer">
                    <a href="#/forgot-password">Forgot your password?</a>
                </div>
                <div class="auth-footer">
                    Don't have an account? <a href="#/register">Create one free</a>
                </div>
            </div>
        </div>
    `;
}

function renderRegister() {
    return `
        <div class="auth-page">
            <div class="auth-card">
                <div class="auth-brand">
                    <a href="#/" class="auth-brand-logo">
                        <div class="auth-brand-icon">
                            <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
                                <rect x="3" y="4" width="18" height="18" rx="3" stroke="#e8956a" stroke-width="1.75"/>
                                <path d="M3 10h18" stroke="#e8956a" stroke-width="1.75"/>
                                <path d="M8 2v4M16 2v4" stroke="#e8956a" stroke-width="1.75" stroke-linecap="round"/>
                                <circle cx="8" cy="14.5" r="1.5" fill="#e8956a"/>
                                <circle cx="12" cy="14.5" r="1.5" fill="#e8956a"/>
                                <circle cx="16" cy="14.5" r="1.5" fill="#e8956a"/>
                            </svg>
                        </div>
                    </a>
                    <h1 class="auth-welcome">Get started free</h1>
                    <p class="auth-tagline">Create your booking page in under 2 minutes</p>
                </div>
                <div class="auth-features">
                    <div class="auth-feature-item">
                        <span class="feature-check">&#10003;</span>
                        <span>Unlimited booking slots</span>
                    </div>
                    <div class="auth-feature-item">
                        <span class="feature-check">&#10003;</span>
                        <span>Automatic email confirmations</span>
                    </div>
                    <div class="auth-feature-item">
                        <span class="feature-check">&#10003;</span>
                        <span>Google Calendar sync</span>
                    </div>
                </div>
                <div id="register-error" class="alert-error hidden">
                    <span style="font-size:1.1rem;">&#9888;</span>
                    <span id="register-error-text"></span>
                </div>
                <form id="register-form" onsubmit="handleRegister(event)">
                    <div class="form-group">
                        <label class="form-label">
                            <span class="label-icon">&#128100;</span> Full Name
                        </label>
                        <input type="text" name="full_name" class="form-input" placeholder="Sarah Johnson" required autofocus>
                    </div>
                    <div class="form-group">
                        <label class="form-label">
                            <span class="label-icon">&#128231;</span> Email address
                        </label>
                        <input type="email" name="email" class="form-input" placeholder="sarah@example.com" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label">
                            <span class="label-icon">&#128187;</span> Username
                        </label>
                        <input type="text" name="username" class="form-input" pattern="[a-zA-Z0-9_-]+" required
                               placeholder="sarah-j">
                        <p class="form-help">Your booking page: <strong>schedulelink.tech/book/<span id="username-preview">sarah-j</span></strong></p>
                    </div>
                    <div class="form-group">
                        <label class="form-label">
                            <span class="label-icon">&#128274;</span> Password
                        </label>
                        <input type="password" name="password" class="form-input" minlength="8" placeholder="At least 8 characters" required>
                    </div>
                    <button type="submit" class="btn-primary" id="register-btn">
                        <span>Create Free Account</span>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                            <path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </button>
                </form>
                <div class="auth-trust">
                    <div class="auth-trust-item">
                        <span class="trust-icon">&#9989;</span>
                        <span>Free to start</span>
                    </div>
                    <div class="auth-trust-item">
                        <span class="trust-icon">&#128274;</span>
                        <span>No credit card needed</span>
                    </div>
                </div>
                <div class="auth-footer">
                    Already have an account? <a href="#/login">Sign in</a>
                </div>
            </div>
        </div>
    `;
}

function renderForgotPassword() {
    return `
        <div class="auth-page">
            <div class="auth-card">
                <div class="auth-brand">
                    <a href="#/" class="auth-brand-logo">
                        <div class="auth-brand-icon">
                            <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
                                <rect x="3" y="4" width="18" height="18" rx="3" stroke="#e8956a" stroke-width="1.75"/>
                                <path d="M3 10h18" stroke="#e8956a" stroke-width="1.75"/>
                                <path d="M8 2v4M16 2v4" stroke="#e8956a" stroke-width="1.75" stroke-linecap="round"/>
                                <circle cx="8" cy="14.5" r="1.5" fill="#e8956a"/>
                                <circle cx="12" cy="14.5" r="1.5" fill="#e8956a"/>
                                <circle cx="16" cy="14.5" r="1.5" fill="#e8956a"/>
                            </svg>
                        </div>
                    </a>
                    <h1 class="auth-welcome">Reset your password</h1>
                    <p class="auth-tagline">Enter your email and we'll send you a reset link</p>
                </div>
                <div id="forgot-success" class="alert-success hidden" style="margin-bottom: 1.5rem; text-align: center;">
                    <span id="forgot-success-text"></span>
                </div>
                <div id="forgot-error" class="alert-error hidden" style="margin-bottom: 1.5rem;">
                    <span id="forgot-error-text"></span>
                </div>
                <form id="forgot-form" onsubmit="handleForgotPassword(event)">
                    <div class="form-group">
                        <label class="form-label">
                            <span class="label-icon">&#128231;</span> Email address
                        </label>
                        <input type="email" name="email" class="form-input" placeholder="you@example.com" required autofocus>
                    </div>
                    <button type="submit" class="btn-primary" id="forgot-btn">
                        <span>Send Reset Link</span>
                    </button>
                </form>
                <div class="auth-footer">
                    Remember your password? <a href="#/login">Sign in</a>
                </div>
            </div>
        </div>
    `;
}

function renderResetPassword(token) {
    if (!token) {
        return `
            <div class="auth-page">
                <div class="auth-card">
                    <div class="auth-brand">
                        <a href="#/" class="auth-brand-logo">
                            <div class="auth-brand-icon">
                                <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
                                    <rect x="3" y="4" width="18" height="18" rx="3" stroke="#e8956a" stroke-width="1.75"/>
                                    <path d="M3 10h18" stroke="#e8956a" stroke-width="1.75"/>
                                    <path d="M8 2v4M16 2v4" stroke="#e8956a" stroke-width="1.75" stroke-linecap="round"/>
                                    <circle cx="8" cy="14.5" r="1.5" fill="#e8956a"/>
                                    <circle cx="12" cy="14.5" r="1.5" fill="#e8956a"/>
                                    <circle cx="16" cy="14.5" r="1.5" fill="#e8956a"/>
                                </svg>
                            </div>
                        </a>
                        <h1 class="auth-welcome">Invalid link</h1>
                        <p class="auth-tagline">This password reset link is invalid or has expired.</p>
                    </div>
                    <div class="auth-footer">
                        <a href="#/forgot-password">Request a new reset link</a>
                    </div>
                    <div class="auth-footer">
                        <a href="#/login">Back to sign in</a>
                    </div>
                </div>
            </div>
        `;
    }

    return `
        <div class="auth-page">
            <div class="auth-card">
                <div class="auth-brand">
                    <a href="#/" class="auth-brand-logo">
                        <div class="auth-brand-icon">
                            <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
                                <rect x="3" y="4" width="18" height="18" rx="3" stroke="#e8956a" stroke-width="1.75"/>
                                <path d="M3 10h18" stroke="#e8956a" stroke-width="1.75"/>
                                <path d="M8 2v4M16 2v4" stroke="#e8956a" stroke-width="1.75" stroke-linecap="round"/>
                                <circle cx="8" cy="14.5" r="1.5" fill="#e8956a"/>
                                <circle cx="12" cy="14.5" r="1.5" fill="#e8956a"/>
                                <circle cx="16" cy="14.5" r="1.5" fill="#e8956a"/>
                            </svg>
                        </div>
                    </a>
                    <h1 class="auth-welcome">Set a new password</h1>
                    <p class="auth-tagline">Enter your new password below</p>
                </div>
                <div id="reset-error" class="alert-error hidden" style="margin-bottom: 1.5rem;">
                    <span id="reset-error-text"></span>
                </div>
                <div id="reset-success" class="alert-success hidden" style="margin-bottom: 1.5rem; text-align: center;">
                    <span id="reset-success-text"></span>
                </div>
                <form id="reset-form" onsubmit="handleResetPassword(event, '${token}')">
                    <div class="form-group">
                        <label class="form-label">
                            <span class="label-icon">&#128274;</span> New Password
                        </label>
                        <input type="password" name="password" class="form-input" minlength="8"
                               placeholder="At least 8 characters" required autofocus>
                    </div>
                    <div class="form-group">
                        <label class="form-label">
                            <span class="label-icon">&#128274;</span> Confirm Password
                        </label>
                        <input type="password" name="password_confirm" class="form-input" minlength="8"
                               placeholder="Repeat your password" required>
                    </div>
                    <button type="submit" class="btn-primary" id="reset-btn">
                        <span>Reset Password</span>
                    </button>
                </form>
                <div class="auth-footer">
                    <a href="#/login">Back to sign in</a>
                </div>
            </div>
        </div>
    `;
}

async function handleForgotPassword(event) {
    event.preventDefault();
    const form = event.target;
    const btn = document.getElementById('forgot-btn');
    const errorDiv = document.getElementById('forgot-error');
    const successDiv = document.getElementById('forgot-success');

    btn.disabled = true;
    btn.querySelector('span').textContent = 'Sending...';
    errorDiv.classList.add('hidden');
    successDiv.classList.add('hidden');

    try {
        await api('/api/auth/forgot-password', {
            method: 'POST',
            body: JSON.stringify({ email: form.email.value })
        });

        // Always show success to avoid email enumeration
        document.getElementById('forgot-success-text').textContent =
            'Check your email — we\'ve sent you a reset link.';
        successDiv.classList.remove('hidden');
        form.classList.add('hidden');
    } catch (e) {
        document.getElementById('forgot-error-text').textContent = e.message;
        errorDiv.classList.remove('hidden');
        btn.disabled = false;
        btn.querySelector('span').textContent = 'Send Reset Link';
    }
}

async function handleResetPassword(event, token) {
    event.preventDefault();
    const form = event.target;
    const btn = document.getElementById('reset-btn');
    const errorDiv = document.getElementById('reset-error');
    const successDiv = document.getElementById('reset-success');

    const password = form.password.value;
    const passwordConfirm = form.password_confirm.value;

    if (password !== passwordConfirm) {
        document.getElementById('reset-error-text').textContent = 'Passwords do not match.';
        errorDiv.classList.remove('hidden');
        return;
    }

    btn.disabled = true;
    btn.querySelector('span').textContent = 'Resetting...';
    errorDiv.classList.add('hidden');

    try {
        await api('/api/auth/reset-password', {
            method: 'POST',
            body: JSON.stringify({ token, password })
        });

        document.getElementById('reset-success-text').textContent =
            'Your password has been reset! Redirecting to sign in...';
        successDiv.classList.remove('hidden');
        form.classList.add('hidden');

        setTimeout(() => navigate('#/login'), 2000);
    } catch (e) {
        document.getElementById('reset-error-text').textContent = e.message;
        errorDiv.classList.remove('hidden');
        btn.disabled = false;
        btn.querySelector('span').textContent = 'Reset Password';
    }
}

async function renderDashboard(app) {
    app.innerHTML = renderDashboardLayout(`
        <div class="loading">
            <div class="spinner"></div>
        </div>
    `);
    
    // Load data
    await Promise.all([
        loadUser(),
        loadBookings(),
        loadSubscriptionStatus()
    ]);
    
    const upcomingBookings = state.bookings
        .filter(b => b.status === 'confirmed' && new Date(b.booking_time) > new Date())
        .slice(0, 5);
    
    const content = `
        <h2 class="mb-3">Dashboard</h2>
        
        ${state.subscriptionStatus?.status === 'free' ? `
            <div class="subscription-banner">
                <h3>📊 Free Plan (${state.subscriptionStatus.bookings_this_month}/${state.subscriptionStatus.bookings_limit} bookings this month)</h3>
                <p>Upgrade to accept unlimited bookings and unlock premium features.</p>
                <div style="display: flex; gap: 1rem; flex-wrap: wrap;">
                    <button class="btn" onclick="handleUpgrade('pro')">Pro - $5/mo</button>
                    <button class="btn btn-primary" onclick="handleUpgrade('pro_plus')">Pro+ - $7/mo (with reminders)</button>
                </div>
            </div>
        ` : ''}
        
        <div class="stats mb-4">
            <div class="stat-card">
                <div class="stat-value">${upcomingBookings.length}</div>
                <div class="stat-label">Upcoming Bookings</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${state.bookings.filter(b => b.status === 'confirmed').length}</div>
                <div class="stat-label">Total Bookings</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${state.user?.meeting_duration || 30} min</div>
                <div class="stat-label">Meeting Duration</div>
            </div>
        </div>
        
        <div class="card mb-3">
            <div class="card-header">
                <h3 class="card-title">Your Booking Link</h3>
            </div>
            <div class="flex items-center gap-2">
                <input type="text" class="form-input" readonly value="${window.location.origin}/book/${state.user?.username}" id="booking-link">
                <button class="btn btn-secondary" onclick="copyBookingLink()">Copy</button>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">
                <h3 class="card-title">Upcoming Bookings</h3>
                <a href="#/bookings" class="btn btn-secondary btn-sm">View All</a>
            </div>
            
            ${upcomingBookings.length === 0 ? `
                <div class="empty-state">
                    <div class="empty-state-icon">📅</div>
                    <h4 class="empty-state-title">No upcoming bookings</h4>
                    <p class="empty-state-text">Share your booking link to start receiving appointments.</p>
                </div>
            ` : upcomingBookings.map(booking => `
                <div class="booking-item">
                    <div class="booking-item-info">
                        <h4>${booking.client_name}</h4>
                        <p class="booking-item-time">${formatDateTime(booking.booking_time, state.user?.timezone)}</p>
                        <p class="booking-item-client">${booking.client_email}</p>
                    </div>
                    <div class="booking-item-actions">
                        <span class="badge badge-success">Confirmed</span>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
    
    app.innerHTML = renderDashboardLayout(content);
}

async function renderSettings(app, params) {
    app.innerHTML = renderDashboardLayout(`
        <div class="loading">
            <div class="spinner"></div>
        </div>
    `);
    
    let alert = '';
    
    if (params.get('billing') === 'success') {
        alert = `<div class="alert alert-success fade-in" style="font-size: 1.05em; padding: 1.25rem; border: 1px solid #22c55e; animation: celebratePulse 2s ease-out;">
            🎉 <strong>Welcome to Pro!</strong> Your subscription is active. Enjoy unlimited bookings!
        </div>`;
        // Auto-refresh user state after a short delay to pick up is_paid: true
        setTimeout(async () => {
            try {
                state.user = await api('/api/auth/me');
                render(); // Re-render to update header badge and subscription card
            } catch(e) {
                // Silent fail — user still sees the success message
            }
        }, 2500);
    } else if (params.get('billing') === 'cancelled') {
        alert = '<div class="alert alert-info fade-in">Billing upgrade was cancelled. No charges were made.</div>';
    } else if (params.get('subscription') === 'success') {
        alert = '<div class="alert alert-success fade-in">🎉 Subscription activated successfully!</div>';
    } else if (params.get('google') === 'success') {
        alert = '<div class="alert alert-success fade-in">✅ Google Calendar connected successfully!</div>';
    } else if (params.get('google') === 'error') {
        alert = '<div class="alert alert-error fade-in">Failed to connect Google Calendar. Please try again.</div>';
    }
    
    await Promise.all([
        loadUser(),
        loadWorkingHours()
    ]);
    
    const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    
    const content = `
        <h2 class="mb-3">Settings</h2>
        
        ${alert}
        
        <div class="card mb-3">
            <h3 class="card-title mb-3">Profile</h3>
            
            <div id="profile-error" class="alert alert-error hidden"></div>
            <div id="profile-success" class="alert alert-success hidden"></div>
            
            <form id="profile-form" onsubmit="handleUpdateProfile(event)">
                <div class="grid grid-2">
                    <div class="form-group">
                        <label class="form-label">Full Name</label>
                        <input type="text" name="full_name" class="form-input" value="${state.user?.full_name || ''}" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Email</label>
                        <input type="email" class="form-input" value="${state.user?.email || ''}" disabled>
                    </div>
                </div>
                <div class="grid grid-2">
                    <div class="form-group">
                        <label class="form-label">Timezone</label>
                        <select name="timezone" class="form-select">
                            ${getTimezoneOptions(state.user?.timezone)}
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Meeting Duration (minutes)</label>
                        <select name="meeting_duration" class="form-select">
                            <option value="15" ${state.user?.meeting_duration === 15 ? 'selected' : ''}>15 minutes</option>
                            <option value="30" ${state.user?.meeting_duration === 30 ? 'selected' : ''}>30 minutes</option>
                            <option value="45" ${state.user?.meeting_duration === 45 ? 'selected' : ''}>45 minutes</option>
                            <option value="60" ${state.user?.meeting_duration === 60 ? 'selected' : ''}>60 minutes</option>
                            <option value="90" ${state.user?.meeting_duration === 90 ? 'selected' : ''}>90 minutes</option>
                        </select>
                    </div>
                </div>
                <div class="form-group">
                    <label class="form-label">Buffer Time Between Meetings (minutes)</label>
                    <select name="buffer_minutes" class="form-select" style="max-width: 200px;">
                        <option value="0" ${state.user?.buffer_minutes === 0 ? 'selected' : ''}>No buffer</option>
                        <option value="5" ${state.user?.buffer_minutes === 5 ? 'selected' : ''}>5 minutes</option>
                        <option value="10" ${state.user?.buffer_minutes === 10 ? 'selected' : ''}>10 minutes</option>
                        <option value="15" ${state.user?.buffer_minutes === 15 ? 'selected' : ''}>15 minutes</option>
                        <option value="30" ${state.user?.buffer_minutes === 30 ? 'selected' : ''}>30 minutes</option>
                    </select>
                </div>
                <button type="submit" class="btn btn-primary">Save Changes</button>
            </form>
        </div>
        
        <div class="card mb-3">
            <h3 class="card-title mb-3">Working Hours</h3>
            <p class="text-muted mb-3">Set your availability for each day of the week.</p>
            
            <form id="working-hours-form" onsubmit="handleUpdateWorkingHours(event)">
                ${state.workingHours.map((wh, i) => `
                    <div class="working-hours-day ${!wh.enabled ? 'disabled' : ''}">
                        <label class="toggle working-hours-toggle">
                            <input type="checkbox" name="day_${i}_enabled" ${wh.enabled ? 'checked' : ''} 
                                   onchange="toggleWorkingDay(${i}, this.checked)">
                            <span class="toggle-slider"></span>
                        </label>
                        <span class="working-hours-day-name">${days[i]}</span>
                        <div class="working-hours-times">
                            <input type="time" name="day_${i}_start" value="${wh.start_time}" ${!wh.enabled ? 'disabled' : ''}>
                            <span>to</span>
                            <input type="time" name="day_${i}_end" value="${wh.end_time}" ${!wh.enabled ? 'disabled' : ''}>
                        </div>
                    </div>
                `).join('')}
                <button type="submit" class="btn btn-primary mt-2">Save Working Hours</button>
            </form>
        </div>
        
        <div class="card mb-3">
            <h3 class="card-title mb-3">Integrations</h3>
            
            <div class="flex items-center justify-between" style="padding: 1rem; background: var(--bg-tertiary); border-radius: var(--radius-md);">
                <div class="flex items-center gap-2">
                    <span style="font-size: 1.5rem;">📆</span>
                    <div>
                        <strong>Google Calendar</strong>
                        <p class="text-muted" style="font-size: 0.875rem;">
                            ${state.user?.google_connected ? 'Connected' : 'Sync your bookings to Google Calendar'}
                        </p>
                    </div>
                </div>
                ${state.user?.google_connected ? `
                    <button class="btn btn-danger btn-sm" onclick="handleDisconnectGoogle()">Disconnect</button>
                ` : `
                    <button class="btn btn-primary btn-sm" onclick="handleConnectGoogle()">Connect</button>
                `}
            </div>
        </div>
        
        <div class="card">
            <h3 class="card-title mb-3">Subscription</h3>
            
            ${renderSubscriptionCard()}
        </div>
    `;
    
    app.innerHTML = renderDashboardLayout(content);
}

async function renderBookings(app) {
    app.innerHTML = renderDashboardLayout(`
        <div class="loading">
            <div class="spinner"></div>
        </div>
    `);
    
    await Promise.all([
        loadUser(),
        loadBookings()
    ]);
    
    const upcoming = state.bookings.filter(b => b.status === 'confirmed' && new Date(b.booking_time) > new Date());
    const past = state.bookings.filter(b => b.status === 'confirmed' && new Date(b.booking_time) <= new Date());
    const canceled = state.bookings.filter(b => b.status === 'canceled');
    
    const content = `
        <h2 class="mb-3">Bookings</h2>
        
        <div id="booking-alert"></div>
        
        <div class="card mb-3">
            <h3 class="card-title mb-3">Upcoming (${upcoming.length})</h3>
            
            ${upcoming.length === 0 ? `
                <div class="empty-state">
                    <p class="text-muted">No upcoming bookings</p>
                </div>
            ` : upcoming.map(booking => `
                <div class="booking-item">
                    <div class="booking-item-info">
                        <h4>${booking.client_name}</h4>
                        <p class="booking-item-time">${formatDateTime(booking.booking_time, state.user?.timezone)}</p>
                        <p class="booking-item-client">
                            📧 ${booking.client_email}
                            ${booking.client_phone ? `<br>📞 ${booking.client_phone}` : ''}
                            ${booking.client_notes ? `<br>📝 ${booking.client_notes}` : ''}
                        </p>
                    </div>
                    <div class="booking-item-actions">
                        <button class="btn btn-danger btn-sm" onclick="handleCancelBooking(${booking.id})">Cancel</button>
                    </div>
                </div>
            `).join('')}
        </div>
        
        <div class="card mb-3">
            <h3 class="card-title mb-3">Past (${past.length})</h3>
            
            ${past.length === 0 ? `
                <div class="empty-state">
                    <p class="text-muted">No past bookings</p>
                </div>
            ` : past.slice(0, 10).map(booking => `
                <div class="booking-item" style="opacity: 0.7;">
                    <div class="booking-item-info">
                        <h4>${booking.client_name}</h4>
                        <p class="booking-item-time">${formatDateTime(booking.booking_time, state.user?.timezone)}</p>
                        <p class="booking-item-client">${booking.client_email}</p>
                    </div>
                    <div class="booking-item-actions">
                        <span class="badge badge-info">Completed</span>
                    </div>
                </div>
            `).join('')}
        </div>
        
        ${canceled.length > 0 ? `
            <div class="card">
                <h3 class="card-title mb-3">Canceled (${canceled.length})</h3>
                ${canceled.slice(0, 5).map(booking => `
                    <div class="booking-item" style="opacity: 0.5;">
                        <div class="booking-item-info">
                            <h4>${booking.client_name}</h4>
                            <p class="booking-item-time">${formatDateTime(booking.booking_time, state.user?.timezone)}</p>
                        </div>
                        <div class="booking-item-actions">
                            <span class="badge badge-error">Canceled</span>
                        </div>
                    </div>
                `).join('')}
            </div>
        ` : ''}
    `;
    
    app.innerHTML = renderDashboardLayout(content);
}

function renderDashboardLayout(content) {
    return `
        <header class="header">
            <div class="container header-content">
                <a href="#/" class="logo"><span>Schedule</span>Link</a>
                <nav class="nav">
                    <span class="text-muted">Welcome, ${state.user?.full_name || 'User'}</span>
                    <a href="#" class="nav-link" onclick="logout(); return false;">Logout</a>
                </nav>
            </div>
        </header>
        <main class="main">
            <div class="container">
                <div class="dashboard">
                    <aside class="sidebar">
                        <nav class="sidebar-nav">
                            <a href="#/dashboard" class="sidebar-link ${getRoute() === '/dashboard' ? 'active' : ''}">
                                <span class="sidebar-link-icon">📊</span>
                                Dashboard
                            </a>
                            <a href="#/bookings" class="sidebar-link ${getRoute() === '/bookings' ? 'active' : ''}">
                                <span class="sidebar-link-icon">📅</span>
                                Bookings
                            </a>
                            <a href="#/settings" class="sidebar-link ${getRoute() === '/settings' ? 'active' : ''}">
                                <span class="sidebar-link-icon">⚙️</span>
                                Settings
                            </a>
                            <hr style="border: none; border-top: 1px solid var(--border); margin: 1rem 0;">
                            <a href="/book/${state.user?.username}" target="_blank" class="sidebar-link">
                                <span class="sidebar-link-icon">🔗</span>
                                View Booking Page
                            </a>
                        </nav>
                    </aside>
                    <div class="dashboard-content fade-in">
                        ${content}
                    </div>
                </div>
            </div>
        </main>
    `;
}

function render404() {
    return `
        <div class="auth-page">
            <div class="card text-center" style="padding: 3rem;">
                <h1 style="font-size: 4rem; margin-bottom: 1rem;">404</h1>
                <p class="text-muted mb-3">Page not found</p>
                <a href="#/" class="btn btn-primary">Go Home</a>
            </div>
        </div>
    `;
}

// ============== Data Loading ==============
async function loadBookings() {
    try {
        state.bookings = await api('/api/bookings');
    } catch (e) {
        state.bookings = [];
    }
}

async function loadWorkingHours() {
    try {
        const data = await api('/api/users/working-hours');
        state.workingHours = data.hours;
    } catch (e) {
        state.workingHours = [];
    }
}

async function loadSubscriptionStatus() {
    try {
        state.subscriptionStatus = await api('/api/stripe/status');
    } catch (e) {
        state.subscriptionStatus = null;
    }
}

// ============== Form Handlers ==============
async function handleLogin(event) {
    event.preventDefault();
    const form = event.target;
    const btn = form.querySelector('#login-btn');
    const errorDiv = document.getElementById('login-error');
    
    btn.disabled = true;
    btn.querySelector('span').textContent = 'Signing in...';
    errorDiv.classList.add('hidden');
    
    try {
        await login(form.email.value, form.password.value);
    } catch (e) {
        document.getElementById('login-error-text').textContent = e.message;
        errorDiv.classList.remove('hidden');
        btn.disabled = false;
        btn.querySelector('span').textContent = 'Sign In';
    }
}

async function handleRegister(event) {
    event.preventDefault();
    const form = event.target;
    const btn = form.querySelector('#register-btn');
    const errorDiv = document.getElementById('register-error');
    
    btn.disabled = true;
    btn.querySelector('span').textContent = 'Creating account...';
    errorDiv.classList.add('hidden');
    
    try {
        await register(
            form.email.value,
            form.password.value,
            form.full_name.value,
            form.username.value
        );
    } catch (e) {
        document.getElementById('register-error-text').textContent = e.message;
        errorDiv.classList.remove('hidden');
        btn.disabled = false;
        btn.querySelector('span').textContent = 'Create Free Account';
    }
}

async function handleUpdateProfile(event) {
    event.preventDefault();
    const form = event.target;
    const errorDiv = document.getElementById('profile-error');
    const successDiv = document.getElementById('profile-success');
    
    errorDiv.classList.add('hidden');
    successDiv.classList.add('hidden');
    
    try {
        await api('/api/users/me', {
            method: 'PUT',
            body: JSON.stringify({
                full_name: form.full_name.value,
                timezone: form.timezone.value,
                meeting_duration: parseInt(form.meeting_duration.value),
                buffer_minutes: parseInt(form.buffer_minutes.value)
            })
        });
        
        await loadUser();
        successDiv.textContent = 'Profile updated successfully!';
        successDiv.classList.remove('hidden');
    } catch (e) {
        errorDiv.textContent = e.message;
        errorDiv.classList.remove('hidden');
    }
}

async function handleUpdateWorkingHours(event) {
    event.preventDefault();
    const form = event.target;
    
    const hours = [];
    for (let i = 0; i < 7; i++) {
        hours.push({
            day_of_week: i,
            enabled: form[`day_${i}_enabled`].checked,
            start_time: form[`day_${i}_start`].value || '09:00',
            end_time: form[`day_${i}_end`].value || '17:00'
        });
    }
    
    try {
        await api('/api/users/working-hours', {
            method: 'PUT',
            body: JSON.stringify({ hours })
        });
        
        alert('Working hours saved!');
    } catch (e) {
        alert('Error: ' + e.message);
    }
}

function toggleWorkingDay(dayIndex, enabled) {
    const startInput = document.querySelector(`input[name="day_${dayIndex}_start"]`);
    const endInput = document.querySelector(`input[name="day_${dayIndex}_end"]`);
    const row = startInput.closest('.working-hours-day');
    
    startInput.disabled = !enabled;
    endInput.disabled = !enabled;
    
    if (enabled) {
        row.classList.remove('disabled');
    } else {
        row.classList.add('disabled');
    }
}

async function handleCancelBooking(bookingId) {
    if (!confirm('Are you sure you want to cancel this booking?')) {
        return;
    }
    
    try {
        await api(`/api/bookings/${bookingId}`, { method: 'DELETE' });
        
        document.getElementById('booking-alert').innerHTML = 
            '<div class="alert alert-success fade-in">Booking canceled successfully!</div>';
        
        await loadBookings();
        renderBookings(document.getElementById('app'));
    } catch (e) {
        document.getElementById('booking-alert').innerHTML = 
            `<div class="alert alert-error fade-in">${e.message}</div>`;
    }
}

function renderSubscriptionCard() {
    const status = state.user?.subscription_status || 'free';
    const isPro = status === 'active';
    const isProPlus = status === 'pro_plus';
    const isPaid = isPro || isProPlus;
    
    if (isPaid) {
        const planName = isProPlus ? 'ScheduleLink Pro+' : 'ScheduleLink Pro';
        const features = isProPlus 
            ? 'Unlimited bookings + Appointment reminders' 
            : 'Unlimited bookings';
        
        return `
            <div style="padding: 1rem; background: var(--bg-tertiary); border-radius: var(--radius-md);">
                <div class="flex items-center justify-between">
                    <div>
                        <strong>Current Plan: ${planName}</strong>
                        <p class="text-muted" style="font-size: 0.875rem;">${features}</p>
                    </div>
                    <button class="btn btn-secondary btn-sm" onclick="handleManageBilling()">Manage Billing</button>
                </div>
                ${isPro ? `
                    <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--border);">
                        <p class="text-muted" style="font-size: 0.875rem; margin-bottom: 0.5rem;">Want appointment reminders for your clients?</p>
                        <button class="btn btn-primary btn-sm" onclick="handleUpgrade('pro_plus')">Upgrade to Pro+ - $7/mo</button>
                    </div>
                ` : ''}
            </div>
        `;
    }
    
    // Free tier - show upgrade options
    return `
        <div style="padding: 1rem; background: var(--bg-tertiary); border-radius: var(--radius-md);">
            <div style="margin-bottom: 1rem;">
                <strong>Current Plan: Free</strong>
                <p class="text-muted" style="font-size: 0.875rem;">5 bookings per month</p>
            </div>
            
            <div style="display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));">
                <div style="padding: 1rem; background: var(--bg-secondary); border-radius: var(--radius-md); border: 1px solid var(--border);">
                    <h4 style="margin: 0 0 0.5rem 0;">Pro - $5/mo</h4>
                    <ul style="margin: 0 0 1rem 0; padding-left: 1.25rem; color: var(--text-muted); font-size: 0.875rem;">
                        <li>Unlimited bookings</li>
                        <li>All integrations</li>
                    </ul>
                    <button class="btn btn-secondary btn-sm btn-block" onclick="handleUpgrade('pro')">Upgrade to Pro</button>
                </div>
                
                <div style="padding: 1rem; background: linear-gradient(135deg, var(--bg-secondary), var(--accent-bg)); border-radius: var(--radius-md); border: 2px solid var(--accent);">
                    <h4 style="margin: 0 0 0.5rem 0;">Pro+ - $7/mo ✨</h4>
                    <ul style="margin: 0 0 1rem 0; padding-left: 1.25rem; color: var(--text-muted); font-size: 0.875rem;">
                        <li>Unlimited bookings</li>
                        <li>All integrations</li>
                        <li><strong style="color: var(--accent);">Appointment reminders</strong></li>
                    </ul>
                    <button class="btn btn-primary btn-sm btn-block" onclick="handleUpgrade('pro_plus')">Upgrade to Pro+</button>
                </div>
            </div>
        </div>
    `;
}

async function handleUpgrade(tier = 'pro') {
    try {
        // Flag that we're heading to Stripe — on return, don't force re-auth
        sessionStorage.setItem('pending_billing', 'upgrade');
        const data = await api('/api/stripe/checkout', { 
            method: 'POST',
            body: JSON.stringify({ tier })
        });
        window.location.href = data.checkout_url;
    } catch (e) {
        sessionStorage.removeItem('pending_billing');
        alert('Error: ' + e.message);
    }
}

async function handleManageBilling() {
    try {
        const data = await api('/api/stripe/portal', { method: 'POST' });
        window.location.href = data.portal_url;
    } catch (e) {
        alert('Error: ' + e.message);
    }
}

async function handleConnectGoogle() {
    try {
        const data = await api('/api/google/auth');
        window.location.href = data.auth_url;
    } catch (e) {
        alert('Error: ' + e.message);
    }
}

async function handleDisconnectGoogle() {
    if (!confirm('Are you sure you want to disconnect Google Calendar?')) {
        return;
    }
    
    try {
        await api('/api/google/disconnect', { method: 'POST' });
        await loadUser();
        renderSettings(document.getElementById('app'));
    } catch (e) {
        alert('Error: ' + e.message);
    }
}

function copyBookingLink() {
    const input = document.getElementById('booking-link');
    input.select();
    document.execCommand('copy');
    
    const btn = input.nextElementSibling;
    const originalText = btn.textContent;
    btn.textContent = 'Copied!';
    setTimeout(() => btn.textContent = originalText, 2000);
}

// ============== Utility Functions ==============
function formatDateTime(dateStr, timezone = 'America/New_York') {
    const date = new Date(dateStr + 'Z'); // Assume UTC from server
    return date.toLocaleString('en-US', {
        timeZone: timezone,
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
    });
}

function getTimezoneOptions(selected) {
    const timezones = [
        'America/New_York',
        'America/Chicago',
        'America/Denver',
        'America/Los_Angeles',
        'America/Phoenix',
        'America/Anchorage',
        'Pacific/Honolulu',
        'Europe/London',
        'Europe/Paris',
        'Europe/Berlin',
        'Asia/Tokyo',
        'Asia/Shanghai',
        'Asia/Dubai',
        'Australia/Sydney'
    ];
    
    return timezones.map(tz => 
        `<option value="${tz}" ${tz === selected ? 'selected' : ''}>${tz.replace('_', ' ')}</option>`
    ).join('');
}

// ============== Initialization ==============
async function init() {
    // Load config
    try {
        const config = await api('/api/config');
        stripePublishableKey = config.stripe_publishable_key;
    } catch (e) {
        console.error('Failed to load config:', e);
    }
    
    // Load user if token exists
    if (state.token) {
        await loadUser();
    }
    
    // Initial render
    render();
    
    // Handle navigation
    window.addEventListener('hashchange', render);
}

// Start the app
init();