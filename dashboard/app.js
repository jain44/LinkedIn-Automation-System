/**
 * Jainam Jain - Tech Internship Outreach Automation Dashboard
 * Dynamic Client-Side Logic & Real-time Synchronization
 */

// State
const state = {
  activeTab: 'sent',
  searchQuery: '',
  roleFilter: 'all',
  autoRefresh: true,
  refreshIntervalMs: 5000,
  refreshTimer: null,
  data: {
    candidate: {
      full_name: 'Jainam Jain',
      cgpa: '9.92 / 10',
      college: 'TCET Mumbai',
      degree: 'B.Tech IT + Minor in AI, 2024-2028',
      email: 'jainamjain1116@gmail.com',
      linkedin: 'https://www.linkedin.com/in/jainam-jain-746188263',
      github: 'https://github.com/jain44'
    },
    metrics: {
      total_leads: 9,
      sent_emails: 7,
      commented_posts: 8,
      application_links: 0,
      pending_leads: 2,
      success_rate: '100%',
      engine_active: true,
      high_match_count: 9,
      last_updated: 'Just now'
    },
    leads: [],
    sent_log: [],
    commented_posts: [],
    application_links: [],
    recent_logs: []
  }
};

// DOM Elements
const el = {
  engineStatus: document.getElementById('engineStatus'),
  engineStatusText: document.getElementById('engineStatusText'),
  lastSyncTime: document.getElementById('lastSyncTime'),
  metricLeads: document.getElementById('metricLeads'),
  metricSent: document.getElementById('metricSent'),
  metricCommented: document.getElementById('metricCommented'),
  metricForms: document.getElementById('metricForms'),
  metricPending: document.getElementById('metricPending'),
  
  countSent: document.getElementById('countSent'),
  countLeads: document.getElementById('countLeads'),
  countCommented: document.getElementById('countCommented'),
  countForms: document.getElementById('countForms'),
  countLogs: document.getElementById('countLogs'),
  countDueReminders: document.getElementById('countDueReminders'),

  tbodySent: document.getElementById('tbodySent'),
  tbodyLeads: document.getElementById('tbodyLeads'),
  gridCommented: document.getElementById('gridCommented'),
  gridForms: document.getElementById('gridForms'),
  terminalLogs: document.getElementById('terminalLogs'),

  searchInput: document.getElementById('searchInput'),
  refreshBtn: document.getElementById('refreshBtn'),
  autoRefreshToggle: document.getElementById('autoRefreshToggle'),
  
  modalOverlay: document.getElementById('modalOverlay'),
  modalTitle: document.getElementById('modalTitle'),
  modalPreviewContent: document.getElementById('modalPreviewContent'),
  modalClose: document.getElementById('modalClose'),
  
  toastContainer: document.getElementById('toastContainer'),

  // Dispatcher elements
  dispEmail: document.getElementById('dispEmail'),
  dispPasteBtn: document.getElementById('dispPasteBtn'),
  dispOppSelect: document.getElementById('dispOppSelect'),
  dispCompany: document.getElementById('dispCompany'),
  dispRole: document.getElementById('dispRole'),
  dispRequirements: document.getElementById('dispRequirements'),
  dispOverview: document.getElementById('dispOverview'),
  dispApplyLink: document.getElementById('dispApplyLink'),
  dispSubject: document.getElementById('dispSubject'),
  dispPreviewBtn: document.getElementById('dispPreviewBtn'),
  dispSendBtn: document.getElementById('dispSendBtn'),
  dispPreviewSubject: document.getElementById('dispPreviewSubject'),
  dispPreviewFrame: document.getElementById('dispPreviewFrame')
};

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
  setupEventListeners();
  fetchStats();
  startAutoRefresh();
});

// Setup Events
function setupEventListeners() {
  // Tabs
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const tabId = btn.getAttribute('data-tab');
      switchTab(tabId);
    });
  });

  // Filter Pills
  document.querySelectorAll('.filter-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      document.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      state.roleFilter = pill.getAttribute('data-filter') || 'all';
      renderAll();
    });
  });

  // Search input
  el.searchInput.addEventListener('input', (e) => {
    state.searchQuery = e.target.value.trim().toLowerCase();
    renderAll();
  });

  // Manual Refresh
  el.refreshBtn.addEventListener('click', () => {
    showToast('Refreshing outreach analytics...', 'info');
    fetchStats();
  });

  // Auto Refresh Toggle
  el.autoRefreshToggle.addEventListener('click', () => {
    state.autoRefresh = !state.autoRefresh;
    if (state.autoRefresh) {
      el.autoRefreshToggle.innerText = '⚡ Auto-Sync: ON (5s)';
      el.autoRefreshToggle.classList.add('highlight');
      startAutoRefresh();
      showToast('Live Auto-Sync Enabled', 'success');
    } else {
      el.autoRefreshToggle.innerText = '⏸️ Auto-Sync: OFF';
      el.autoRefreshToggle.classList.remove('highlight');
      clearInterval(state.refreshTimer);
      showToast('Auto-Sync Paused', 'info');
    }
  });

  // Modal Close
  el.modalClose.addEventListener('click', closeModal);
  el.modalOverlay.addEventListener('click', (e) => {
    if (e.target === el.modalOverlay) closeModal();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
  });

  // Dispatcher Events
  if (el.dispPasteBtn) {
    el.dispPasteBtn.addEventListener('click', async () => {
      try {
        const text = await navigator.clipboard.readText();
        if (text) {
          el.dispEmail.value = text.trim();
          showToast(`Pasted email: ${text.trim()}`, 'success');
          updateDispatcherPreview();
        }
      } catch (err) {
        showToast('Please paste manually using Ctrl+V', 'info');
      }
    });
  }

  if (el.dispOppSelect) {
    el.dispOppSelect.addEventListener('change', () => {
      const val = el.dispOppSelect.value;
      if (val !== '') {
        const idx = parseInt(val, 10);
        loadDispatcherOpportunity(idx);
      }
    });
  }

  if (el.dispPreviewBtn) {
    el.dispPreviewBtn.addEventListener('click', updateDispatcherPreview);
  }

  if (el.dispSendBtn) {
    el.dispSendBtn.addEventListener('click', dispatchCustomEmail);
  }

  // Live input preview triggers
  [el.dispEmail, el.dispRole, el.dispCompany, el.dispSubject].forEach(input => {
    if (input) {
      input.addEventListener('input', debounce(updateDispatcherPreview, 600));
    }
  });
}

function switchTab(tabId) {
  state.activeTab = tabId;
  document.querySelectorAll('.tab-btn').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-tab') === tabId);
  });
  document.querySelectorAll('.tab-content').forEach(c => {
    c.classList.toggle('active', c.id === `tab-${tabId}`);
  });
}

// Fetch stats from server
async function fetchStats() {
  try {
    const res = await fetch('/api/stats');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json();
    state.data = json;
    updateUIWithData();
  } catch (err) {
    // If running via file:// or server not yet started, attempt localhost port 5050
    if (window.location.protocol === 'file:') {
      try {
        const fallbackRes = await fetch('http://127.0.0.1:5050/api/stats');
        const fallbackJson = await fallbackRes.json();
        state.data = fallbackJson;
        updateUIWithData();
        return;
      } catch (e) {
        console.warn('Dashboard server not reachable at http://127.0.0.1:5050 - using cached state.');
      }
    }
    updateUIWithData();
  }
}

function startAutoRefresh() {
  clearInterval(state.refreshTimer);
  state.refreshTimer = setInterval(() => {
    if (state.autoRefresh) {
      fetchStats();
    }
  }, state.refreshIntervalMs);
}

// Update UI
function updateUIWithData() {
  const { metrics } = state.data;

  // Engine Status
  if (metrics.engine_active) {
    el.engineStatus.classList.remove('idle');
    el.engineStatusText.innerText = 'Engine Active: Scraping LinkedIn & Engaging';
  } else {
    el.engineStatus.classList.add('idle');
    el.engineStatusText.innerText = 'Engine Standby';
  }

  // Counters
  el.metricLeads.innerText = metrics.total_leads || 0;
  el.metricSent.innerText = metrics.sent_emails || 0;
  el.metricCommented.innerText = metrics.commented_posts || 0;
  el.metricForms.innerText = metrics.application_links || 0;
  el.metricPending.innerText = metrics.pending_leads || 0;

  el.countSent.innerText = metrics.sent_emails || 0;
  el.countLeads.innerText = metrics.total_leads || 0;
  el.countCommented.innerText = metrics.commented_posts || 0;
  el.countForms.innerText = metrics.application_links || 0;
  el.countLogs.innerText = (state.data.recent_logs || []).length;
  if (el.countDueReminders) el.countDueReminders.innerText = metrics.due_reminders || 0;

  el.lastSyncTime.innerText = metrics.last_updated || new Date().toLocaleTimeString();

  renderAll();
}

function renderAll() {
  renderSentTable();
  renderLeadsTable();
  renderCommentedGrid();
  renderFormsGrid();
  renderLogs();
  populateDispatcherSelect();
}

// Matches filter & query
function matchesFilter(item) {
  const q = state.searchQuery;
  const f = state.roleFilter;

  // Role filter check
  if (f !== 'all') {
    const roleText = (item.job_role || item.role || '').toLowerCase();
    const statusText = (item.status || '').toLowerCase();

    if (f === 'genai' && !roleText.includes('genai') && !roleText.includes('ai') && !roleText.includes('llm')) return false;
    if (f === 'fullstack' && !roleText.includes('full stack') && !roleText.includes('mern') && !roleText.includes('software')) return false;
    if (f === 'backend' && !roleText.includes('backend') && !roleText.includes('python') && !roleText.includes('java')) return false;
    if (f === 'pending' && statusText !== 'pending') return false;
    if (f === 'sent' && statusText !== 'sent') return false;
  }

  // Text search query
  if (!q) return true;
  const combined = Object.values(item).join(' ').toLowerCase();
  return combined.includes(q);
}

// Convert plain URLs inside text to clickable HTML links
function linkifyText(text) {
  if (!text) return '';
  const escaped = escapeHtml(text);
  return escaped.replace(/(https?:\/\/[^\s<>"']+)/g, '<a href="$1" target="_blank" rel="noopener" style="color: var(--cyan-light); text-decoration: underline; font-weight: 500;">$1</a>');
}

// Link Resolver for Saved Posts & Leads
function resolvePostLinks(post) {
  let directUrl = (post.post_url || '').trim();
  const text = post.post_snippet || '';
  
  // Extract all URLs mentioned in the text (http/https)
  const urlRegex = /(https?:\/\/[^\s<>"']+)/gi;
  const extractedUrls = [];
  let match;
  while ((match = urlRegex.exec(text)) !== null) {
    let u = match[1].replace(/[.,;!]+$/, ''); // clean trailing punctuation
    if (!extractedUrls.includes(u)) {
      extractedUrls.push(u);
    }
  }

  // If directUrl is empty, check if one of the extracted URLs is a LinkedIn post/activity/lnkd.in link
  if (!directUrl && extractedUrls.length > 0) {
    const lnk = extractedUrls.find(u => u.includes('linkedin.com') || u.includes('lnkd.in'));
    if (lnk) {
      directUrl = lnk;
    }
  }

  // Create a 1-click targeted LinkedIn search URL for author + role / key phrase
  const author = (post.recruiter_name || '').replace(/Feed post/gi, '').replace(/\b(?:3rd\+|2nd|1st)\b/gi, '').trim();
  const cleanSnippet = text
    .replace(/Feed post/gi, '')
    .replace(author, '')
    .replace(/\b\d+\s*[hdwm]\b/gi, '')
    .replace(/\bFollow\b/gi, '')
    .replace(/WE'RE HIRING/gi, '')
    .replace(/Hiring/gi, '')
    .trim();
  const firstWords = cleanSnippet.replace(/[^\w\s]/gi, ' ').split(/\s+/).filter(w => w.length > 2).slice(0, 5).join(' ');
  const searchQuery = [author, firstWords].filter(Boolean).join(' ').trim();
  const searchUrl = `https://www.linkedin.com/search/results/content/?keywords=${encodeURIComponent(searchQuery || author || 'intern developer')}&sortBy=%22date_posted%22`;

  return {
    directUrl,
    extractedUrls,
    searchUrl,
    searchQuery
  };
}

// Open Full Post Reader Modal
function openFullPostModal(sourceType, index) {
  let item = null;
  if (sourceType === 'commented') {
    item = (state.data.commented_posts || [])[index];
  } else if (sourceType === 'lead') {
    item = (state.data.leads || [])[index];
  } else if (sourceType === 'sent') {
    item = (state.data.sent_log || [])[index];
  }

  if (!item) return;

  const links = resolvePostLinks(item);
  const author = item.recruiter_name || item.company_name || 'Hiring Author';
  const role = item.job_role || 'Developer Opportunity';
  const timeStr = item.commented_at || item.discovered_at || item.sent_at || 'Recently';
  const rawSnippet = item.post_snippet || 'No post content recorded.';
  const linkedSnippet = linkifyText(rawSnippet);
  const suggestedComment = "Interested! 🙌 Please share the application link / details. Thank you!";

  el.modalTitle.innerText = `📄 Post Review: ${author}`;
  el.modalPreviewContent.className = "modal-post-reader";
  el.modalPreviewContent.innerHTML = `
    <div class="post-reader-container">
      <div class="post-reader-header">
        <div>
          <h4 style="margin: 0; font-size: 17px; color: #ffffff; display: flex; align-items: center; gap: 8px;">
            👤 ${escapeHtml(author)}
            ${item.job_role ? `<span class="role-badge" style="font-size: 11px;">${escapeHtml(item.job_role)}</span>` : ''}
          </h4>
          <div style="font-size: 12px; color: var(--text-dim); margin-top: 4px;">
            🕒 Discovered / Tracked: ${escapeHtml(timeStr)}
          </div>
        </div>
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
          ${links.directUrl ? `
            <a href="${escapeHtml(links.directUrl)}" target="_blank" rel="noopener" class="action-btn-sm" style="background: var(--primary); color: #fff; text-decoration: none; padding: 6px 14px; font-size: 12.5px;">
              🔗 Open Directly on LinkedIn
            </a>
          ` : `
            <a href="${escapeHtml(links.searchUrl)}" target="_blank" rel="noopener" class="action-btn-sm" style="background: linear-gradient(135deg, #0284c7, #0369a1); color: #fff; text-decoration: none; padding: 6px 14px; font-size: 12.5px;">
              🔍 Find Post on LinkedIn
            </a>
          `}
        </div>
      </div>

      ${links.extractedUrls.length > 0 ? `
        <div class="post-reader-links-box">
          <div style="font-size: 11px; text-transform: uppercase; font-weight: 700; color: var(--emerald-light); margin-bottom: 6px;">
            🚀 Extracted Application / Job Links (${links.extractedUrls.length})
          </div>
          <div style="display: flex; flex-direction: column; gap: 6px;">
            ${links.extractedUrls.map(u => `
              <div style="display: flex; align-items: center; gap: 8px;">
                <a href="${escapeHtml(u)}" target="_blank" rel="noopener" class="action-btn-sm" style="background: rgba(16, 185, 129, 0.2); border-color: rgba(16, 185, 129, 0.5); color: var(--emerald-light); text-decoration: none;">
                  🌐 Open Link: ${escapeHtml(u.length > 45 ? u.substring(0, 42) + '...' : u)}
                </a>
                <button class="copy-btn" title="Copy Link" onclick="copyToClipboard('${escapeHtml(u)}')">📋</button>
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}

      <div class="post-reader-content">
        <div style="font-size: 11px; text-transform: uppercase; font-weight: 700; color: var(--text-dim); margin-bottom: 8px;">
          📝 Full Post Text
        </div>
        <div class="post-raw-text">
          ${linkedSnippet}
        </div>
      </div>

      <div class="post-reader-actions">
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
          <button class="action-btn-sm" onclick="copyToClipboard('${escapeHtml(rawSnippet).replace(/'/g, "\\'")}')">
            📋 Copy Entire Post Text
          </button>
          <button class="action-btn-sm" onclick="copyToClipboard('${escapeHtml(suggestedComment)}')">
            💬 Copy Suggested Comment
          </button>
          ${item.email ? `
            <button class="action-btn-sm" style="background: rgba(99, 102, 241, 0.2); border-color: rgba(99, 102, 241, 0.5); color: var(--primary-light);" onclick="prefillDispatcherAndSwitch('${escapeHtml(item.email)}', '${escapeHtml(author)}', '${escapeHtml(role)}')">
              ✉️ Send Custom Outreach
            </button>
          ` : ''}
        </div>
      </div>
    </div>
  `;
  el.modalOverlay.classList.add('active');
}

function prefillDispatcherAndSwitch(email, recruiter, role) {
  closeModal();
  switchTab('dispatcher');
  if (el.dispEmail) el.dispEmail.value = email || '';
  if (el.dispCompany) el.dispCompany.value = recruiter || '';
  if (el.dispRole) el.dispRole.value = role || '';
  updateDispatcherPreview();
  showToast(`Loaded outreach details for ${email}`, 'info');
}


// 1. Sent Outreach Log
function renderSentTable() {
  const items = (state.data.sent_log || []).filter(matchesFilter);
  if (!items.length) {
    el.tbodySent.innerHTML = `<tr><td colspan="6" class="empty-state">
      <div class="empty-state-icon">📬</div>
      <div class="empty-state-title">No sent emails match your filter</div>
      <div>Delivered cold emails will be logged here automatically.</div>
    </td></tr>`;
    return;
  }

  el.tbodySent.innerHTML = items.map((r, i) => {
    const hasPhone = Boolean(r.phone_number && r.phone_number.trim());
    const waLink = r.whatsapp_link || (hasPhone ? `https://wa.me/${r.phone_number.replace(/\D/g, '')}` : '');
    return `
    <tr>
      <td>
        <div class="recruiter-cell">
          <span class="recruiter-name">${escapeHtml(r.recruiter_name || 'Hiring Team')}</span>
          <span class="recruiter-sub">${escapeHtml(r.email)}</span>
          ${hasPhone ? `
            <div style="margin-top: 5px; display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
              <span class="phone-pill" style="font-size: 11px;">📱 ${escapeHtml(r.phone_number)}</span>
              <button class="copy-btn" title="Copy Phone Number" onclick="copyToClipboard('${escapeHtml(r.phone_number)}')">📋</button>
              ${waLink ? `
                <a href="${escapeHtml(waLink)}" target="_blank" rel="noopener" class="whatsapp-btn-sm" style="font-size: 11px; padding: 2px 7px;">
                  💬 WhatsApp
                </a>
              ` : ''}
            </div>
          ` : ''}
        </div>
      </td>
      <td>
        <span class="role-badge ${getRoleBadgeClass(r.job_role)}">${escapeHtml(r.job_role || 'Developer Intern')}</span>
      </td>
      <td style="max-width: 320px; font-weight: 500;">
        ${escapeHtml(r.subject || 'Application for Developer Intern')}
      </td>
      <td style="font-family: var(--font-mono); font-size: 12px; color: var(--text-dim); white-space: nowrap;">
        ${escapeHtml(r.sent_at || '-')}
      </td>
      <td>
        <span class="status-badge sent">🚀 Delivered</span>
      </td>
      <td>
        <div style="display: flex; gap: 6px; flex-wrap: wrap;">
          <button class="action-btn-sm" onclick="previewEmail('${escapeHtml(r.email)}')">
            👁️ Preview Email
          </button>
          <button class="action-btn-sm" onclick="openFullPostModal('sent', ${i})" title="View original LinkedIn post snippet">
            📄 View Post
          </button>
        </div>
      </td>
    </tr>
  `}).join('');
}

// 2. Discovered Email Leads
function renderLeadsTable() {
  const items = (state.data.leads || []).filter(matchesFilter);
  if (!items.length) {
    el.tbodyLeads.innerHTML = `<tr><td colspan="7" class="empty-state">
      <div class="empty-state-icon">🎯</div>
      <div class="empty-state-title">No leads match your filter</div>
      <div>New leads parsed from LinkedIn will appear here.</div>
    </td></tr>`;
    return;
  }

  el.tbodyLeads.innerHTML = items.map((r, i) => {
    const isSent = r.status === 'sent';
    const isWhatsAppPending = r.status === 'whatsapp_pending';
    const scoreVal = parseInt(r.score) || 100;
    const hasEmail = Boolean(r.email && r.email.trim());
    const hasPhone = Boolean(r.phone_number && r.phone_number.trim());
    const waLink = r.whatsapp_link || (hasPhone ? `https://wa.me/${r.phone_number.replace(/\D/g, '')}` : '');

    return `
      <tr>
        <td>
          <div class="recruiter-cell">
            <span class="recruiter-name">${escapeHtml(r.recruiter_name || 'Recruiter')}</span>
            <span class="recruiter-sub">${escapeHtml(r.search_keyword || 'LinkedIn Search')}</span>
          </div>
        </td>
        <td>
          <div class="contact-info-stack">
            ${hasEmail ? `
              <div class="contact-email-row">
                <span style="font-family: var(--font-mono); font-size: 13px; color: var(--cyan-light);">
                  ${escapeHtml(r.email)}
                </span>
                <button class="copy-btn" title="Copy Email" onclick="copyToClipboard('${escapeHtml(r.email)}')">
                  📋
                </button>
              </div>
            ` : ''}
            ${hasPhone ? `
              <div class="contact-phone-row">
                <span class="phone-pill">
                  📱 ${escapeHtml(r.phone_number)}
                </span>
                <button class="copy-btn" title="Copy Phone Number" onclick="copyToClipboard('${escapeHtml(r.phone_number)}')">
                  📋
                </button>
                ${waLink ? `
                  <a href="${escapeHtml(waLink)}" target="_blank" rel="noopener" class="whatsapp-btn-sm" title="Chat on WhatsApp">
                    💬 WhatsApp
                  </a>
                ` : ''}
              </div>
            ` : ''}
            ${!hasEmail && !hasPhone ? `<span style="color: var(--text-dim); font-size: 12px;">No direct contact</span>` : ''}
          </div>
        </td>
        <td>
          <span class="role-badge ${getRoleBadgeClass(r.job_role)}">${escapeHtml(r.job_role || 'Developer Intern')}</span>
        </td>
        <td>
          <div class="score-badge">
            <span class="score-pill">${scoreVal}% Match</span>
          </div>
        </td>
        <td style="font-family: var(--font-mono); font-size: 12px; color: var(--text-dim); white-space: nowrap;">
          ${escapeHtml((r.discovered_at || '').substring(0, 16))}
        </td>
        <td>
          <span class="status-badge ${isSent ? 'sent' : (isWhatsAppPending ? 'applied' : 'pending')}">
            ${isSent ? 'Delivered' : (isWhatsAppPending ? '📱 WhatsApp Ready' : 'Pending Send')}
          </span>
        </td>
        <td>
          <div style="display: flex; gap: 6px; flex-wrap: wrap;">
            ${hasEmail ? `
              <button class="action-btn-sm" onclick="previewEmail('${escapeHtml(r.email)}')">
                Preview
              </button>
              ${!isSent ? `
                <button class="action-btn-sm" style="background: rgba(16, 185, 129, 0.15); border-color: rgba(16, 185, 129, 0.4); color: var(--emerald-light);" onclick="triggerSendSingle('${escapeHtml(r.email)}')">
                  🚀 Send
                </button>
              ` : ''}
            ` : ''}
            <button class="action-btn-sm" onclick="openFullPostModal('lead', ${i})" title="View original LinkedIn post snippet & recruiter details">
              📄 View Post
            </button>
            ${waLink ? `
              <a href="${escapeHtml(waLink)}" target="_blank" rel="noopener" class="whatsapp-btn-sm" style="font-size: 11px;">
                💬 Message
              </a>
            ` : ''}
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

// 3. Saved Posts for Manual Review & Engagement
function renderCommentedGrid() {
  const items = (state.data.commented_posts || []).filter(matchesFilter);
  if (!items.length) {
    el.gridCommented.innerHTML = `<div class="empty-state" style="grid-column: 1 / -1;">
      <div class="empty-state-icon">📌</div>
      <div class="empty-state-title">No saved posts match your filter</div>
      <div>Relevant internship posts discovered during scraping will be saved here for you to review and engage with at your convenience.</div>
    </div>`;
    return;
  }

  el.gridCommented.innerHTML = items.map((post, i) => {
    const links = resolvePostLinks(post);
    const suggestedComment = "Interested! 🙌 Please share the application link / details. Thank you!";
    const snippetHtml = linkifyText(post.post_snippet || 'LinkedIn internship post');

    return `
      <div class="activity-card" style="border-top: 2px solid var(--primary);">
        <div>
          <div class="activity-card-header">
            <div>
              <div class="activity-author">👤 ${escapeHtml(post.recruiter_name || 'Hiring Author')}</div>
              <div class="activity-time">🕒 ${escapeHtml(post.commented_at || post.discovered_at || '-')}</div>
            </div>
            <span class="meta-pill" style="font-size: 11px; background: rgba(99, 102, 241, 0.15); color: var(--primary-light); border-color: rgba(99, 102, 241, 0.3);">
              📌 Saved for Review
            </span>
          </div>
          <div class="activity-snippet">
            ${snippetHtml}
          </div>
          <div class="comment-bubble" style="background: rgba(13, 21, 39, 0.6); border: 1px solid var(--border-subtle); padding: 10px 12px; border-radius: 6px; margin-top: 10px;">
            <div style="font-size: 11px; color: var(--text-dim); text-transform: uppercase; font-weight: 600; margin-bottom: 4px;">💡 Suggested Comment (Copy & Paste Manually):</div>
            <span style="font-size: 12.5px; color: var(--cyan-light);">"${escapeHtml(suggestedComment)}"</span>
          </div>
        </div>
        <div class="activity-footer" style="margin-top: 14px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
          <div style="display: flex; gap: 6px; flex-wrap: wrap; align-items: center;">
            <button class="action-btn-sm" style="background: rgba(99, 102, 241, 0.25); border-color: rgba(99, 102, 241, 0.5); color: #c7d2fe;" onclick="openFullPostModal('commented', ${i})">
              👁️ View Full Post
            </button>
            ${links.directUrl ? `
              <a href="${escapeHtml(links.directUrl)}" target="_blank" rel="noopener" class="action-btn-sm" style="background: var(--primary); color: #fff; text-decoration: none;">
                🔗 Open on LinkedIn
              </a>
              <button class="copy-btn" title="Copy LinkedIn Post Link" onclick="copyToClipboard('${escapeHtml(links.directUrl)}')">📋</button>
            ` : `
              <a href="${escapeHtml(links.searchUrl)}" target="_blank" rel="noopener" class="action-btn-sm" style="background: rgba(14, 165, 233, 0.2); border-color: rgba(14, 165, 233, 0.5); color: var(--cyan-light); text-decoration: none;" title="Find on LinkedIn: ${escapeHtml(links.searchQuery)}">
                🔍 Find Post on LinkedIn
              </a>
            `}
            ${links.extractedUrls.length > 0 ? `
              <a href="${escapeHtml(links.extractedUrls[0])}" target="_blank" rel="noopener" class="action-btn-sm" style="background: rgba(16, 185, 129, 0.2); border-color: rgba(16, 185, 129, 0.5); color: var(--emerald-light); text-decoration: none;" title="Open Extracted Apply Link">
                🚀 Open Apply Link
              </a>
            ` : ''}
            <button class="action-btn-sm" onclick="copyToClipboard('${escapeHtml(suggestedComment)}')">
              💬 Copy Comment
            </button>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

// 4. Application Links & Google Forms
function renderFormsGrid() {
  const items = (state.data.application_links || []).filter(matchesFilter);
  if (!items.length) {
    el.gridForms.innerHTML = `<div class="empty-state" style="grid-column: 1 / -1;">
      <div class="empty-state-icon">📋</div>
      <div class="empty-state-title">No application forms saved yet</div>
      <div style="max-width: 500px; margin: 0 auto; font-size: 13.5px;">
        As the engine searches keywords like <code>forms gle intern developer</code> and <code>apply link software intern</code>, 
        direct Google Forms, Notion pages, and job application links will populate here automatically with structured company overviews, roles, and requirements!
      </div>
    </div>`;
    return;
  }

  state.currentForms = items;

  el.gridForms.innerHTML = items.map((link, idx) => {
    const isApplied = link.status === 'applied';
    const company = link.company_name || link.recruiter_name || 'Tech Company';
    const role = link.job_role || 'Software Engineer Intern';
    const overview = link.overview || 'Internship opportunity for software engineering and technical roles.';
    const requirements = link.requirements || 'Full-stack development, software engineering, and technical problem-solving.';
    const postUrl = link.post_url || '';

    return `
      <div class="opp-card" id="opp-card-${idx}" style="border-top: 3px solid ${isApplied ? 'var(--cyan)' : 'var(--amber)'};">
        <div>
          <div class="activity-card-header">
            <div>
              <div class="opp-company-badge">🏢 ${escapeHtml(company)}</div>
              <div class="opp-role-title">${escapeHtml(role)}</div>
              <div class="activity-time" style="margin-top: 4px;">
                👤 ${escapeHtml(link.recruiter_name || 'Hiring Team')} • 🕒 ${escapeHtml((link.discovered_at || '').substring(0, 16))}
              </div>
            </div>
            <span class="status-badge ${isApplied ? 'applied' : 'pending'}" id="status-badge-${idx}">
              ${isApplied ? 'Applied ✓' : 'New Opportunity'}
            </span>
          </div>

          <div style="margin-bottom: 12px;">
            <div class="opp-section-title">💡 What the Internship is About:</div>
            <div class="opp-overview-box">
              ${escapeHtml(overview)}
            </div>
          </div>

          <div>
            <div class="opp-section-title">🛠️ Requirements & Key Details:</div>
            <div class="opp-req-box">
              ${escapeHtml(requirements)}
            </div>
          </div>

          <!-- Quick Email Dispatcher Bar -->
          <div class="quick-email-bar">
            <div class="quick-email-label">
              <span>✉️ Found Recruiter / Contact Email?</span>
              <span style="font-size: 10px; color: var(--text-dim); text-transform: none;">Auto-crafts tailored mail & attaches resume</span>
            </div>
            <div class="quick-email-row">
              <input type="email" id="quick-email-${idx}" class="quick-email-input" placeholder="Paste recruiter email (e.g. hr@${company.toLowerCase().replace(/[^a-z0-9]/g, '') || 'company'}.com)...">
              <button type="button" class="btn-quick-send" id="btn-quick-send-${idx}" onclick="quickSendOpportunity(${idx})">
                🚀 Send Mail
              </button>
              <button type="button" class="action-btn-sm" onclick="quickPreviewOpportunity(${idx})">
                👁️ Preview
              </button>
              <button type="button" class="action-btn-sm" onclick="openInDispatcher(${idx})" title="Open full details in Direct Mail Dispatcher">
                ⚡ Dispatcher
              </button>
            </div>
          </div>
        </div>

        <div class="activity-footer">
          <div style="display: flex; gap: 8px; flex-wrap: wrap;">
            <a href="${escapeHtml(link.apply_link)}" target="_blank" rel="noopener" class="opp-btn-apply">
              👉 Apply Now
            </a>
            ${postUrl ? `
              <a href="${escapeHtml(postUrl)}" target="_blank" rel="noopener" class="action-btn-sm">
                🔗 View Post
              </a>
            ` : ''}
            <button class="action-btn-sm" onclick="copyToClipboard('${escapeHtml(link.apply_link)}')">
              📋 Copy Link
            </button>
          </div>
          <button class="action-btn-sm" onclick="toggleLinkStatus('${escapeHtml(link.apply_link)}', '${isApplied ? 'new' : 'applied'}')">
            ${isApplied ? 'Mark New' : '✓ Mark Applied'}
          </button>
        </div>
      </div>
    `;
  }).join('');
}


// 5. Logs
function renderLogs() {
  const logs = state.data.recent_logs || [];
  if (!logs.length) {
    el.terminalLogs.innerHTML = '<div style="color: #64748b;">Waiting for engine activity stream...</div>';
    return;
  }

  el.terminalLogs.innerHTML = logs.map(line => {
    let cls = '';
    if (line.includes('[WARNING]')) cls = 'log-warn';
    else if (line.includes('✨ Found Lead')) cls = 'log-lead';
    else if (line.includes('💬 Auto-commented') || line.includes('✅')) cls = 'log-success';
    else if (line.includes('[INFO]')) cls = 'log-info';

    return `<div class="log-line ${cls}">${escapeHtml(line)}</div>`;
  }).join('');

  // Auto-scroll to bottom of terminal
  el.terminalLogs.scrollTop = el.terminalLogs.scrollHeight;
}

// Helper: Badge Classes
function getRoleBadgeClass(role) {
  const r = (role || '').toLowerCase();
  if (r.includes('genai') || r.includes('ai') || r.includes('llm')) return 'genai';
  if (r.includes('full stack') || r.includes('mern')) return 'fullstack';
  return '';
}

// Email Preview Modal
async function previewEmail(email) {
  el.modalTitle.innerText = `Outreach Preview: ${email}`;
  el.modalPreviewContent.className = "modal-preview-frame";
  el.modalPreviewContent.innerHTML = `<div style="text-align: center; padding: 40px; color: #64748b;">Rendering email template...</div>`;
  el.modalOverlay.classList.add('active');

  try {
    const res = await fetch(`/api/email_preview?email=${encodeURIComponent(email)}`);
    if (res.ok) {
      const html = await res.text();
      el.modalPreviewContent.innerHTML = html;
      return;
    }
  } catch (err) {
    console.warn('API error, falling back to local render:', err);
  }

  // Fallback content if standalone
  el.modalPreviewContent.innerHTML = `
    <div style="font-family: sans-serif; line-height: 1.6; color: #1e293b;">
      <p>Dear Hiring Team,</p>
      <p>I came across your posting for the Developer Intern position. With 1+ Year of hands-on experience building production full-stack systems and autonomous AI agents, my background in React, Next.js, Node.js, FastAPI, and LangGraph aligns directly with what you are looking for.</p>
      <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-left: 4px solid #0a66c2; border-radius: 6px; padding: 16px; margin: 16px 0;">
        <strong style="color: #0a66c2;">--- SUBMISSION DETAILS ---</strong><br>
        • Candidate Name: Jainam Jain<br>
        • Education: B.Tech IT + Minor in AI, TCET Mumbai (CGPA: 9.92 / 10)<br>
        • Total Experience: 1+ Year (3 internships + 2 live production systems)<br>
        • Primary Tech Stack: React, Next.js, Node.js, Python, FastAPI, Docker, LangGraph<br>
        • Key Projects: JusticeAI (Groq/Node Legal AI), Kavach (FastAPI ML AUC 0.74), GrowthOS (7 AI Agents)<br>
        • Availability: Immediate (Full-time or Part-time)
      </div>
      <p>I have attached my updated 1-page resume for your review. Are you available for a brief 10–15 minute call sometime this week?</p>
      <p>Best regards,<br><strong>Jainam Jain</strong><br>jainamjain1116@gmail.com | +91 79779 63474</p>
    </div>
  `;
}

function closeModal() {
  el.modalOverlay.classList.remove('active');
}

// Copy to Clipboard
function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    showToast(`Copied to clipboard: ${text}`, 'success');
  }).catch(() => {
    showToast('Failed to copy', 'error');
  });
}

// Toggle link status
async function toggleLinkStatus(applyLink, newStatus) {
  try {
    const res = await fetch('/api/links/status', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ apply_link: applyLink, status: newStatus })
    });
    if (res.ok) {
      showToast(`Opportunity marked as ${newStatus}`, 'success');
      fetchStats();
    }
  } catch (e) {
    showToast('Updated locally', 'info');
  }
}

// Trigger single send
async function triggerSendSingle(email) {
  showToast(`Initiating outreach sequence for ${email}...`, 'info');
  try {
    const res = await fetch('/api/trigger_send', { method: 'POST' });
    if (res.ok) {
      showToast('Email outreach process launched in background!', 'success');
    }
  } catch (e) {
    showToast('Run "python send_emails.py --send" in terminal', 'info');
  }
}

// Toast
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = 'toast';
  
  let icon = 'ℹ️';
  if (type === 'success') icon = '✅';
  if (type === 'error') icon = '❌';

  toast.innerHTML = `<span>${icon}</span><span>${escapeHtml(message)}</span>`;
  el.toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(40px)';
    toast.style.transition = 'all 0.25s ease';
    setTimeout(() => toast.remove(), 250);
  }, 3200);
}

// Utility: HTML Escaper
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// ==========================================================================
// DIRECT MAIL DISPATCHER & OPPORTUNITY QUICK-SEND FUNCTIONS
// ==========================================================================

// Populate dropdown of opportunities
function populateDispatcherSelect() {
  if (!el.dispOppSelect) return;
  const currentVal = el.dispOppSelect.value;
  const items = state.data.application_links || [];

  let html = '<option value="">-- Select an opportunity to auto-fill or enter custom below --</option>';
  items.forEach((link, idx) => {
    const comp = link.company_name || link.recruiter_name || 'Tech Company';
    const role = link.job_role || 'Software Engineer Intern';
    const status = link.status === 'applied' ? '✓ Applied' : 'New';
    html += `<option value="${idx}">[${status}] ${escapeHtml(comp)} — ${escapeHtml(role)}</option>`;
  });
  html += '<option value="custom">✨ Custom / Unlisted Opportunity</option>';
  el.dispOppSelect.innerHTML = html;

  if (currentVal && el.dispOppSelect.querySelector(`option[value="${currentVal}"]`)) {
    el.dispOppSelect.value = currentVal;
  }
}

// Load opportunity into Dispatcher Form
window.loadDispatcherOpportunity = function(idx) {
  if (idx === 'custom') {
    if (el.dispCompany) el.dispCompany.value = '';
    if (el.dispRole) el.dispRole.value = 'Full Stack & GenAI Developer Intern';
    if (el.dispRequirements) el.dispRequirements.value = 'React, Next.js, Node.js, Python, FastAPI, TypeScript, AI';
    if (el.dispOverview) el.dispOverview.value = '';
    if (el.dispApplyLink) el.dispApplyLink.value = '';
    updateDispatcherPreview();
    return;
  }

  const items = state.data.application_links || [];
  const link = items[idx];
  if (!link) return;

  if (el.dispCompany) el.dispCompany.value = link.company_name || link.recruiter_name || '';
  if (el.dispRole) el.dispRole.value = link.job_role || 'Software Engineer Intern';
  if (el.dispRequirements) el.dispRequirements.value = link.requirements || '';
  if (el.dispOverview) el.dispOverview.value = link.overview || '';
  if (el.dispApplyLink) el.dispApplyLink.value = link.apply_link || '';

  showToast(`Loaded details for ${link.company_name || 'opportunity'}`, 'info');
  updateDispatcherPreview();
};

// Switch to dispatcher tab and load opportunity
window.openInDispatcher = function(idx) {
  const item = state.currentForms && state.currentForms[idx];
  if (!item) return;

  switchTab('dispatcher');
  if (el.dispOppSelect) {
    el.dispOppSelect.value = String(idx);
  }
  loadDispatcherOpportunity(idx);

  const cardInput = document.getElementById(`quick-email-${idx}`);
  if (cardInput && cardInput.value.trim() && el.dispEmail) {
    el.dispEmail.value = cardInput.value.trim();
  }
  if (el.dispEmail) el.dispEmail.focus();
};

// Quick send directly from an opportunity card
window.quickSendOpportunity = async function(idx) {
  const item = state.currentForms && state.currentForms[idx];
  if (!item) return;

  const emailInput = document.getElementById(`quick-email-${idx}`);
  const email = emailInput ? emailInput.value.trim() : '';
  const btn = document.getElementById(`btn-quick-send-${idx}`);

  if (!email || !email.includes('@') || !email.includes('.')) {
    showToast('Please enter a valid recruiter email address.', 'error');
    if (emailInput) emailInput.focus();
    return;
  }

  const origText = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '⏳ Sending...';
  }

  try {
    const payload = {
      email: email,
      company_name: item.company_name || item.recruiter_name || '',
      recruiter_name: item.recruiter_name || item.company_name || 'Hiring Team',
      job_role: item.job_role || 'Software Engineer Intern',
      overview: item.overview || '',
      requirements: item.requirements || '',
      apply_link: item.apply_link || '',
      post_url: item.post_url || item.apply_link || ''
    };

    const res = await fetch('/api/send_custom_email', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (data.success) {
      showToast(`🎉 Tailored application + resume sent to ${email}!`, 'success');
      const badge = document.getElementById(`status-badge-${idx}`);
      if (badge) {
        badge.className = 'status-badge applied';
        badge.innerText = 'Applied ✓';
      }
      const card = document.getElementById(`opp-card-${idx}`);
      if (card) card.style.borderTop = '3px solid var(--cyan)';
      if (emailInput) emailInput.value = '';
      fetchStats();
    } else {
      showToast(data.error || 'Failed to send email.', 'error');
    }
  } catch (err) {
    showToast('Network error while dispatching: ' + err.message, 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origText;
    }
  }
};

// Quick preview directly from opportunity card
window.quickPreviewOpportunity = async function(idx) {
  const item = state.currentForms && state.currentForms[idx];
  if (!item) return;

  const emailInput = document.getElementById(`quick-email-${idx}`);
  const email = emailInput ? emailInput.value.trim() : '';

  const payload = {
    email: email || 'recruiter@company.com',
    company_name: item.company_name || item.recruiter_name || '',
    recruiter_name: item.recruiter_name || item.company_name || 'Hiring Team',
    job_role: item.job_role || 'Software Engineer Intern',
    overview: item.overview || '',
    requirements: item.requirements || '',
    apply_link: item.apply_link || '',
    post_url: item.post_url || item.apply_link || ''
  };

  try {
    const res = await fetch('/api/preview_custom_email', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.success) {
      openPreviewModalWithContent(data.subject, data.html_body);
    } else {
      showToast(data.error || 'Preview failed', 'error');
    }
  } catch (err) {
    showToast('Preview error: ' + err.message, 'error');
  }
};

// Dispatcher Live Preview
async function updateDispatcherPreview() {
  if (!el.dispPreviewFrame) return;

  const email = (el.dispEmail ? el.dispEmail.value.trim() : '') || 'recruiter@company.com';
  const company = el.dispCompany ? el.dispCompany.value.trim() : '';
  const role = el.dispRole ? el.dispRole.value.trim() : 'Software Engineer Intern';
  const reqs = el.dispRequirements ? el.dispRequirements.value.trim() : '';
  const overview = el.dispOverview ? el.dispOverview.value.trim() : '';
  const applyLink = el.dispApplyLink ? el.dispApplyLink.value.trim() : '';
  const subject = el.dispSubject ? el.dispSubject.value.trim() : '';

  const payload = {
    email: email,
    company_name: company,
    recruiter_name: company || 'Hiring Team',
    job_role: role,
    requirements: reqs,
    overview: overview,
    apply_link: applyLink,
    subject: subject
  };

  try {
    const res = await fetch('/api/preview_custom_email', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.success) {
      if (el.dispPreviewSubject) {
        el.dispPreviewSubject.innerText = data.subject;
      }
      el.dispPreviewFrame.srcdoc = data.html_body;
    }
  } catch (e) {
    console.warn('Live preview update error:', e);
  }
}

// Dispatch email from Direct Mail Dispatcher
async function dispatchCustomEmail() {
  const email = el.dispEmail ? el.dispEmail.value.trim() : '';
  if (!email || !email.includes('@') || !email.includes('.')) {
    showToast('Please enter a valid recipient email address.', 'error');
    if (el.dispEmail) el.dispEmail.focus();
    return;
  }

  const origText = el.dispSendBtn.innerHTML;
  el.dispSendBtn.disabled = true;
  el.dispSendBtn.innerHTML = '⏳ Dispatching with Resume...';

  const payload = {
    email: email,
    company_name: el.dispCompany ? el.dispCompany.value.trim() : '',
    recruiter_name: (el.dispCompany ? el.dispCompany.value.trim() : '') || 'Hiring Team',
    job_role: el.dispRole ? el.dispRole.value.trim() : 'Software Engineer Intern',
    requirements: el.dispRequirements ? el.dispRequirements.value.trim() : '',
    overview: el.dispOverview ? el.dispOverview.value.trim() : '',
    apply_link: el.dispApplyLink ? el.dispApplyLink.value.trim() : '',
    subject: el.dispSubject ? el.dispSubject.value.trim() : ''
  };

  try {
    const res = await fetch('/api/send_custom_email', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (data.success) {
      showToast(`🎉 Tailored application + resume sent to ${email}!`, 'success');
      el.dispEmail.value = '';
      fetchStats();
      switchTab('sent');
    } else {
      showToast(data.error || 'Failed to dispatch email.', 'error');
    }
  } catch (err) {
    showToast('Dispatch error: ' + err.message, 'error');
  } finally {
    el.dispSendBtn.disabled = false;
    el.dispSendBtn.innerHTML = origText;
  }
}

// Helper: Open Modal with Custom Content
function openPreviewModalWithContent(title, html) {
  el.modalTitle.innerText = title || 'Outreach Email Preview';
  el.modalPreviewContent.innerHTML = `<iframe srcdoc="${escapeHtml(html)}" style="width:100%; height:480px; border:none; display:block;"></iframe>`;
  el.modalOverlay.classList.add('active');
}

// Utility: Debounce
function debounce(fn, ms) {
  let timer;
  return function(...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), ms);
  };
}

// 1-Click Action: Dispatch Single Lead Email + Resume
async function triggerSendSingle(email) {
  if (!email) return;
  if (!confirm(`Send tailored application email + 1-page resume to ${email}?`)) return;
  showToast(`Initiating outreach to ${email}...`, 'info');
  try {
    const res = await fetch('/api/send_single_lead', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email })
    });
    const data = await res.json();
    if (data.success) {
      showToast(`🚀 Outreach initiated for ${email}! Check logs tab for live progress.`, 'success');
      setTimeout(fetchStats, 1500);
    } else {
      showToast(data.error || 'Failed to dispatch email.', 'error');
    }
  } catch (err) {
    showToast('Send error: ' + err.message, 'error');
  }
}

// 1-Click Action: Trigger 3-Day Follow-Up Reminders
async function triggerReminders() {
  const due = (state.data && state.data.metrics && state.data.metrics.due_reminders) || 0;
  const promptMsg = due > 0 
    ? `You have ${due} outreach emails sent >= 3 days ago. Check inbox for replies and dispatch polite follow-up reminders?`
    : `Check Gmail inbox for recruiter replies and send polite follow-up reminders to unreplied contacts?`;

  if (!confirm(promptMsg)) return;
  showToast('🔍 Checking Gmail inbox & triggering follow-ups in background...', 'info');
  try {
    const res = await fetch('/api/trigger_reminders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    const data = await res.json();
    if (data.success) {
      showToast('⏰ Follow-up reminder process running in background! Check activity log.', 'success');
      setTimeout(fetchStats, 2000);
    } else {
      showToast(data.error || 'Failed to trigger reminders.', 'error');
    }
  } catch (err) {
    showToast('Reminder error: ' + err.message, 'error');
  }
}

