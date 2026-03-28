// content.js - Enhanced version with better UI and error handling

function injectButton() {
  const targetElement = document.querySelector('#above-the-fold #top-row');
  if (targetElement && !document.getElementById('yt-comment-analyzer-btn')) {
    const btn = document.createElement('button');
    btn.textContent = 'Analyze Comments';
    btn.id = 'yt-comment-analyzer-btn';
    btn.onclick = handleAnalysisClick;
    targetElement.appendChild(btn);
  }
}

function handleAnalysisClick() {
  const videoId = new URL(window.location.href).searchParams.get("v");
  
  if (!videoId) {
    displayResultsPanel('<p class="error-msg">Error: Could not find video ID.</p>');
    return;
  }
  
  displayResultsPanel(`
    <div class="loading-container">
      <div class="spinner"></div>
      <p>Fetching and analyzing comments...</p>
      <p class="loading-subtext">This may take 1-2 minutes for videos with many comments</p>
    </div>
  `);
  
  chrome.runtime.sendMessage({ 
    type: 'GET_COMMENT_ANALYSIS', 
    videoId: videoId 
  }, (response) => {
    if (!response || response.error) {
      const errorMsg = response ? response.error : 'No response from backend.';
      displayResultsPanel(`
        <div class="error-container">
          <h3>❌ Analysis Failed</h3>
          <p class="error-msg">${errorMsg}</p>
          <p class="error-help">Make sure the Flask server is running at http://127.0.0.1:5000</p>
        </div>
      `);
    } else {
      const resultsHTML = formatResults(response);
      displayResultsPanel(resultsHTML);
    }
  });
}

function displayResultsPanel(content) {
  const existingOverlay = document.getElementById('yt-results-overlay');
  if (existingOverlay) existingOverlay.remove();
  
  const overlay = document.createElement('div');
  overlay.id = 'yt-results-overlay';
  
  const panel = document.createElement('div');
  panel.id = 'yt-results-panel';
  
  const closeBtn = document.createElement('span');
  closeBtn.id = 'yt-results-close-btn';
  closeBtn.innerHTML = '&times;';
  closeBtn.onclick = () => overlay.remove();
  
  panel.innerHTML = content;
  panel.prepend(closeBtn);
  overlay.appendChild(panel);
  document.body.appendChild(overlay);
  
  // Close on overlay click
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) {
      overlay.remove();
    }
  });
}

function formatResults(data) {
  console.log("Analysis Results:", data);
  
  // Extract sentiment data with fallbacks
  const positive = data.sentiment?.positive || 0;
  const negative = data.sentiment?.negative || 0;
  const neutral = data.sentiment?.neutral || 0;
  const total = positive + negative + neutral;
  
  if (total === 0) {
    return `
      <div class="error-container">
        <h3>⚠️ No Valid Comments Found</h3>
        <p>Fetched ${data.totalFetched || 0} comments, but none were suitable for analysis.</p>
        <p class="error-help">This may happen if:</p>
        <ul>
          <li>Comments are disabled</li>
          <li>Most comments are not in English</li>
          <li>Comments are too short or spam</li>
        </ul>
      </div>
    `;
  }
  
  const pos_percent = ((positive / total) * 100).toFixed(1);
  const neg_percent = ((negative / total) * 100).toFixed(1);
  const neu_percent = ((neutral / total) * 100).toFixed(1);

  
  // Format topics
  let topicsHTML = '';
  if (data.topics && data.topics.length > 0) {
    topicsHTML = data.topics
      .filter(topic => topic && topic.length > 0)
      .slice(0, 5)
      .map((topic) => `<li class="topic-tag">${escapeHtml(topic)}</li>`)
      .join('');
  }
  
  if (!topicsHTML) {
    topicsHTML = '<li class="topic-tag">No clear topics detected</li>';
  }
  
  // Sentiment emoji and color
  let overallEmoji = '😐';
  let overallText = 'Mixed';
  let overallClass = 'neutral';
  
  if (positive > negative + neutral) {
    overallEmoji = '😊';
    overallText = 'Mostly Positive';
    overallClass = 'positive';
  } else if (negative > positive + neutral) {
    overallEmoji = '😟';
    overallText = 'Mostly Negative';
    overallClass = 'negative';
  }
  
  return `
    <h3>📊 Analysis Complete</h3>
    <div class="stats-overview">
      <div class="stat-box">
        <div class="stat-number">${data.commentCount}</div>
        <div class="stat-label">Comments Analyzed</div>
      </div>
      <div class="stat-box">
        <div class="stat-number ${overallClass}">${overallEmoji}</div>
        <div class="stat-label">${overallText}</div>
      </div>
    </div>
    
    <h4>💭 Sentiment Distribution</h4>
    <div class="sentiment-bar-container">
      <div class="sentiment-bar-positive" style="width: ${pos_percent}%;" title="${positive} positive comments">
        ${pos_percent > 10 ? pos_percent + '%' : ''}
      </div>
      <div class="sentiment-bar-neutral" style="width: ${neu_percent}%;" title="${neutral} neutral comments">
        ${neu_percent > 10 ? neu_percent + '%' : ''}
      </div>
      <div class="sentiment-bar-negative" style="width: ${neg_percent}%;" title="${negative} negative comments">
        ${neg_percent > 10 ? neg_percent + '%' : ''}
      </div>
    </div>
    <div class="sentiment-legend">
      <span class="legend-item"><span class="legend-color positive"></span> Positive: ${positive} (${pos_percent}%)</span>
      <span class="legend-item"><span class="legend-color neutral"></span> Neutral: ${neutral} (${neu_percent}%)</span>
      <span class="legend-item"><span class="legend-color negative"></span> Negative: ${negative} (${neg_percent}%)</span>
    </div>
    
    <h4>🔥 Hot Topics</h4>
    <ul class="topic-list">${topicsHTML}</ul>
    
    ${data.mostLikedComment ? `
      <h4>👍 Most Liked Comment (${data.mostLikedComment.likes} likes)</h4>
      <div class="comment-card ${data.mostLikedComment.sentiment}">
        <em>"${escapeHtml(truncateText(data.mostLikedComment.text, 200))}"</em>
      </div>
    ` : ''}
    
    <h4>😊 Most Positive Comment</h4>
    <div class="comment-card positive">
      <em>"${escapeHtml(truncateText(data.topPositiveComment, 200))}"</em>
    </div>
    
    <h4>😞 Most Negative Comment</h4>
    <div class="comment-card negative">
      <em>"${escapeHtml(truncateText(data.topNegativeComment, 200))}"</em>
    </div>
    
    <div class="footer-info">
      <small>Analyzed ${data.commentCount} out of ${data.totalFetched || data.commentCount} fetched comments</small>
    </div>
  `;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function truncateText(text, maxLength) {
  if (!text || text === 'N/A') return text;
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
}

// Initialize button injection
const observer = new MutationObserver((mutations, obs) => {
  const targetElement = document.querySelector('#above-the-fold #top-row');
  if (targetElement) {
    injectButton();
    obs.disconnect();
  }
});

observer.observe(document.body, { childList: true, subtree: true });

// Re-inject on page navigation (YouTube SPA)
let lastUrl = location.href;
new MutationObserver(() => {
  const url = location.href;
  if (url !== lastUrl) {
    lastUrl = url;
    setTimeout(injectButton, 1000);
  }
}).observe(document, { subtree: true, childList: true });