const searchForm = document.querySelector('#searchForm');
const searchInput = document.querySelector('#searchInput');
const searchResults = document.querySelector('#searchResults');
const researchForm = document.querySelector('#researchForm');
const researchTitle = document.querySelector('#researchTitle');
const fullText = document.querySelector('#fullText');
const researchMessage = document.querySelector('#researchMessage');
const recentArticles = document.querySelector('#recentArticles');
const refreshButton = document.querySelector('#refreshButton');
const articleCount = document.querySelector('#articleCount');
const statusText = document.querySelector('#statusText');
const statusDot = document.querySelector('.status-dot');

function showMessage(element, message, type = '') {
  element.textContent = message;
  element.className = `message ${type}`;
}

function articleCard(article) {
  const summary = article.summary || 'No summary available.';
  const clipped = summary.length > 120 ? `${summary.slice(0, 120)}...` : summary;
  return `<article class="article-card">
    <div><h3>${escapeHtml(article.title)}</h3><p>${escapeHtml(clipped)}</p></div>
    <div class="article-meta">${article.word_count || 0} words / ${escapeHtml(article.source || 'wikipedia')}</div>
  </article>`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#039;', '"': '&quot;'
  }[character]));
}

async function loadRecent() {
  try {
    const response = await fetch('/articles/recent?limit=9');
    const articles = await response.json();
    if (!response.ok) throw new Error(articles.error || 'Could not load articles.');
    articleCount.textContent = `${articles.length} SAVED`;
    recentArticles.className = articles.length ? 'library-grid' : 'library-grid empty-state';
    recentArticles.innerHTML = articles.length
      ? articles.map(articleCard).join('')
      : 'No saved articles yet. Research a page to begin.';
  } catch (error) {
    recentArticles.textContent = error.message;
  }
}

async function checkHealth() {
  try {
    const response = await fetch('/health');
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Offline');
    statusText.textContent = `${data.stored_articles} saved / database online`;
    statusDot.classList.add('online');
  } catch (error) {
    statusText.textContent = 'Database unavailable';
  }
}

searchForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const query = searchInput.value.trim();
  if (!query) return;
  searchResults.className = 'results empty-state';
  searchResults.textContent = 'Searching Wikipedia...';
  try {
    const response = await fetch(`/search?q=${encodeURIComponent(query)}&limit=6`);
    const results = await response.json();
    if (!response.ok) throw new Error(results.error || 'Search failed.');
    searchResults.className = 'results';
    searchResults.innerHTML = results.length
      ? results.map((result) => `<div class="result-item">
          <div><div class="result-title">${escapeHtml(result.title)}</div><div class="result-snippet">${escapeHtml(result.snippet || 'Wikipedia article')}</div></div>
          <button class="result-save" data-title="${escapeHtml(result.title)}" type="button">SAVE +</button>
        </div>`).join('')
      : '<div class="empty-state">No results found. Try a broader phrase.</div>';
    document.querySelectorAll('.result-save').forEach((button) => button.addEventListener('click', () => {
      researchTitle.value = button.dataset.title;
      researchTitle.focus();
      window.scrollTo({ top: researchForm.offsetTop - 40, behavior: 'smooth' });
    }));
  } catch (error) {
    searchResults.textContent = error.message;
  }
});

researchForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const title = researchTitle.value.trim();
  if (!title) return;
  showMessage(researchMessage, 'Fetching article and saving to Neon...');
  try {
    const response = await fetch('/research', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, full_text: fullText.checked })
    });
    const article = await response.json();
    if (!response.ok) throw new Error(article.error || 'Research failed.');
    showMessage(researchMessage, `Saved "${article.title}" to your library.`, 'success');
    researchTitle.value = '';
    fullText.checked = false;
    await loadRecent();
    await checkHealth();
  } catch (error) {
    showMessage(researchMessage, error.message, 'error');
  }
});

refreshButton.addEventListener('click', loadRecent);
checkHealth();
loadRecent();
