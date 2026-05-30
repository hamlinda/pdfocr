// Application state
let currentTab = 'dashboard';
let pollInterval = null;
let heartbeatInterval = null;
let isScanning = false;

// DOM Elements
const navItems = document.querySelectorAll('.nav-item');
const tabs = {
    dashboard: document.getElementById('dashboard-tab'),
    files: document.getElementById('files-tab'),
    settings: document.getElementById('settings-tab')
};

const statusBadge = document.getElementById('system-status-badge');
const scanBtn = document.getElementById('trigger-scan-btn');

// Metrics elements
const totalEl = document.getElementById('metric-total');
const searchableEl = document.getElementById('metric-searchable');
const ocrSuccessEl = document.getElementById('metric-ocr-success');
const failedEl = document.getElementById('metric-failed');

// Tables
const directoriesTableBody = document.querySelector('#directories-table tbody');
const filesTableBody = document.querySelector('#files-table tbody');

// Previews
const previewSection = document.getElementById('preview-section');
const previewFilename = document.getElementById('preview-filename');
const closePreviewBtn = document.getElementById('close-preview-btn');
const iframeOriginal = document.getElementById('iframe-original');
const iframeOcr = document.getElementById('iframe-ocr');

// Settings
const settingDirs = document.getElementById('setting-dirs');
const settingSubfolder = document.getElementById('setting-subfolder');
const settingLogfile = document.getElementById('setting-logfile');
const settingLang = document.getElementById('setting-lang');
const settingForce = document.getElementById('setting-force');

// Initialize Dashboard
document.addEventListener('DOMContentLoaded', () => {
    setupTabNavigation();
    fetchStats();
    
    // Poll stats every 3 seconds
    pollInterval = setInterval(fetchStats, 3000);
    
    // Send heartbeat every 2.5 seconds
    startHeartbeat();
    
    // Scan trigger event
    scanBtn.addEventListener('click', triggerScan);
    
    // Close preview
    closePreviewBtn.addEventListener('click', () => {
        previewSection.style.display = 'none';
        iframeOriginal.src = '';
        iframeOcr.src = '';
    });
});

// Tab Navigation
function setupTabNavigation() {
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const tabName = item.getAttribute('data-tab');
            switchTab(tabName);
        });
    });
}

function switchTab(tabName) {
    currentTab = tabName;
    
    // Update active nav item
    navItems.forEach(item => {
        if (item.getAttribute('data-tab') === tabName) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });
    
    // Update visible content panel
    Object.keys(tabs).forEach(key => {
        if (key === tabName) {
            tabs[key].style.display = 'block';
        } else {
            tabs[key].style.display = 'none';
        }
    });
}

// Heartbeat Mechanism
function startHeartbeat() {
    sendHeartbeat();
    heartbeatInterval = setInterval(sendHeartbeat, 2500);
    
    // Stop heartbeats immediately on tab close/unload
    window.addEventListener('beforeunload', () => {
        clearInterval(heartbeatInterval);
        clearInterval(pollInterval);
    });
}

function sendHeartbeat() {
    fetch('/api/heartbeat', { method: 'POST' })
        .then(res => res.json())
        .catch(err => console.error("Heartbeat error:", err));
}

// Fetch Stats and Reports
function fetchStats() {
    fetch('/api/stats')
        .then(res => res.json())
        .then(data => {
            updateMetrics(data.stats);
            updateDirectoriesTable(data.directories);
            updateFilesTable(data.files);
            updateSettings(data.config);
            updateScanningStatus(data.scanning);
        })
        .catch(err => {
            console.error("Error fetching stats:", err);
        });
}

// Update UI Scanning Status
function updateScanningStatus(scanning) {
    isScanning = scanning;
    if (scanning) {
        statusBadge.textContent = 'Scanning...';
        statusBadge.className = 'badge-status scanning';
        scanBtn.disabled = true;
        scanBtn.textContent = '🔄 Scanning...';
    } else {
        statusBadge.textContent = 'Idle';
        statusBadge.className = 'badge-status idle';
        scanBtn.disabled = false;
        scanBtn.textContent = '⚡ Scan Directories';
    }
}

// Update Metrics Cards
function updateMetrics(stats) {
    if (!stats) return;
    
    totalEl.textContent = stats.total_pdfs || 0;
    
    const percentage = stats.total_pdfs > 0 
        ? Math.round((stats.already_searchable / stats.total_pdfs) * 100) 
        : 0;
        
    searchableEl.textContent = `${percentage}%`;
    ocrSuccessEl.textContent = stats.ocr_succeeded || 0;
    failedEl.textContent = stats.ocr_failed || 0;
}

// Update Directories table
function updateDirectoriesTable(directories) {
    if (!directories || directories.length === 0) {
        directoriesTableBody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center text-dim">No directories scanned yet. Click "Scan Directories" to begin.</td>
            </tr>
        `;
        return;
    }
    
    directoriesTableBody.innerHTML = directories.map(dir => {
        const total = dir.total_files || 0;
        const processed = (dir.already_searchable || 0) + (dir.ocr_succeeded || 0);
        const progressPercent = total > 0 ? Math.round((processed / total) * 100) : 100;
        
        let statusBadgeClass = 'idle';
        let statusLabel = 'Idle';
        
        if (isScanning && progressPercent < 100) {
            statusBadgeClass = 'scanning';
            statusLabel = 'Processing';
        } else if (progressPercent === 100) {
            statusBadgeClass = 'ocr-complete';
            statusLabel = 'Completed';
        }
        
        // Shorten directory path for presentation
        const pathParts = dir.path.split('/');
        const shortPath = pathParts.length > 3 
            ? '.../' + pathParts.slice(-2).join('/') 
            : dir.path;
            
        return `
            <tr>
                <td title="${dir.path}"><strong>${shortPath}</strong></td>
                <td>
                    <div class="progress-bar-container">
                        <div class="progress-bar-fill" style="width: ${progressPercent}%"></div>
                    </div>
                    <span class="progress-label">${progressPercent}%</span>
                </td>
                <td>${total}</td>
                <td>${dir.ocr_succeeded} / ${dir.already_searchable}</td>
                <td><span class="badge-status ${statusBadgeClass}">${statusLabel}</span></td>
            </tr>
        `;
    }).join('');
}

// Update Files Log Table
function updateFilesTable(files) {
    if (!files || files.length === 0) {
        filesTableBody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center text-dim">No files indexed yet. Run a scan.</td>
            </tr>
        `;
        return;
    }
    
    // Sort files by latest processed
    const sortedFiles = [...files].sort((a, b) => new Date(b.processed_at) - new Date(a.processed_at));
    
    filesTableBody.innerHTML = sortedFiles.map(file => {
        let statusClass = 'idle';
        let statusText = 'Checked';
        let actionHtml = '';
        
        if (file.status === 'ALREADY_SEARCHABLE') {
            statusClass = 'searchable';
            statusText = 'Searchable';
            actionHtml = `<a class="link-action" onclick="viewDocument('${file.original_path.replace(/'/g, "\\'")}', null, '${file.rel_path.replace(/'/g, "\\'")}')">View</a>`;
        } else if (file.status === 'OCR_SUCCESS') {
            statusClass = 'ocr-complete';
            statusText = 'OCR Succeeded';
            actionHtml = `<a class="link-action" onclick="viewDocument('${file.original_path.replace(/'/g, "\\'")}', '${file.ocr_path.replace(/'/g, "\\'")}', '${file.rel_path.replace(/'/g, "\\'")}')">Compare Preview</a>`;
        } else {
            statusClass = 'unsearchable';
            statusText = file.status.replace('_', ' ');
            actionHtml = `<a class="link-action" onclick="viewDocument('${file.original_path.replace(/'/g, "\\'")}', null, '${file.rel_path.replace(/'/g, "\\'")}')">Inspect Original</a>`;
        }
        
        const dateStr = new Date(file.processed_at).toLocaleString();
        const filename = file.original_path.split('/').pop();
        
        return `
            <tr>
                <td><strong>${filename}</strong></td>
                <td class="text-dim" title="${file.rel_path}">${file.rel_path}</td>
                <td><span class="badge-status ${statusClass}">${statusText}</span></td>
                <td>${dateStr}</td>
                <td>${actionHtml}</td>
            </tr>
        `;
    }).join('');
}

// Update Settings
function updateSettings(config) {
    if (!config) return;
    settingDirs.textContent = config.scan_directories.join(', ');
    settingSubfolder.textContent = config.ocr_subfolder;
    settingLogfile.textContent = config.log_file;
    settingLang.textContent = config.ocr_lang;
    settingForce.textContent = config.force_ocr ? 'True' : 'False';
}

// Trigger Scan
function triggerScan() {
    if (isScanning) return;
    
    updateScanningStatus(true);
    
    fetch('/api/scan', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            console.log("Scan started:", data);
            fetchStats();
        })
        .catch(err => {
            console.error("Scan error:", err);
            updateScanningStatus(false);
        });
}

// Load Document into split screen view
window.viewDocument = function(originalPath, ocrPath, relPath) {
    previewFilename.textContent = relPath.split('/').pop();
    
    // Set up original source
    iframeOriginal.src = `/files/${encodeURIComponent(originalPath)}`;
    
    // Set up OCR source or hide if not present
    const ocrPanel = iframeOcr.closest('.preview-panel');
    if (ocrPath) {
        iframeOcr.src = `/files/${encodeURIComponent(ocrPath)}`;
        ocrPanel.style.display = 'flex';
        iframeOriginal.closest('.preview-panel').querySelector('.panel-header').textContent = 'Original Scan (Not Searchable)';
    } else {
        iframeOcr.src = '';
        ocrPanel.style.display = 'none';
        iframeOriginal.closest('.preview-panel').querySelector('.panel-header').textContent = 'Document View';
    }
    
    // Open preview tab & scroll to view
    previewSection.style.display = 'block';
    switchTab('dashboard'); // Always switch back to dashboard tab where preview resides
    
    setTimeout(() => {
        previewSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
};
