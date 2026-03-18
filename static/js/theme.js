/**
 * Theme Manager - Light/Dark Mode Toggle
 * SmartAttendance System
 */
(function() {
    'use strict';

    const STORAGE_KEY = 'smartattendance-theme';

    function getStoredTheme() {
        return localStorage.getItem(STORAGE_KEY);
    }

    function setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem(STORAGE_KEY, theme);
    }

    function toggleTheme() {
        const current = document.documentElement.getAttribute('data-theme') || 'light';
        const next = current === 'light' ? 'dark' : 'light';
        setTheme(next);
    }

    // Initialize theme
    function initTheme() {
        const stored = getStoredTheme();
        if (stored) {
            setTheme(stored);
        } else {
            // Check system preference
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            setTheme(prefersDark ? 'dark' : 'light');
        }
    }

    // Apply theme immediately (before DOM load to prevent flash)
    initTheme();

    // Bind toggle button after DOM loads
    document.addEventListener('DOMContentLoaded', function() {
        const toggleBtn = document.getElementById('theme-toggle');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', toggleTheme);
        }
    });

    // Listen for system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
        if (!getStoredTheme()) {
            setTheme(e.matches ? 'dark' : 'light');
        }
    });
})();
