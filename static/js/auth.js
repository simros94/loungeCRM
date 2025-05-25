/**
 * Checks user authentication status.
 * Redirects to login if not authenticated and not on the login page.
 * Redirects to dashboard if authenticated and on the login page.
 * @param {string} currentPage - A string identifying the current page, e.g., 'dashboard.html'.
 */
async function checkAuthentication(currentPage = '') {
    try {
        const response = await fetch('/auth/status');
        if (!response.ok) { // Not authenticated or other error
            if (currentPage !== 'login.html') {
                window.location.href = 'login.html';
            }
            return;
        }
        const data = await response.json();
        if (data.user) { // User is authenticated
            if (currentPage === 'login.html') {
                window.location.href = 'dashboard.html';
            }
        } else { // No user data, effectively not authenticated
            if (currentPage !== 'login.html') {
                window.location.href = 'login.html';
            }
        }
    } catch (error) {
        console.error('Error checking authentication status:', error);
        // If auth status check fails, and we are not on login page, redirect to login as a fallback.
        if (currentPage !== 'login.html') {
            // window.location.href = 'login.html';
            // Potentially show a less disruptive error, or allow page to load if it can function offline.
            // For this project, redirecting is simpler.
            console.warn('Connectivity issue? Redirecting to login.');
           // window.location.href = 'login.html'; // Commented out to prevent loop if /auth/status is itself broken
        }
    }
}

/**
 * Sets up a logout button.
 * Assumes a button with id="logoutButton" exists on the page.
 */
function setupLogoutButton() {
    const logoutButton = document.getElementById('logoutButton');
    if (logoutButton) {
        logoutButton.addEventListener('click', async (event) => {
            event.preventDefault();
            try {
                const response = await fetch('/auth/logout', { method: 'POST' });
                if (response.ok) {
                    localStorage.removeItem('loungeUser'); // Clear any stored user info
                    window.location.href = 'login.html';
                } else {
                    const data = await response.json();
                    alert(data.message || 'Logout failed. Please try again.');
                }
            } catch (error) {
                console.error('Logout error:', error);
                alert('An error occurred during logout.');
            }
        });
    }
}

// Example: Call checkAuthentication on page load for pages that need it.
// For instance, in dashboard.html, you'd include this script and then call:
// document.addEventListener('DOMContentLoaded', () => {
//     checkAuthentication('dashboard.html');
//     setupLogoutButton();
//     // ... other dashboard specific JS
// });

// In login.html, you might only call checkAuthentication to redirect if already logged in:
// document.addEventListener('DOMContentLoaded', () => {
//     checkAuthentication('login.html'); 
//     // No logout button on login page typically
// });
