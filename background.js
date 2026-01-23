chrome.omnibox.onInputChanged.addListener((text, suggest) => {
  if (text.startsWith('http') || text.startsWith('ftp')) {
    suggest([
      {
        content: text,
        description: `Download: ${text}`
      }
    ]);
  }
});

chrome.omnibox.onInputEntered.addListener((text, disposition) => {
  if (text.startsWith('http') || text.startsWith('ftp')) {
    downloadFile(text);
  }
});

function downloadFile(url) {
  chrome.downloads.download({
    url: url,
    saveAs: true
  }, (downloadId) => {
    if (chrome.runtime.lastError) {
      console.error('Download failed:', chrome.runtime.lastError.message);
    } else {
      console.log('Download started with ID:', downloadId);
    }
  });
}

chrome.action.onClicked.addListener((tab) => {
  if (tab.url && (tab.url.startsWith('http') || tab.url.startsWith('ftp'))) {
    downloadFile(tab.url);
  }
});