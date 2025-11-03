// Apple-style web interface for yt2pod

const urlInput = document.getElementById('urlInput');
const submitBtn = document.getElementById('submitBtn');
const inputGroup = document.getElementById('inputGroup');
const status = document.getElementById('status');
const statusText = document.getElementById('statusText');
const result = document.getElementById('result');
const resultTitle = document.getElementById('resultTitle');
const resultMeta = document.getElementById('resultMeta');
const resultFile = document.getElementById('resultFile');
const error = document.getElementById('error');
const errorText = document.getElementById('errorText');
const podcastInfo = document.getElementById('podcastInfo');

let currentJobId = null;
let statusCheckInterval = null;

// Load config on page load
fetch('/api/config')
    .then(res => res.json())
    .then(data => {
        if (data.podcast_title) {
            podcastInfo.textContent = data.podcast_title;
        }
    })
    .catch(() => {});

// Submit URL
submitBtn.addEventListener('click', () => submitUrl());
urlInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        submitUrl();
    }
});

function submitUrl() {
    const url = urlInput.value.trim();
    
    if (!url) {
        showError('Вставьте ссылку YouTube');
        return;
    }

    // Reset UI
    hideAll();
    inputGroup.classList.add('processing');
    submitBtn.disabled = true;

    // Submit to backend
    fetch('/api/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            showError(data.error);
            return;
        }

        currentJobId = data.job_id;
        showStatus('Обработка...');
        startStatusCheck();
    })
    .catch(err => {
        showError('Ошибка соединения');
        console.error(err);
    });
}

function startStatusCheck() {
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
    }

    statusCheckInterval = setInterval(() => {
        if (!currentJobId) return;

        fetch(`/api/status/${currentJobId}`)
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    stopStatusCheck();
                    showError(data.error);
                    return;
                }

                // Update status text
                if (data.message) {
                    statusText.textContent = data.message;
                }
                
                // Update progress bar if available
                if (data.progress) {
                    updateProgressBar(data.progress);
                }

                // Check if completed
                if (data.status === 'completed') {
                    stopStatusCheck();
                    showResult(data);
                } else if (data.status === 'error') {
                    stopStatusCheck();
                    showError(data.message || 'Ошибка обработки');
                }
            })
            .catch(err => {
                stopStatusCheck();
                showError('Ошибка проверки статуса');
                console.error(err);
            });
    }, 1000);
}

function stopStatusCheck() {
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
        statusCheckInterval = null;
    }
}

function updateProgressBar(progressData) {
    const progressBar = document.getElementById('progressBar');
    const progressFill = document.getElementById('progressFill');
    const progressPercent = document.getElementById('progressPercent');
    
    if (progressBar && progressData.percent !== undefined) {
        progressBar.style.display = 'block';
        progressFill.style.width = `${progressData.percent}%`;
        progressPercent.textContent = `${Math.round(progressData.percent)}%`;
    }
}

function showStatus(message) {
    hideAll();
    status.style.display = 'block';
    statusText.textContent = message;
    
    // Reset progress bar
    const progressBar = document.getElementById('progressBar');
    if (progressBar) {
        progressBar.style.display = 'none';
    }
}

function showResult(data) {
    hideAll();
    inputGroup.classList.remove('processing');
    submitBtn.disabled = false;
    
    result.style.display = 'block';
    
    if (data.duplicate) {
        resultTitle.textContent = 'Уже в фиде';
        resultMeta.textContent = data.title || '';
        resultFile.textContent = '';
    } else {
        resultTitle.textContent = data.title || 'Готово';
        resultMeta.textContent = data.duration ? `Длительность: ${data.duration}` : '';
        resultFile.textContent = data.file_name || '';
    }
    
    // Clear input
    urlInput.value = '';
    currentJobId = null;
}

function showError(message) {
    hideAll();
    inputGroup.classList.remove('processing');
    submitBtn.disabled = false;
    
    error.style.display = 'block';
    errorText.textContent = message;
    
    currentJobId = null;
    
    // Auto-hide after 3 seconds
    setTimeout(() => {
        if (error.style.display === 'block') {
            error.style.display = 'none';
        }
    }, 3000);
}

function hideAll() {
    status.style.display = 'none';
    result.style.display = 'none';
    error.style.display = 'none';
}

// Auto-focus input on load
window.addEventListener('load', () => {
    urlInput.focus();
});
