chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === 'GET_COMMENT_ANALYSIS') {
    const url = `http://127.0.0.1:5000/analyze/${request.videoId}`;
    console.log(`Fetching from: ${url}`);
    
    fetch(url)
      .then(response => response.json())
      .then(data => sendResponse(data))
      .catch(error => sendResponse({ error: error.toString() }));
    
    return true; // Keep the message channel open for the async response
  }
});