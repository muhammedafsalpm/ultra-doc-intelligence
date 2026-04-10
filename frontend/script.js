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
    
    // Check if file is too large
    if (fileSizeMB > 100) {
        showStatus('File too large. Maximum size is 100MB', 'error');
        return;
    }
    
    // Show warning for large files
    if (fileSizeMB > 10) {
        const proceed = confirm(`File size is ${fileSizeMB.toFixed(1)}MB. Large files may take longer to process. Continue?`);
        if (!proceed) return;
        showStatus(`Processing large file (${fileSizeMB.toFixed(1)}MB). This may take a moment...`, 'info');
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    showStatus('Uploading and processing document...', 'info');
    document.getElementById('uploadBtn').disabled = true;
    
    // Use streaming endpoint for large files
    const endpoint = file.size > 10 * 1024 * 1024 ? '/upload-stream' : '/upload';
    
    try {
        const response = await fetch(`${API_URL}${endpoint}`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            currentSessionId = data.session_id;
            showStatus(`✅ ${data.message}`, 'success');
            
            document.getElementById('sessionId').textContent = currentSessionId;
            document.getElementById('docName').textContent = data.filename;
            document.getElementById('chunksCount').textContent = data.chunks_count;
            document.getElementById('sessionInfo').style.display = 'block';
            document.getElementById('askBtn').disabled = false;
            document.getElementById('extractBtn').disabled = false;
        } else {
            showStatus(`❌ Error: ${data.detail}`, 'error');
        }
    } catch (error) {
        showStatus(`❌ Connection error: ${error.message}. Make sure the backend is running on port 8000`, 'error');
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
    document.getElementById('askBtn').textContent = 'Thinking...';
    
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
        document.getElementById('askBtn').textContent = 'Ask';
    }
}

function displayAnswer(data) {
    document.getElementById('answerArea').style.display = 'block';
    document.getElementById('answer').textContent = data.answer;
    
    // Display confidence
    const confidencePercent = (data.confidence_score * 100).toFixed(1);
    document.getElementById('confidenceFill').style.width = `${confidencePercent}%`;
    document.getElementById('confidenceText').textContent = `${confidencePercent}%`;
    
    // Change color based on confidence
    const fill = document.getElementById('confidenceFill');
    if (data.confidence_score < 0.4) {
        fill.style.background = 'linear-gradient(90deg, #f56565, #c53030)';
        fill.style.color = 'white';
    } else if (data.confidence_score < 0.7) {
        fill.style.background = 'linear-gradient(90deg, #ed8936, #dd6b20)';
    } else {
        fill.style.background = 'linear-gradient(90deg, #48bb78, #38a169)';
    }
    
    // Display sources
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
    
    // Display grounding badge
    const badge = document.getElementById('groundedBadge');
    if (data.grounded) {
        badge.textContent = '✓ Grounded Answer - Information verified from document';
        badge.className = 'badge badge-grounded';
    } else {
        badge.textContent = '⚠ Low Confidence - Please verify information';
        badge.className = 'badge badge-not-grounded';
    }
    
    // Scroll to answer
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
            
            // Format JSON for display
            const formatted = {
                extracted_data: data.extracted_data,
                confidence_scores: data.confidence_scores
            };
            
            document.getElementById('extractedJson').textContent = JSON.stringify(formatted, null, 2);
            
            // Highlight null values
            const jsonText = document.getElementById('extractedJson').textContent;
            const highlighted = jsonText.replace(/"null"/g, '"⚠️ null"');
            document.getElementById('extractedJson').textContent = highlighted;
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

// Drag and drop support
const dropZone = document.querySelector('.upload-zone');
if (dropZone) {
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--primary)';
        dropZone.style.background = 'var(--light)';
    });
    
    dropZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--border)';
        dropZone.style.background = 'transparent';
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
        dropZone.style.background = 'transparent';
    });
}
