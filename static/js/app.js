/**
 * Main Application JavaScript
 * SmartAttendance System
 */

// ============================================
// Toast Notification System
// ============================================
function showToast(type, title, message, duration = 5000) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const icons = {
        success: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
        error: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
        warning: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
        info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
    };

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-icon">${icons[type] || icons.info}</div>
        <div class="toast-content">
            <div class="toast-title">${title}</div>
            <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close" onclick="dismissToast(this)">&times;</button>
    `;

    container.appendChild(toast);

    // Auto-dismiss
    setTimeout(() => {
        dismissToast(toast.querySelector('.toast-close'));
    }, duration);
}

function dismissToast(closeBtn) {
    const toast = closeBtn.closest('.toast');
    if (!toast) return;
    
    toast.classList.add('toast-fade-out');
    setTimeout(() => toast.remove(), 300);
}

// ============================================
// Loading Overlay
// ============================================
function showLoading(text = 'Processing...') {
    const overlay = document.getElementById('loading-overlay');
    const loadingText = document.getElementById('loading-text');
    if (overlay) {
        overlay.classList.remove('hidden');
        if (loadingText) loadingText.textContent = text;
    }
}

function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.add('hidden');
    }
}

// ============================================
// Sidebar Toggle (Mobile)
// ============================================
document.addEventListener('DOMContentLoaded', function() {
    const menuToggle = document.getElementById('menu-toggle');
    const sidebar = document.getElementById('sidebar');
    const sidebarClose = document.getElementById('sidebar-close');

    if (menuToggle && sidebar) {
        menuToggle.addEventListener('click', function() {
            sidebar.classList.toggle('open');
        });
    }

    if (sidebarClose && sidebar) {
        sidebarClose.addEventListener('click', function() {
            sidebar.classList.remove('open');
        });
    }

    // Close sidebar when clicking outside
    document.addEventListener('click', function(e) {
        if (sidebar && sidebar.classList.contains('open')) {
            if (!sidebar.contains(e.target) && !menuToggle.contains(e.target)) {
                sidebar.classList.remove('open');
            }
        }
    });

    // Auto-dismiss flash alerts after 5 seconds
    document.querySelectorAll('.alert').forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-10px)';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });
});

// ============================================
// Utility Functions
// ============================================
function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function formatTime(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Debounce utility
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
