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

// Chat elements
const chatPanel = document.getElementById('chatPanel');
const chatMessages = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');
const chatSend = document.getElementById('chatSend');
const chatTranscriptStatus = document.getElementById('chatTranscriptStatus');
let chatHistory = [];

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
    const item = document.createElement('div');
    item.className = 'episode-item';
    
    // Format date
    const date = formatDate(episode.pub_date);
    
    const statusBadgeClass = `badge-${(episode.transcript_status || 'none')}`;
    const statusLabel = episode.transcript_status === 'done' ? 'Транскрипт' : (
        episode.transcript_status === 'in_progress' ? 'Транскрибируется' : (
            episode.transcript_status === 'error' ? 'Ошибка' : 'Нет транскрипта'
        )
    );

    item.innerHTML = `
        <div class="episode-header">
            <div class="episode-icon" data-audio-url="${episode.audio_url || ''}">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polygon points="5 3 19 12 5 21 5 3"/>
                </svg>
            </div>
            <div class="episode-info">
                <div class="episode-title">${escapeHtml(episode.title)}</div>
                <div class="episode-meta">
                    ${episode.duration ? `<span class="episode-duration">${episode.duration}</span>` : ''}
                    ${date ? `<span class="episode-date">${date}</span>` : ''}
                    <span class="transcript-badge ${statusBadgeClass}" title="Статус транскрипции">${statusLabel}</span>
                </div>
            </div>
            <button class="episode-delete-btn" data-guid="${episode.guid}" title="Удалить эпизод">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"/>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                    <line x1="10" y1="11" x2="10" y2="17"/>
                    <line x1="14" y1="11" x2="14" y2="17"/>
                </svg>
            </button>
        </div>
    `;
    
    // Add click handler to play button
    const playIcon = item.querySelector('.episode-icon');
    playIcon.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        
        if (!episode.audio_url) {
            alert('Аудио файл не найден');
            return;
        }
        
        playEpisode(episode);
    });
    
    // Add click handler to title (opens external link)
    const titleEl = item.querySelector('.episode-title');
    if (episode.link) {
        titleEl.style.cursor = 'pointer';
        titleEl.addEventListener('click', (e) => {
            e.stopPropagation();
            window.open(episode.link, '_blank', 'noopener,noreferrer');
        });
    }
    
    // Add click handler to delete button
    const deleteBtn = item.querySelector('.episode-delete-btn');
    deleteBtn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        deleteEpisode(episode.guid, episode.title);
    });
    
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
    uploadBtn.disabled = false;
    
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
    
    // Clear inputs and reset forms
    urlInput.value = '';
    resetUploadForm();
    currentJobId = null;
}

// ===== FILE UPLOAD =====
const uploadZone = document.getElementById('uploadZone');
const fileInput = document.getElementById('fileInput');
const uploadMetadata = document.getElementById('uploadMetadata');
const selectedFile = document.getElementById('selectedFile');
const titleInput = document.getElementById('titleInput');
const descriptionInput = document.getElementById('descriptionInput');
const uploadBtn = document.getElementById('uploadBtn');

let selectedFileObj = null;

// Click to browse
uploadZone.addEventListener('click', () => {
    fileInput.click();
});

// File selected
fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        handleFileSelect(file);
    }
});

// Drag and drop
uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('drag-over');
});

uploadZone.addEventListener('dragleave', () => {
    uploadZone.classList.remove('drag-over');
});

uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('drag-over');
    
    const file = e.dataTransfer.files[0];
    if (file) {
        handleFileSelect(file);
    }
});

function handleFileSelect(file) {
    // Check file type
    const validTypes = ['audio/mpeg', 'audio/mp4', 'audio/x-m4a', 'video/mp4'];
    const validExts = ['.mp3', '.mp4', '.m4a'];
    const hasValidExt = validExts.some(ext => file.name.toLowerCase().endsWith(ext));
    
    if (!validTypes.includes(file.type) && !hasValidExt) {
        showError('Неподдерживаемый формат. Используйте MP3, MP4 или M4A');
        return;
    }
    
    // Check file size (500MB)
    if (file.size > 500 * 1024 * 1024) {
        showError('Файл слишком большой. Максимум 500MB');
        return;
    }
    
    selectedFileObj = file;
    selectedFile.textContent = `📎 ${file.name} (${formatFileSize(file.size)})`;
    
    // Show metadata form
    uploadZone.style.display = 'none';
    uploadMetadata.style.display = 'block';
    
    // Auto-fill title from filename
    const filename = file.name.replace(/\.(mp3|mp4|m4a)$/i, '');
    titleInput.value = filename;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Upload button click
uploadBtn.addEventListener('click', () => {
    if (!selectedFileObj) return;
    
    const title = titleInput.value.trim();
    const description = descriptionInput.value.trim();
    
    // Reset UI
    inputGroup.classList.add('processing');
    uploadBtn.disabled = true;
    
    // Show loading status
    showStatus('Загрузка файла...');
    
    // Create FormData
    const formData = new FormData();
    formData.append('file', selectedFileObj);
    if (title) formData.append('title', title);
    if (description) formData.append('description', description);
    
    // Upload
    fetch('/api/upload', {
        method: 'POST',
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            showError(data.error);
            uploadBtn.disabled = false;
            resetUploadForm();
            return;
        }
        
        currentJobId = data.job_id;
        showStatus('Обработка файла...');
        
        // Start status polling
        startStatusCheck();
    })
    .catch(err => {
        showError('Ошибка загрузки: ' + err.message);
        uploadBtn.disabled = false;
        resetUploadForm();
    });
});

// Reset upload form when switching tabs
function resetUploadForm() {
    selectedFileObj = null;
    fileInput.value = '';
    titleInput.value = '';
    descriptionInput.value = '';
    uploadZone.style.display = 'block';
    uploadMetadata.style.display = 'none';
    uploadBtn.disabled = false;
}

// ===== AUDIO PLAYER =====
const audioPlayer = document.getElementById('audioPlayer');
const audioElement = document.getElementById('audioElement');
const audioPlayerTitle = document.getElementById('audioPlayerTitle');
const audioPlayerMeta = document.getElementById('audioPlayerMeta');
const audioPlayerPlayPause = document.getElementById('audioPlayerPlayPause');
const audioPlayerProgress = document.getElementById('audioPlayerProgress');
const audioPlayerClose = document.getElementById('audioPlayerClose');
const audioPlayerVolume = document.getElementById('audioPlayerVolume');

let currentEpisode = null;

// Close player
audioPlayerClose.addEventListener('click', () => {
    audioElement.pause();
    audioPlayer.style.display = 'none';
    currentEpisode = null;
});

// Play/Pause toggle
audioPlayerPlayPause.addEventListener('click', () => {
    if (audioElement.paused) {
        audioElement.play();
    } else {
        audioElement.pause();
    }
});

// Update UI when playing/paused
audioElement.addEventListener('play', () => {
    audioPlayerPlayPause.querySelector('.play-icon').style.display = 'none';
    audioPlayerPlayPause.querySelector('.pause-icon').style.display = 'block';
});

audioElement.addEventListener('pause', () => {
    audioPlayerPlayPause.querySelector('.play-icon').style.display = 'block';
    audioPlayerPlayPause.querySelector('.pause-icon').style.display = 'none';
});

// Update progress and time
audioElement.addEventListener('timeupdate', () => {
    if (audioElement.duration) {
        const progress = (audioElement.currentTime / audioElement.duration) * 100;
        audioPlayerProgress.value = progress;
        
        const current = formatTime(audioElement.currentTime);
        const total = formatTime(audioElement.duration);
        audioPlayerMeta.textContent = `${current} / ${total}`;
    }
});

// Seek when clicking on progress bar
audioPlayerProgress.addEventListener('input', (e) => {
    const seekTime = (e.target.value / 100) * audioElement.duration;
    audioElement.currentTime = seekTime;
});

// Volume toggle
audioPlayerVolume.addEventListener('click', () => {
    if (audioElement.volume > 0) {
        audioElement.volume = 0;
        audioPlayerVolume.style.opacity = '0.3';
    } else {
        audioElement.volume = 1;
        audioPlayerVolume.style.opacity = '0.6';
    }
});

// Format time (seconds to MM:SS)
function formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return '00:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

// Play episode function (called when clicking episode icon)
function playEpisode(episode) {
    currentEpisode = episode;
    
    // Show player
    audioPlayer.style.display = 'block';
    
    // Set audio source - use proxy for GitHub URLs to avoid CORS
    const audioUrl = episode.audio_url;
    if (audioUrl.startsWith('https://github.com/')) {
        // Use proxy endpoint
        audioElement.src = `/api/proxy-audio?url=${encodeURIComponent(audioUrl)}`;
    } else {
        // Use direct URL for local files
        audioElement.src = audioUrl;
    }
    
    // Update info
    audioPlayerTitle.textContent = episode.title;
    audioPlayerMeta.textContent = '00:00 / 00:00';
    
    // Reset progress
    audioPlayerProgress.value = 0;
    
    // Play
    audioElement.play().catch(err => {
        console.error('Failed to play audio:', err);
        alert('Не удалось воспроизвести аудио');
    });

    // Reset chat for new episode
    chatHistory = [];
    chatMessages.innerHTML = '';
    chatInput.disabled = false;
    updateChatTranscriptStatus('—', '');

    // Ensure transcription started
    if (episode.guid && episode.audio_url) {
        fetch('/api/transcripts/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ guid: episode.guid, audio_url: episode.audio_url })
        })
        .then(res => res.json())
        .then(() => {
            pollTranscriptStatus(episode.guid);
        })
        .catch(() => {});
    }
}

// Delete episode function
function deleteEpisode(guid, title) {
    // Confirm deletion
    if (!confirm(`Удалить эпизод?\n\n"${title}"\n\nЭто действие необратимо.`)) {
        return;
    }
    
    // Show loading
    showStatus('Удаление эпизода...');
    
    // Send delete request
    fetch(`/api/episodes/${guid}`, {
        method: 'DELETE'
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            showError(data.error);
            return;
        }
        
        // Hide status and show success briefly
        hideAll();
        showStatus('Эпизод удален');
        
        // Reload episodes after a short delay
        setTimeout(() => {
            hideAll();
            loadEpisodes();
        }, 1000);
        
        // If currently playing this episode, stop it
        if (currentEpisode && currentEpisode.guid === guid) {
            audioPlayerClose.click();
        }
    })
    .catch(err => {
        showError('Ошибка удаления: ' + err.message);
        console.error(err);
    });
}

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    if (!audioPlayer.style.display || audioPlayer.style.display === 'none') return;
    
    // Space - play/pause
    if (e.code === 'Space' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
        e.preventDefault();
        audioPlayerPlayPause.click();
    }
    
    // Arrow Left - rewind 10s
    if (e.code === 'ArrowLeft') {
        e.preventDefault();
        audioElement.currentTime = Math.max(0, audioElement.currentTime - 10);
    }
    
    // Arrow Right - forward 10s
    if (e.code === 'ArrowRight') {
        e.preventDefault();
        audioElement.currentTime = Math.min(audioElement.duration, audioElement.currentTime + 10);
    }
});

// ===== CHAT LOGIC =====
function appendChatMessage(role, content) {
    const div = document.createElement('div');
    div.className = `msg msg-${role}`;
    div.textContent = content;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function updateChatTranscriptStatus(text, statusClass) {
    chatTranscriptStatus.textContent = text;
    chatTranscriptStatus.classList.remove('status-none', 'status-in_progress', 'status-done', 'status-error');
    if (statusClass) chatTranscriptStatus.classList.add(statusClass);
}

function pollTranscriptStatus(guid) {
    if (!guid) return;
    fetch(`/api/transcripts/status/${guid}`)
        .then(res => res.json())
        .then(data => {
            const st = data.status || 'none';
            if (st === 'done') updateChatTranscriptStatus('Готово', 'status-done');
            else if (st === 'in_progress') updateChatTranscriptStatus('В процессе', 'status-in_progress');
            else if (st === 'error') updateChatTranscriptStatus('Ошибка', 'status-error');
            else updateChatTranscriptStatus('Нет', 'status-none');

            if (st === 'in_progress') {
                setTimeout(() => pollTranscriptStatus(guid), 5000);
            }
        })
        .catch(() => {});
}

function sendChat() {
    if (!currentEpisode || !currentEpisode.guid) {
        appendChatMessage('assistant', 'Сначала запустите воспроизведение эпизода.');
        return;
    }
    const text = chatInput.value.trim();
    if (!text) return;
    chatInput.value = '';
    chatInput.disabled = true;
    appendChatMessage('user', text);

    fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            guid: currentEpisode.guid,
            message: text,
            history: chatHistory
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            appendChatMessage('assistant', 'Ошибка чата: ' + (data.details?.message || data.error));
            return;
        }
        const reply = data.reply || '...';
        appendChatMessage('assistant', reply);
        // update history
        chatHistory.push({ role: 'user', content: text });
        chatHistory.push({ role: 'assistant', content: reply });
    })
    .catch(err => {
        appendChatMessage('assistant', 'Ошибка сети: ' + err.message);
    })
    .finally(() => {
        chatInput.disabled = false;
        chatInput.focus();
    });
}

chatSend.addEventListener('click', () => sendChat());
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendChat();
});
