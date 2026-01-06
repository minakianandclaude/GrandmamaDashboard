/**
 * Good Morning Dashboard - Frontend JavaScript
 *
 * Handles:
 * - Fetching briefing data from API
 * - Updating DOM with new data
 * - Auto-refresh functionality
 * - Theme management
 * - Weather icon mapping
 */

(function() {
    'use strict';

    // ============================================
    // Configuration
    // ============================================

    const CONFIG = {
        apiEndpoint: '/api/briefing',
        configEndpoint: '/api/config',
        refreshInterval: 60000, // Will be overridden by server config
        retryDelay: 5000,
        maxRetries: 3
    };

    // ============================================
    // Weather Icon Mapping
    // ============================================

    const WEATHER_ICONS = {
        // Clear conditions
        'clear': '☀️',
        'sunny': '☀️',

        // Cloudy conditions
        'partly cloudy': '⛅',
        'mostly cloudy': '🌥️',
        'cloudy': '☁️',
        'overcast': '☁️',

        // Rain
        'rain': '🌧️',
        'rainy': '🌧️',
        'light rain': '🌦️',
        'drizzle': '🌦️',
        'showers': '🌧️',

        // Storms
        'thunderstorm': '⛈️',
        'stormy': '⛈️',

        // Snow
        'snow': '🌨️',
        'snowy': '🌨️',
        'light snow': '🌨️',
        'flurries': '❄️',

        // Fog/Haze
        'fog': '🌫️',
        'foggy': '🌫️',
        'mist': '🌫️',
        'haze': '🌫️',
        'hazy': '🌫️',

        // Default
        'default': '🌤️'
    };

    /**
     * Get weather icon for given condition
     */
    function getWeatherIcon(condition) {
        if (!condition) return WEATHER_ICONS.default;

        const normalized = condition.toLowerCase().trim();

        // Check for exact match first
        if (WEATHER_ICONS[normalized]) {
            return WEATHER_ICONS[normalized];
        }

        // Check for partial matches
        for (const [key, icon] of Object.entries(WEATHER_ICONS)) {
            if (normalized.includes(key) || key.includes(normalized)) {
                return icon;
            }
        }

        return WEATHER_ICONS.default;
    }

    // ============================================
    // Time Formatting
    // ============================================

    /**
     * Extract just the time portion from time_of_day string
     * e.g., "7:15 in the morning" -> "7:15 AM"
     */
    function formatTimeDisplay(timeOfDay) {
        if (!timeOfDay) return '';

        // Extract time from strings like "7:15 in the morning"
        const match = timeOfDay.match(/^(\d{1,2}:\d{2})/);
        if (!match) return timeOfDay;

        const time = match[1];

        // Determine AM/PM based on time period description
        if (timeOfDay.includes('afternoon') || timeOfDay.includes('evening')) {
            return time + ' PM';
        } else if (timeOfDay.includes('morning') || timeOfDay.includes('night')) {
            return time + ' AM';
        }

        return time;
    }

    /**
     * Get time period description
     */
    function getTimePeriod(timeOfDay) {
        if (!timeOfDay) return '';

        if (timeOfDay.includes('morning')) return 'Good morning';
        if (timeOfDay.includes('afternoon')) return 'Good afternoon';
        if (timeOfDay.includes('evening')) return 'Good evening';
        if (timeOfDay.includes('night')) return 'Good night';

        return 'Hello';
    }

    // ============================================
    // DOM Updates
    // ============================================

    /**
     * Update the dashboard with new briefing data
     */
    function updateDashboard(briefing) {
        // Update greeting
        const greetingName = document.querySelector('.greeting-name');
        const greetingText = document.querySelector('.greeting');
        if (greetingName && briefing.recipient_name) {
            greetingName.textContent = briefing.recipient_name;
        }

        // Update greeting based on time of day
        if (greetingText && briefing.date) {
            const period = getTimePeriod(briefing.date.time_of_day);
            greetingText.innerHTML = `${period}, <span class="greeting-name">${briefing.recipient_name}</span>.`;
        }

        // Update date/time
        updateDateTime(briefing.date);

        // Update weather
        updateWeather(briefing.weather);

        // Update appointments
        updateAppointments(briefing.appointments);

        // Show any errors
        updateErrors(briefing.errors);

        // Add fade animation
        document.querySelector('.dashboard').classList.add('fade-update');
        setTimeout(() => {
            document.querySelector('.dashboard').classList.remove('fade-update');
        }, 600);
    }

    /**
     * Update date/time section
     */
    function updateDateTime(dateInfo) {
        if (!dateInfo) return;

        const timeDisplay = document.querySelector('.time-display');
        const dayOfWeek = document.querySelector('.day-of-week');
        const fullDate = document.querySelector('.full-date');

        if (timeDisplay) {
            timeDisplay.textContent = formatTimeDisplay(dateInfo.time_of_day);
        }

        if (dayOfWeek) {
            dayOfWeek.textContent = dateInfo.day_of_week;
        }

        if (fullDate) {
            fullDate.textContent = dateInfo.full_date;
        }
    }

    /**
     * Update weather section
     */
    function updateWeather(weather) {
        const weatherCard = document.querySelector('.weather-card');
        if (!weatherCard) return;

        if (!weather) {
            weatherCard.innerHTML = `
                <div class="card-title">Weather</div>
                <div class="weather-unavailable">Weather information unavailable</div>
            `;
            return;
        }

        const icon = getWeatherIcon(weather.conditions);

        // Build high/low display if available
        const highLowHtml = (weather.high_f !== undefined && weather.low_f !== undefined)
            ? `<div class="weather-highlow">
                   <span class="high">H: ${weather.high_f}°</span>
                   <span class="low">L: ${weather.low_f}°</span>
               </div>`
            : '';

        // Build forecast days HTML
        let forecastHtml = '';
        if (weather.forecast && weather.forecast.length > 0) {
            forecastHtml = weather.forecast.map(day => {
                const dayIcon = getWeatherIcon(day.conditions);
                return `
                    <div class="forecast-day">
                        <span class="forecast-day-name">${day.day_name}</span>
                        <span class="forecast-icon">${dayIcon}</span>
                        <span class="forecast-temps">
                            <span class="high">${day.high_f}°</span>
                            <span class="low">${day.low_f}°</span>
                        </span>
                    </div>
                `;
            }).join('');
        }

        weatherCard.innerHTML = `
            <div class="card-title">Weather</div>
            <div class="weather-content">
                <div class="weather-today">
                    <div class="weather-icon">${icon}</div>
                    <div class="temperature">
                        ${weather.temperature_f}<span class="temperature-unit">°F</span>
                    </div>
                    <div class="weather-conditions">${weather.conditions}</div>
                    ${highLowHtml}
                </div>
                <div class="weather-forecast">
                    ${forecastHtml}
                </div>
            </div>
        `;
    }

    /**
     * Update appointments section
     */
    function updateAppointments(appointments) {
        const appointmentsList = document.querySelector('.appointments-list');
        if (!appointmentsList) return;

        if (!appointments || appointments.length === 0) {
            appointmentsList.innerHTML = `
                <li class="no-appointments">
                    No appointments scheduled for today. Enjoy your day!
                </li>
            `;
            return;
        }

        appointmentsList.innerHTML = appointments.map(apt => `
            <li class="appointment">
                <div class="appointment-time">${apt.time}</div>
                <div class="appointment-details">
                    <div class="appointment-title">${apt.title}</div>
                    ${apt.description ? `<div class="appointment-description">${apt.description}</div>` : ''}
                    ${apt.prep_reminder ? `<div class="appointment-prep">${apt.prep_reminder}</div>` : ''}
                </div>
            </li>
        `).join('');
    }

    /**
     * Update error display
     */
    function updateErrors(errors) {
        const existingBanner = document.querySelector('.error-banner');

        if (!errors || errors.length === 0) {
            if (existingBanner) {
                existingBanner.remove();
            }
            return;
        }

        const dashboard = document.querySelector('.dashboard');
        if (!dashboard) return;

        if (existingBanner) {
            existingBanner.innerHTML = `Some information may be unavailable: ${errors.join(', ')}`;
        } else {
            const banner = document.createElement('div');
            banner.className = 'error-banner';
            banner.textContent = `Some information may be unavailable: ${errors.join(', ')}`;
            dashboard.insertBefore(banner, dashboard.firstChild);
        }
    }

    /**
     * Update status indicator
     */
    function updateStatus(isError = false) {
        const statusDot = document.querySelector('.status-dot');
        const lastUpdate = document.querySelector('.last-update');

        if (statusDot) {
            statusDot.classList.toggle('error', isError);
        }

        if (lastUpdate) {
            const now = new Date();
            lastUpdate.textContent = `Last updated: ${now.toLocaleTimeString()}`;
        }
    }

    // ============================================
    // API Communication
    // ============================================

    let retryCount = 0;

    /**
     * Fetch briefing data from API
     */
    async function fetchBriefing() {
        try {
            const response = await fetch(CONFIG.apiEndpoint);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            retryCount = 0; // Reset on success
            updateStatus(false);
            return data;

        } catch (error) {
            console.error('Failed to fetch briefing:', error);
            updateStatus(true);

            if (retryCount < CONFIG.maxRetries) {
                retryCount++;
                console.log(`Retrying in ${CONFIG.retryDelay}ms (attempt ${retryCount}/${CONFIG.maxRetries})`);
                setTimeout(refreshDashboard, CONFIG.retryDelay);
            }

            return null;
        }
    }

    /**
     * Fetch configuration from API
     */
    async function fetchConfig() {
        try {
            const response = await fetch(CONFIG.configEndpoint);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            return await response.json();

        } catch (error) {
            console.error('Failed to fetch config:', error);
            return null;
        }
    }

    // ============================================
    // Theme Management
    // ============================================

    /**
     * Apply theme to document
     */
    function applyTheme(theme) {
        const validThemes = ['calm', 'bright', 'high_contrast'];

        if (!validThemes.includes(theme)) {
            theme = 'calm';
        }

        document.documentElement.setAttribute('data-theme', theme);
        console.log(`Theme applied: ${theme}`);
    }

    // ============================================
    // Refresh Logic
    // ============================================

    let refreshTimer = null;

    /**
     * Hide loading spinner and show dashboard
     */
    function showDashboard() {
        const loading = document.getElementById('loading');
        const dashboard = document.getElementById('dashboard');

        if (loading) {
            loading.style.display = 'none';
        }
        if (dashboard) {
            dashboard.style.display = 'grid';
        }
    }

    /**
     * Refresh dashboard data
     */
    async function refreshDashboard() {
        const briefing = await fetchBriefing();

        if (briefing) {
            updateDashboard(briefing);
            showDashboard();
        }
    }

    /**
     * Start auto-refresh timer
     */
    function startAutoRefresh(interval) {
        if (refreshTimer) {
            clearInterval(refreshTimer);
        }

        CONFIG.refreshInterval = interval * 1000; // Convert to ms
        refreshTimer = setInterval(refreshDashboard, CONFIG.refreshInterval);

        console.log(`Auto-refresh started: every ${interval} seconds`);
    }

    // ============================================
    // Initialization
    // ============================================

    /**
     * Initialize the dashboard
     */
    async function init() {
        console.log('Good Morning Dashboard initializing...');

        // Fetch config first
        const config = await fetchConfig();

        if (config) {
            // Apply theme
            applyTheme(config.theme);

            // Set refresh interval
            startAutoRefresh(config.refresh_interval_seconds);
        } else {
            // Use defaults
            applyTheme('calm');
            startAutoRefresh(60);
        }

        // Initial data load
        await refreshDashboard();

        console.log('Dashboard initialized');
    }

    // Start when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Expose for debugging
    window.Dashboard = {
        refresh: refreshDashboard,
        applyTheme: applyTheme,
        getWeatherIcon: getWeatherIcon
    };

})();
