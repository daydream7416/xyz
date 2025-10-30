// API Configuration
window.API_CONFIG = {
    getAgentRegistrationUrl: function() {
        // Use environment-based API URL
        const isLocalhost = window.location.hostname === 'localhost' || 
                           window.location.hostname === '127.0.0.1' ||
                           window.location.hostname === '';

        if (isLocalhost) {
            return 'http://localhost:8000/api/agent/register';
        } else {
            // Use Railway backend URL for production
            const runtimeOverride = window.__METRA_API_BASE_URL || window.localStorage?.getItem('METRA_API_BASE_URL');
            const baseUrl = runtimeOverride || 'https://capable-beauty.up.railway.app';
            return `${baseUrl.replace(/\/$/, '')}/api/agent/register`;
        }
    }
};

// Meta Pixel Configuration
window.META_PIXEL_ID = 'YOUR_PIXEL_ID_HERE'; // Replace with your actual Meta Pixel ID

// Initialize Meta Pixel with actual ID
if (typeof fbq !== 'undefined' && window.META_PIXEL_ID && window.META_PIXEL_ID !== 'YOUR_PIXEL_ID_HERE') {
    fbq('init', window.META_PIXEL_ID);
} else {
    console.warn('Meta Pixel ID not configured. Please set your actual Pixel ID in config.js');
}
