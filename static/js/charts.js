/**
 * Chart.js Configuration & Rendering
 * SmartAttendance System
 */

// Global Chart.js defaults
if (typeof Chart !== 'undefined') {
    Chart.defaults.font.family = "'Poppins', -apple-system, BlinkMacSystemFont, sans-serif";
    Chart.defaults.font.size = 12;
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
    Chart.defaults.plugins.legend.labels.padding = 20;
}

// Store chart instances for cleanup
const chartInstances = {};

/**
 * Get theme-aware colors
 */
function getChartColors() {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    return {
        primary: isDark ? '#818cf8' : '#4f46e5',
        primaryLight: isDark ? 'rgba(129, 140, 248, 0.15)' : 'rgba(79, 70, 229, 0.1)',
        accent: isDark ? '#2dd4bf' : '#0d9488',
        accentLight: isDark ? 'rgba(45, 212, 191, 0.15)' : 'rgba(13, 148, 136, 0.1)',
        success: isDark ? '#34d399' : '#10b981',
        error: isDark ? '#f87171' : '#ef4444',
        warning: isDark ? '#fbbf24' : '#f59e0b',
        text: isDark ? '#94a3b8' : '#64748b',
        grid: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
        background: isDark ? '#1e293b' : '#ffffff'
    };
}

/**
 * Render attendance trend chart (line chart)
 */
function renderTrendChart(canvasId, trendData) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    // Destroy existing chart
    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
    }

    const colors = getChartColors();
    const labels = trendData.map(d => d.date);
    const attendanceCounts = trendData.map(d => d.attendance_count);
    const sessionCounts = trendData.map(d => d.sessions);

    chartInstances[canvasId] = new Chart(canvas, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Attendance',
                    data: attendanceCounts,
                    borderColor: colors.primary,
                    backgroundColor: colors.primaryLight,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointBackgroundColor: colors.primary,
                    borderWidth: 2.5,
                },
                {
                    label: 'Sessions',
                    data: sessionCounts,
                    borderColor: colors.accent,
                    backgroundColor: colors.accentLight,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointBackgroundColor: colors.accent,
                    borderWidth: 2.5,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: colors.text,
                    }
                },
                tooltip: {
                    backgroundColor: colors.background,
                    titleColor: colors.text,
                    bodyColor: colors.text,
                    borderColor: colors.grid,
                    borderWidth: 1,
                    padding: 12,
                    cornerRadius: 8,
                }
            },
            scales: {
                x: {
                    grid: { color: colors.grid },
                    ticks: { color: colors.text }
                },
                y: {
                    beginAtZero: true,
                    grid: { color: colors.grid },
                    ticks: {
                        color: colors.text,
                        stepSize: 1,
                        precision: 0
                    }
                }
            }
        }
    });
}

/**
 * Render branch distribution chart (bar/doughnut)
 */
function renderBranchChart(canvasId, branchStats) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
    }

    const colors = getChartColors();
    const chartColors = [
        colors.primary, colors.accent, colors.success,
        colors.warning, colors.error, '#8b5cf6', '#ec4899'
    ];

    const labels = branchStats.map(b => b.branch);
    const studentData = branchStats.map(b => b.total_students);
    const attendanceData = branchStats.map(b => b.total_attendance);

    chartInstances[canvasId] = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Students',
                    data: studentData,
                    backgroundColor: chartColors.map(c => c + '33'),
                    borderColor: chartColors,
                    borderWidth: 2,
                    borderRadius: 6,
                },
                {
                    label: 'Attendance',
                    data: attendanceData,
                    backgroundColor: chartColors.map((c, i) => chartColors[(i + 2) % chartColors.length] + '33'),
                    borderColor: chartColors.map((c, i) => chartColors[(i + 2) % chartColors.length]),
                    borderWidth: 2,
                    borderRadius: 6,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: { color: colors.text }
                },
                tooltip: {
                    backgroundColor: colors.background,
                    titleColor: colors.text,
                    bodyColor: colors.text,
                    borderColor: colors.grid,
                    borderWidth: 1,
                    padding: 12,
                    cornerRadius: 8,
                }
            },
            scales: {
                x: {
                    grid: { color: colors.grid },
                    ticks: { color: colors.text }
                },
                y: {
                    beginAtZero: true,
                    grid: { color: colors.grid },
                    ticks: {
                        color: colors.text,
                        stepSize: 1,
                        precision: 0
                    }
                }
            }
        }
    });
}

/**
 * Render bar chart: attendance per day (last 7 days)
 */
function renderBarChart(canvasId, barData) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
    }

    const colors = getChartColors();
    const labels = barData.map(d => d.date);
    const presentData = barData.map(d => d.present);
    const lateData = barData.map(d => d.late);

    chartInstances[canvasId] = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Present',
                    data: presentData,
                    backgroundColor: colors.success + 'cc',
                    borderColor: colors.success,
                    borderWidth: 1,
                    borderRadius: 4,
                },
                {
                    label: 'Late',
                    data: lateData,
                    backgroundColor: colors.warning + 'cc',
                    borderColor: colors.warning,
                    borderWidth: 1,
                    borderRadius: 4,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: { color: colors.text }
                },
                tooltip: {
                    backgroundColor: colors.background,
                    titleColor: colors.text,
                    bodyColor: colors.text,
                    borderColor: colors.grid,
                    borderWidth: 1,
                    padding: 12,
                    cornerRadius: 8,
                }
            },
            scales: {
                x: {
                    grid: { color: colors.grid },
                    ticks: { color: colors.text }
                },
                y: {
                    beginAtZero: true,
                    grid: { color: colors.grid },
                    ticks: {
                        color: colors.text,
                        stepSize: 1,
                        precision: 0
                    }
                }
            }
        }
    });
}

/**
 * Render pie chart: Present vs Late vs Absent (today)
 */
function renderPieChart(canvasId, pieData) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
    }

    const colors = getChartColors();
    const labels = ['Present', 'Late', 'Absent'];
    const values = [
        pieData.present ?? 0,
        pieData.late ?? 0,
        pieData.absent ?? 0
    ];
    const backgroundColors = [colors.success, colors.warning, colors.error];

    chartInstances[canvasId] = new Chart(canvas, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: backgroundColors,
                borderColor: colors.background,
                borderWidth: 2,
                hoverOffset: 6,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: { color: colors.text, padding: 16 }
                },
                tooltip: {
                    backgroundColor: colors.background,
                    titleColor: colors.text,
                    bodyColor: colors.text,
                    borderColor: colors.grid,
                    borderWidth: 1,
                    padding: 12,
                    cornerRadius: 8,
                    callbacks: {
                        label: function(ctx) {
                            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                            const pct = total ? Math.round((ctx.raw / total) * 100) : 0;
                            return ctx.label + ': ' + ctx.raw + ' (' + pct + '%)';
                        }
                    }
                }
            }
        }
    });
}

// Re-render charts on theme change
const observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
        if (mutation.attributeName === 'data-theme') {
            // Re-render all charts with new colors
            Object.keys(chartInstances).forEach(id => {
                const chart = chartInstances[id];
                if (chart) {
                    // Trigger redraw - charts pick up new colors on next render call
                    chart.update();
                }
            });
        }
    });
});

observer.observe(document.documentElement, { attributes: true });
