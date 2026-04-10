const API_URL = 'http://localhost:8000';
let currentSessionId = null;

// File handling
document.getElementById('fileInput').addEventListener('change', function(e) {
    const file = e.target.files[0];
    if (file) {
        document.getElementById('fileName').textContent = file.name;
        document.getElementById('fileInfo').style.display = 'flex';
        document.getElementById('uploadBtn').disabled = false;
        document.querySelector('.upload-zone').style.display = 'none';
    }
});

function clearFile() {
    document.getElementById('fileInput').value = '';
    document.getElementById('fileInfo').style.display = 'none';
    document.getElementById('uploadBtn').disabled = true;
    document.querySelector('.upload-zone').style.display = 'block';
}

function setQuestion(question) {
    document.getElementById('questionInput').value = question;
    askQuestion();
}

function showStatus(message, type) {
    const statusDiv = document.getElementById('uploadStatus');
    statusDiv.innerHTML = `<div class="status-message status-${type}">${message}</div>`;
    setTimeout(() => {
        if (statusDiv.firstChild) {
            statusDiv.removeChild(statusDiv.firstChild);
        }
    }, 5000);
}

async function uploadDocument() {
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];
    
    if (!file) {
        showStatus('Please select a file first', 'error');
        return;
    }
    
    const fileSizeMB = file.size / (1024 * 1024);
    if (fileSizeMB > 100) {
        showStatus('File too large. Maximum size is 100MB', 'error');
        return;
    }
    
    if (fileSizeMB > 10) {
        if (!confirm(`File size is ${fileSizeMB.toFixed(1)}MB. Processing may take a moment. Continue?`)) {
            return;
        }
        showStatus(`Processing large file (${fileSizeMB.toFixed(1)}MB)...`, 'info');
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    showStatus('Uploading and processing document...', 'info');
    document.getElementById('uploadBtn').disabled = true;
    
    try {
        const endpoint = file.size > 10 * 1024 * 1024 ? '/upload-stream' : '/upload';
        const response = await fetch(`${API_URL}${endpoint}`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            currentSessionId = data.session_id;
            showStatus(`Success: ${data.message}. Indexed ${data.chunks_count} text chunks.`, 'success');
            
            document.getElementById('sessionId').textContent = currentSessionId;
            document.getElementById('docName').textContent = data.filename;
            document.getElementById('chunksCount').textContent = data.chunks_count;
            document.getElementById('createdAt').textContent = new Date(data.timestamp).toLocaleString();
            document.getElementById('sessionInfo').style.display = 'block';
            document.getElementById('askBtn').disabled = false;
            document.getElementById('extractBtn').disabled = false;
            
            // Refresh sessions list
            refreshSessions();
        } else {
            showStatus(`Error: ${data.detail}`, 'error');
        }
    } catch (error) {
        showStatus(`Connection error: ${error.message}. Make sure backend is running on port 8000`, 'error');
    } finally {
        document.getElementById('uploadBtn').disabled = false;
    }
}

async function askQuestion() {
    const question = document.getElementById('questionInput').value;
    
    if (!question.trim()) {
        alert('Please enter a question');
        return;
    }
    
    if (!currentSessionId) {
        alert('Please upload a document first');
        return;
    }
    
    document.getElementById('askBtn').disabled = true;
    document.getElementById('askBtn').textContent = 'Processing...';
    
    try {
        const response = await fetch(`${API_URL}/ask`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                session_id: currentSessionId,
                question: question
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            displayAnswer(data);
        } else {
            alert(`Error: ${data.detail}`);
        }
    } catch (error) {
        alert(`Connection error: ${error.message}`);
    } finally {
        document.getElementById('askBtn').disabled = false;
        document.getElementById('askBtn').textContent = 'Submit Query';
    }
}

function displayAnswer(data) {
    document.getElementById('answerArea').style.display = 'block';
    document.getElementById('answer').textContent = data.answer;
    
    const confidencePercent = (data.confidence_score * 100).toFixed(1);
    document.getElementById('confidenceFill').style.width = `${confidencePercent}%`;
    document.getElementById('confidenceText').textContent = `${confidencePercent}%`;
    
    const fill = document.getElementById('confidenceFill');
    if (data.confidence_score < 0.4) {
        fill.style.background = 'linear-gradient(90deg, #ef4444, #dc2626)';
    } else if (data.confidence_score < 0.7) {
        fill.style.background = 'linear-gradient(90deg, #f59e0b, #d97706)';
    } else {
        fill.style.background = 'linear-gradient(90deg, #10b981, #059669)';
    }
    
    const sourcesDiv = document.getElementById('sources');
    sourcesDiv.innerHTML = '';
    if (data.sources && data.sources.length > 0) {
        data.sources.forEach((source, index) => {
            const sourceDiv = document.createElement('div');
            sourceDiv.innerHTML = `<strong>Source ${index + 1}:</strong><br>${source}`;
            sourcesDiv.appendChild(sourceDiv);
        });
    } else {
        sourcesDiv.innerHTML = '<div>No specific sources available</div>';
    }
    
    const badge = document.getElementById('groundedBadge');
    if (data.grounded) {
        badge.textContent = 'Verified Answer - Information confirmed from document';
        badge.className = 'badge badge-grounded';
    } else {
        badge.textContent = 'Low Confidence - Please verify information';
        badge.className = 'badge badge-not-grounded';
    }
    
    document.getElementById('answerArea').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

async function extractStructured() {
    if (!currentSessionId) {
        alert('Please upload a document first');
        return;
    }
    
    document.getElementById('extractBtn').disabled = true;
    document.getElementById('extractBtn').textContent = 'Extracting...';
    
    try {
        const response = await fetch(`${API_URL}/extract?session_id=${currentSessionId}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            document.getElementById('extractionResult').style.display = 'block';
            
            const formatted = {
                extracted_data: data.extracted_data,
                confidence_scores: data.confidence_scores
            };
            
            document.getElementById('extractedJson').textContent = JSON.stringify(formatted, null, 2);
        } else {
            alert(`Error: ${data.detail}`);
        }
    } catch (error) {
        alert(`Connection error: ${error.message}`);
    } finally {
        document.getElementById('extractBtn').disabled = false;
        document.getElementById('extractBtn').textContent = 'Extract Shipment Data';
    }
}

async function deleteSession() {
    if (!currentSessionId) {
        return;
    }
    
    if (!confirm('Are you sure you want to delete this session? All document data will be removed.')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/session/${currentSessionId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showStatus('Session deleted successfully', 'success');
            currentSessionId = null;
            document.getElementById('sessionInfo').style.display = 'none';
            document.getElementById('answerArea').style.display = 'none';
            document.getElementById('extractionResult').style.display = 'none';
            document.getElementById('askBtn').disabled = true;
            document.getElementById('extractBtn').disabled = true;
            document.getElementById('questionInput').value = '';
            refreshSessions();
        } else {
            const data = await response.json();
            showStatus(`Error: ${data.detail}`, 'error');
        }
    } catch (error) {
        showStatus(`Connection error: ${error.message}`, 'error');
    }
}

async function refreshSessions() {
    try {
        const response = await fetch(`${API_URL}/sessions`);
        const data = await response.json();
        
        const sessionsList = document.getElementById('sessionsList');
        
        if (data.active_sessions === 0) {
            sessionsList.innerHTML = '<p class="empty-message">No active sessions</p>';
            return;
        }
        
        sessionsList.innerHTML = '';
        data.sessions.forEach(session => {
            const sessionDiv = document.createElement('div');
            sessionDiv.className = 'session-item';
            sessionDiv.innerHTML = `
                <div class="session-info-compact">
                    <div class="session-id">${session.session_id.substring(0, 16)}...</div>
                    <div class="session-doc">${session.filename}</div>
                    <div class="session-doc" style="font-size: 0.7rem; color: #6b7280;">${new Date(session.created_at).toLocaleString()}</div>
                </div>
                <div class="session-actions">
                    <button class="btn-small" onclick="switchToSession('${session.session_id}')">Load</button>
                    <button class="btn-small" onclick="deleteSessionById('${session.session_id}')">Delete</button>
                </div>
            `;
            sessionsList.appendChild(sessionDiv);
        });
    } catch (error) {
        console.error('Failed to refresh sessions:', error);
    }
}

function switchToSession(sessionId) {
    currentSessionId = sessionId;
    
    // Find session data from the list
    fetch(`${API_URL}/sessions`)
        .then(res => res.json())
        .then(data => {
            const session = data.sessions.find(s => s.session_id === sessionId);
            if (session) {
                document.getElementById('sessionId').textContent = sessionId;
                document.getElementById('docName').textContent = session.filename;
                document.getElementById('chunksCount').textContent = session.chunks_count;
                document.getElementById('createdAt').textContent = new Date(session.created_at).toLocaleString();
                document.getElementById('sessionInfo').style.display = 'block';
                document.getElementById('askBtn').disabled = false;
                document.getElementById('extractBtn').disabled = false;
                showStatus(`Loaded session for ${session.filename}`, 'success');
            }
        })
        .catch(error => {
            showStatus(`Error loading session: ${error.message}`, 'error');
        });
}

async function deleteSessionById(sessionId) {
    if (!confirm('Delete this session?')) return;
    
    try {
        const response = await fetch(`${API_URL}/session/${sessionId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            if (currentSessionId === sessionId) {
                currentSessionId = null;
                document.getElementById('sessionInfo').style.display = 'none';
                document.getElementById('askBtn').disabled = true;
                document.getElementById('extractBtn').disabled = true;
            }
            refreshSessions();
            showStatus('Session deleted', 'success');
        }
    } catch (error) {
        showStatus(`Error: ${error.message}`, 'error');
    }
}

function copyToClipboard() {
    const jsonText = document.getElementById('extractedJson').textContent;
    navigator.clipboard.writeText(jsonText).then(() => {
        showStatus('JSON copied to clipboard', 'success');
    }).catch(() => {
        showStatus('Failed to copy', 'error');
    });
}

// Drag and drop support
const dropZone = document.querySelector('.upload-zone');
if (dropZone) {
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--primary)';
        dropZone.style.background = '#eff6ff';
    });
    
    dropZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--border)';
        dropZone.style.background = 'var(--light)';
    });
    
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        const file = e.dataTransfer.files[0];
        if (file) {
            const fileInput = document.getElementById('fileInput');
            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(file);
            fileInput.files = dataTransfer.files;
            
            const event = new Event('change');
            fileInput.dispatchEvent(event);
        }
        dropZone.style.borderColor = 'var(--border)';
        dropZone.style.background = 'var(--light)';
    });
}

// Load sessions on page load
refreshSessions();
