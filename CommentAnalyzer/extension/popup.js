document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('analyze-button').addEventListener('click', onAnalyzeClick);
});

function onAnalyzeClick() {
  const button = document.getElementById('analyze-button');
  const statusText = document.getElementById('status-text');
  const resultsContainer = document.getElementById('results-container');

  button.disabled = true;
  statusText.textContent = 'Finding video ID...';
  resultsContainer.innerHTML = '';

  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (!tabs[0].url.includes("youtube.com/watch")) {
      statusText.textContent = 'Error: Not a YouTube video page.';
      button.disabled = false;
      return;
    }
    
    const videoId = new URL(tabs[0].url).searchParams.get("v");
    statusText.textContent = 'Sending request to backend... (This can take a minute)';

    chrome.runtime.sendMessage({ type: 'GET_COMMENT_ANALYSIS', videoId: videoId }, (response) => {
      if (response.error) {
        statusText.textContent = `Error: ${response.error}`;
      } else {
        statusText.textContent = `Analysis Complete for ${response.commentCount} comments.`;
        displayResults(response);
      }
      button.disabled = false;
    });
  });
}

function displayResults(data) {
  const resultsContainer = document.getElementById('results-container');
  const positive = data.sentiment.POSITIVE || 0;
  const negative = data.sentiment.NEGATIVE || 0;

  let topicsHTML = data.topics.map((topic, index) => `<li><b>Topic ${index + 1}:</b> ${topic}</li>`).join('');

  resultsContainer.innerHTML = `
    <h4>Sentiment Breakdown</h4>
    <p>Positive: ${positive} | Negative: ${negative}</p>
    <h4>Dominant Topics</h4>
    <ul>${topicsHTML}</ul>
    <h4>Top Positive Comment</h4>
    <p><em>"${data.topPositiveComment}"</em></p>
    <h4>Top Negative Comment</h4>
    <p><em>"${data.topNegativeComment}"</em></p>
  `;
} 