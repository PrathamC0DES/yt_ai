
let sponsorSegments = [];
let currentVideoId = null;
let checkInterval = null;
let skipButton = null;


function getVideoId() {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get('v');
}


async function fetchSponsorSegments(videoId) {
  try {
    console.log('ðŸ” Smart Skip: Fetching sponsor data for video:', videoId);
    
    const response = await fetch(
      `https://sponsor.ajay.app/api/skipSegments?videoID=${videoId}&categories=["sponsor","selfpromo","interaction","intro","outro","preview","music_offtopic"]`
    );
    
    if (response.ok) {
      const data = await response.json();
      console.log('âœ… Smart Skip: Found segments:', data);
      return data;
    }
    console.log('âš ï¸ Smart Skip: No segments found (404)');
    return [];
  } catch (error) {
    console.log('âŒ Smart Skip: API error:', error);
    return [];
  }
}


function createSkipButton() {
  if (skipButton) return skipButton;
  
  skipButton = document.createElement('div');
  skipButton.id = 'smart-skip-button';
  skipButton.innerHTML = `
    <button class="skip-btn">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
        <path d="M5 4L19 12L5 20V4Z" fill="white"/>
        <rect x="19" y="4" width="2" height="16" fill="white"/>
      </svg>
      <span class="skip-text">Skip Sponsor</span>
      <span class="skip-timer"></span>
    </button>
  `;
  
  skipButton.style.display = 'none';
  
  
  skipButton.querySelector('.skip-btn').addEventListener('click', () => {
    skipCurrentSegment();
  });
  
  return skipButton;
}


function addSkipButtonToPlayer() {
  const player = document.querySelector('.html5-video-player');
  if (player && !document.getElementById('smart-skip-button')) {
    const button = createSkipButton();
    player.appendChild(button);
  }
}


function checkForSponsor() {
  const video = document.querySelector('video');
  if (!video || sponsorSegments.length === 0) return;
  
  const currentTime = video.currentTime;
  
  for (const segment of sponsorSegments) {
    const [start, end] = segment.segment;
    
    
    if (currentTime >= start - 2 && currentTime < start) {
      showSkipButton(segment, start - currentTime);
      return;
    }
    
    
    if (currentTime >= start && currentTime < end) {
      chrome.storage.sync.get(['autoSkip'], (result) => {
        if (result.autoSkip !== false) { 
          video.currentTime = end;
          showNotification('Skipped sponsor segment');
        } else {
          showSkipButton(segment, 0);
        }
      });
      return;
    }
  }
  
  hideSkipButton();
}


function showSkipButton(segment, timeUntil) {
  if (!skipButton) return;
  
  skipButton.style.display = 'block';
  const timer = skipButton.querySelector('.skip-timer');
  
  if (timeUntil > 0) {
    timer.textContent = `in ${Math.ceil(timeUntil)}s`;
  } else {
    timer.textContent = '';
  }
  
  
  skipButton.dataset.segmentEnd = segment.segment[1];
}


function hideSkipButton() {
  if (skipButton) {
    skipButton.style.display = 'none';
  }
}


function skipCurrentSegment() {
  const video = document.querySelector('video');
  const endTime = parseFloat(skipButton.dataset.segmentEnd);
  
  if (video && endTime) {
    video.currentTime = endTime;
    showNotification('Sponsor skipped!');
    hideSkipButton();
  }
}


function showNotification(message) {
  const notification = document.createElement('div');
  notification.className = 'smart-skip-notification';
  notification.textContent = message;
  document.body.appendChild(notification);
  
  setTimeout(() => {
    notification.classList.add('fade-out');
    setTimeout(() => notification.remove(), 300);
  }, 2000);
}


async function initializeVideo() {
  const videoId = getVideoId();
  
  if (videoId && videoId !== currentVideoId) {
    currentVideoId = videoId;
    sponsorSegments = await fetchSponsorSegments(videoId);
    
    if (sponsorSegments.length > 0) {
      console.log(`âœ¨ Smart Skip: Found ${sponsorSegments.length} sponsor segments:`);
      sponsorSegments.forEach((seg, i) => {
        console.log(`   ${i+1}. ${seg.category}: ${seg.segment[0].toFixed(1)}s â†’ ${seg.segment[1].toFixed(1)}s`);
      });
    } else {
      console.log('ðŸ“º Smart Skip: This video has no sponsor data yet');
    }
    
    
    if (checkInterval) {
      clearInterval(checkInterval);
    }
    
    
    if (sponsorSegments.length > 0) {
      addSkipButtonToPlayer();
      checkInterval = setInterval(checkForSponsor, 500);
    }
  }
}


let lastUrl = location.href;
new MutationObserver(() => {
  const url = location.href;
  if (url !== lastUrl) {
    lastUrl = url;
    initializeVideo();
  }
}).observe(document, { subtree: true, childList: true });


if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeVideo);
} else {
  initializeVideo();
}

document.addEventListener('yt-navigate-finish', initializeVideo)