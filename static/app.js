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
    loadEpisodes();
});

// Episodes management
const episodesList = document.getElementById('episodesList');
const episodesCount = document.getElementById('episodesCount');

function loadEpisodes() {
    fetch('/api/episodes')
        .then(res => res.json())
        .then(data => {
            if (data.episodes && data.episodes.length > 0) {
                displayEpisodes(data.episodes);
                episodesCount.textContent = data.episodes.length;
            } else {
                showEmptyEpisodes();
            }
        })
        .catch(err => {
            console.error('Failed to load episodes:', err);
            showEmptyEpisodes();
        });
}

function displayEpisodes(episodes) {
    episodesList.innerHTML = '';
    
    episodes.forEach(episode => {
        const episodeItem = createEpisodeItem(episode);
        episodesList.appendChild(episodeItem);
    });
}

function createEpisodeItem(episode) {
    const item = document.createElement('a');
    item.className = 'episode-item';
    item.href = episode.link || '#';
    item.target = '_blank';
    item.rel = 'noopener noreferrer';
    
    // Format date
    const date = formatDate(episode.pub_date);
    
    item.innerHTML = `
        <div class="episode-header">
            <div class="episode-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polygon points="5 3 19 12 5 21 5 3"/>
                </svg>
            </div>
            <div class="episode-info">
                <div class="episode-title">${escapeHtml(episode.title)}</div>
                <div class="episode-meta">
                    ${episode.duration ? `<span class="episode-duration">${episode.duration}</span>` : ''}
                    ${date ? `<span class="episode-date">${date}</span>` : ''}
                </div>
            </div>
        </div>
    `;
    
    return item;
}

function formatDate(dateString) {
    if (!dateString) return '';
    
    try {
        const date = new Date(dateString);
        const now = new Date();
        const diffTime = Math.abs(now - date);
        const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
        
        if (diffDays === 0) return 'Сегодня';
        if (diffDays === 1) return 'Вчера';
        if (diffDays < 7) return `${diffDays} дн. назад`;
        if (diffDays < 30) return `${Math.floor(diffDays / 7)} нед. назад`;
        
        // Format as DD.MM.YYYY
        const day = date.getDate().toString().padStart(2, '0');
        const month = (date.getMonth() + 1).toString().padStart(2, '0');
        const year = date.getFullYear();
        return `${day}.${month}.${year}`;
    } catch (e) {
        return '';
    }
}

function showEmptyEpisodes() {
    episodesList.innerHTML = '<div class="episodes-empty">Эпизоды появятся здесь после добавления</div>';
    episodesCount.textContent = '0';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Reload episodes after successful addition
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
        
        // Reload episodes list after successful addition
        setTimeout(() => {
            loadEpisodes();
        }, 1000);
    }
    
    // Clear input
    urlInput.value = '';
    currentJobId = null;
}
