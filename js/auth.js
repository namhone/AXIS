(function () {
  'use strict';

  const pageHost = window.location.hostname;
  const API_HOSTS = Array.from(new Set(
    [pageHost, 'localhost', '127.0.0.1'].filter(Boolean)
  ));
  const configuredApiBase = typeof window.AXIS_API_BASE === 'string'
    ? window.AXIS_API_BASE.replace(/\/+$/, '')
    : '';
  const USE_SAME_ORIGIN_API = !['localhost', '127.0.0.1'].includes(pageHost) || window.location.port === '8787';
  let activeApiHost = API_HOSTS[0];
  function apiBase(host) { return configuredApiBase || (USE_SAME_ORIGIN_API ? '/api/v1/auth' : 'http://' + host + ':8000/api/v1/auth'); }
  function accountApiBase(host) { return configuredApiBase ? configuredApiBase + '/account' : (USE_SAME_ORIGIN_API ? '/api/v1/account' : 'http://' + host + ':8000/api/v1/account'); }
  function rootApiBase(host) { return configuredApiBase ? configuredApiBase.replace(/\/auth$/, '') : (USE_SAME_ORIGIN_API ? '/api/v1' : 'http://' + host + ':8000/api/v1'); }
  const AUTH_AREA_SELECTOR = '#authArea';
  let currentUser = null;
  let currentAvatarUrl = '';
  let avatarRequestVersion = 0;
  let sessionCheckVersion = 0;
  let sessionInvalidationPromise = null;

  function normalizeAuthUser(payload) {
    if (!payload || typeof payload !== 'object') return null;
    if (payload.data && typeof payload.data === 'object') {
      if (payload.data.user && typeof payload.data.user === 'object') return payload.data.user;
      if (payload.data.id || payload.data.email) return payload.data;
    }
    if (payload.user && typeof payload.user === 'object') return payload.user;
    return payload.id || payload.email ? payload : null;
  }

  function ensureNotice() {
    let notice = document.getElementById('authNotice');
    if (!notice) {
      notice = document.createElement('div');
      notice.id = 'authNotice';
      notice.className = 'auth-notice hidden';
      notice.setAttribute('role', 'status');
      document.body.appendChild(notice);
    }
    return notice;
  }

  function showNotice(message, isError) {
    const notice = ensureNotice();
    notice.textContent = message;
    notice.classList.toggle('is-error', Boolean(isError));
    notice.classList.remove('hidden');
    window.clearTimeout(showNotice.timer);
    showNotice.timer = window.setTimeout(function () {
      notice.classList.add('hidden');
    }, 3600);
  }

  function setAuthState(user) {
    currentUser = user || null;
    avatarRequestVersion += 1;
    const signedIn = Boolean(currentUser);
    document.body.classList.toggle('auth-signed-in', signedIn);
    const authAreas = document.querySelectorAll(AUTH_AREA_SELECTOR);
    authAreas.forEach(function (authArea) {
      authArea.classList.toggle('hidden', signedIn);
    });
    const desktopAuthArea = document.querySelector('.header-auth > .auth-area, .header-auth #authArea');

    let userPanel = document.getElementById('userPanel');
    if (signedIn && !userPanel && desktopAuthArea && desktopAuthArea.parentElement) {
      userPanel = document.createElement('div');
      userPanel.id = 'userPanel';
      userPanel.className = 'user-panel';
      userPanel.innerHTML = [
        '<button class="user-chip" id="userChip" type="button" aria-expanded="false" aria-label="Mở menu tài khoản">',
        '<span class="user-avatar" aria-hidden="true"></span>',
        '<span class="user-avatar-caret" aria-hidden="true">⌄</span>',
        '</button>',
        '<div class="user-menu hidden" id="userMenu" role="menu">',
        '<div class="user-menu-name" id="userMenuName"></div>',
        '<div class="user-menu-email" id="userMenuEmail"></div>',
        '<button class="user-menu-item" type="button" data-menu-action="profile">Chỉnh sửa hồ sơ</button>',
        '<button class="user-menu-item" type="button" data-menu-action="settings">Cài đặt thông tin</button>',
        '<button class="user-menu-item logout" type="button" data-auth-logout>Đăng xuất</button>',
        '</div>'
      ].join('');
      desktopAuthArea.parentElement.appendChild(userPanel);
    }
    if (userPanel) {
      userPanel.classList.toggle('hidden', !signedIn);
      const userChip = userPanel.querySelector('#userChip');
      const userMenuName = userPanel.querySelector('#userMenuName');
      const userMenuEmail = userPanel.querySelector('#userMenuEmail');
      const avatar = userPanel.querySelector('.user-avatar');
      if (userMenuName) userMenuName.textContent = signedIn ? (currentUser.full_name || '') : '';
      if (userMenuEmail) userMenuEmail.textContent = signedIn ? currentUser.email : '';
      if (avatar) {
        avatar.textContent = signedIn ? getInitial(currentUser.full_name || currentUser.email) : '';
        avatar.style.backgroundImage = '';
      }
      if (userChip) userChip.setAttribute('aria-expanded', 'false');
      const userMenu = userPanel.querySelector('#userMenu');
      if (userMenu) userMenu.classList.add('hidden');
    }

    document.querySelectorAll('.mobile-auth').forEach(function (mobileAuth) {
      mobileAuth.classList.toggle('hidden', signedIn);
    });
    document.querySelectorAll('[data-auth-action]').forEach(function (button) {
      button.classList.toggle('hidden', signedIn);
    });
    if (signedIn) {
      loadAvatar();
    } else {
      if (currentAvatarUrl) {
        URL.revokeObjectURL(currentAvatarUrl);
        currentAvatarUrl = '';
      }
      clearAvatar();
    }
    document.dispatchEvent(new CustomEvent('axis:auth-state', {
      detail: { signedIn: signedIn, user: currentUser }
    }));
  }

  function getInitial(email) {
    return String(email || '?').trim().charAt(0).toUpperCase() || '?';
  }

  function renderAvatar(url) {
    document.querySelectorAll('.user-avatar').forEach(function (avatar) {
      avatar.textContent = '';
      avatar.style.backgroundImage = 'url("' + url + '")';
      avatar.style.backgroundSize = 'cover';
      avatar.style.backgroundPosition = 'center';
    });
    const portraitPreview = document.getElementById('portraitPreview');
    if (portraitPreview) {
      portraitPreview.innerHTML = '<img src="' + url + '" alt="Ảnh chân dung" />';
    }
  }

  function clearAvatar() {
    document.querySelectorAll('.user-avatar').forEach(function (avatar) {
      avatar.style.backgroundImage = '';
    });
    const portraitPreview = document.getElementById('portraitPreview');
    if (portraitPreview) {
      portraitPreview.textContent = currentUser ? getInitial(currentUser.full_name || currentUser.email) : 'A';
    }
  }

  async function loadAvatar() {
    const requestVersion = avatarRequestVersion;
    const userId = currentUser && currentUser.id;
    try {
      const response = await fetchWithTimeout(
        apiBase(activeApiHost) + '/avatar?refresh=' + Date.now(),
        { credentials: 'include' },
        8000
      );
      if (requestVersion !== avatarRequestVersion || !currentUser || currentUser.id !== userId) return;
      if (!response.ok) {
        clearAvatar();
        return;
      }
      const nextAvatarUrl = URL.createObjectURL(await response.blob());
      if (requestVersion !== avatarRequestVersion || !currentUser || currentUser.id !== userId) {
        URL.revokeObjectURL(nextAvatarUrl);
        return;
      }
      if (currentAvatarUrl) URL.revokeObjectURL(currentAvatarUrl);
      currentAvatarUrl = nextAvatarUrl;
      renderAvatar(currentAvatarUrl);
    } catch (error) {
      // The text initial remains a safe fallback when no avatar exists.
    }
  }

  async function uploadAvatar(file) {
    if (!file) return;
    if (!currentUser) {
      showNotice('Vui lòng đăng nhập trước khi tải ảnh đại diện.', true);
      return;
    }
    const previewUrl = URL.createObjectURL(file);
    renderAvatar(previewUrl);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const response = await fetchWithTimeout(apiBase(activeApiHost) + '/avatar', {
        method: 'PUT',
        credentials: 'include',
        body: formData
      }, 15000);
      if (!response.ok) {
        let message = 'Không thể tải ảnh đại diện lên.';
        try {
          const body = await response.json();
          if (body.error && body.error.message) message = body.error.message;
        } catch (error) {}
        throw new Error(message);
      }

      showNotice('Đã cập nhật ảnh đại diện cho tài khoản.');
      await loadAvatar();
    } catch (error) {
      await loadAvatar();
      if (currentAvatarUrl) renderAvatar(currentAvatarUrl);
      showNotice(error.message || 'Không thể tải ảnh đại diện lên.', true);
    } finally {
      URL.revokeObjectURL(previewUrl);
    }
  }

  async function uploadDocument(file, documentType) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType || 'certificate');
    const response = await fetchWithTimeout(accountApiBase(activeApiHost) + '/documents', {
      method: 'POST',
      credentials: 'include',
      body: formData
    }, 15000);
    if (!response.ok) throw await createApiError(response, 'Không thể lưu tài liệu vào tài khoản.');
    return response.json();
  }

  async function listDocuments() {
    return accountRequest('/documents', { headers: { Accept: 'application/json' } });
  }

  async function downloadDocument(documentId) {
    const response = await fetchWithTimeout(accountApiBase(activeApiHost) + '/documents/' + encodeURIComponent(documentId) + '/download', {
      credentials: 'include'
    }, 15000);
    if (!response.ok) throw await createApiError(response, 'Không thể tải tài liệu xuống.');
    return response.blob();
  }

  async function deleteDocument(documentId) {
    return accountRequest('/documents/' + encodeURIComponent(documentId), { method: 'DELETE' });
  }

  async function accountRequest(path, options) {
    let response;
    try {
      response = await fetchWithTimeout(accountApiBase(activeApiHost) + path, Object.assign({
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' }
      }, options || {}), 10000);
    } catch (error) {
      throw new Error('Không thể kết nối máy chủ. Vui lòng thử lại.');
    }
    if (!response.ok) {
      if (response.status === 401) {
        await invalidateExpiredSession();
      }
      throw await createApiError(response, response.status === 401
        ? 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.'
        : 'Không thể đồng bộ dữ liệu tài khoản.');
    }
    return response.status === 204 ? null : response.json();
  }

  async function apiRequest(path, options) {
    let response;
    try {
      response = await fetchWithTimeout(rootApiBase(activeApiHost) + path, Object.assign({
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' }
      }, options || {}), 10000);
    } catch (error) {
      throw new Error('Không thể kết nối máy chủ. Vui lòng thử lại.');
    }
    if (!response.ok) {
      if (response.status === 401) {
        await invalidateExpiredSession();
      }
      throw await createApiError(response, response.status === 401
        ? 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.'
        : 'Không thể đồng bộ dữ liệu tài khoản.');
    }
    return response.status === 204 ? null : response.json();
  }

  async function createApiError(response, fallbackMessage) {
    let body = null;
    try {
      body = await response.json();
    } catch (error) {
      body = null;
    }
    const message = response.status === 401 && fallbackMessage
      ? fallbackMessage
      : body && body.error && body.error.message
      ? body.error.message
      : body && typeof body.detail === 'string'
        ? body.detail
        : fallbackMessage;
    const error = new Error(message);
    error.status = response.status;
    return error;
  }

  async function invalidateExpiredSession() {
    if (sessionInvalidationPromise) return sessionInvalidationPromise;
    sessionInvalidationPromise = (async function () {
      try {
        await fetchWithTimeout(apiBase(activeApiHost) + '/logout', {
          method: 'POST',
          credentials: 'include',
          headers: { Accept: 'application/json' }
        }, 5000);
      } catch (error) {
        // The local UI must still leave the stale session even if logout cannot reach the API.
      } finally {
        setAuthState(null);
        showNotice('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.', true);
        sessionInvalidationPromise = null;
      }
    })();
    return sessionInvalidationPromise;
  }

  function appPageUrl(pageName) {
    const current = new URL(window.location.href);
    const pagesIndex = current.pathname.indexOf('/pages/');
    const rootPath = pagesIndex >= 0
      ? current.pathname.slice(0, pagesIndex + 1)
      : current.pathname.replace(/[^/]*$/, '');
    return new URL(rootPath + 'pages/' + pageName, current.origin).href;
  }

  function createModal() {
    let modal = document.getElementById('authModal');
    if (modal) return modal;
    modal = document.createElement('div');
    modal.className = 'auth-modal hidden';
    modal.id = 'authModal';
    modal.setAttribute('aria-hidden', 'true');
    modal.innerHTML = [
      '<div class="settings-modal-backdrop" data-close-auth="true"></div>',
      '<div class="auth-modal-panel" role="dialog" aria-modal="true" aria-labelledby="authModalTitle">',
      '<button type="button" class="settings-close" data-close-auth="true" aria-label="Đóng">×</button>',
      '<h3 id="authModalTitle">Đăng nhập</h3>',
      '<p class="auth-modal-note">Tiếp tục hành trình định hướng cùng Axis.</p>',
      '<form id="authForm">',
      '<label class="auth-field hidden" id="authNameField">Họ và tên<input name="name" type="text" autocomplete="name" placeholder="Nguyễn Văn A"></label>',
      '<label class="auth-field">Email<input name="email" type="email" autocomplete="email" required placeholder="you@example.com"></label>',
      '<label class="auth-field">Mật khẩu<input name="password" type="password" autocomplete="current-password" required minlength="8" placeholder="Tối thiểu 8 ký tự"></label>',
      '<button class="primary-btn full" type="submit">Tiếp tục</button>',
      '</form>',
      '<button class="auth-switch" type="button" id="authSwitch">Chưa có tài khoản? Đăng ký</button>',
      '</div>'
    ].join('');
    document.body.appendChild(modal);
    return modal;
  }

  function closeModal() {
    const modal = document.getElementById('authModal');
    if (modal) {
      modal.classList.add('hidden');
      modal.setAttribute('aria-hidden', 'true');
    }
  }

  function fetchWithTimeout(url, options, timeoutMs) {
    const controller = typeof AbortController === 'function' ? new AbortController() : null;
    const requestOptions = Object.assign({}, options || {});
    if (controller) requestOptions.signal = controller.signal;
    const limit = timeoutMs || 8000;
    let timer;
    const timeout = new Promise(function (_, reject) {
      timer = window.setTimeout(function () {
        if (controller) controller.abort();
        reject(new Error('Yêu cầu máy chủ đã hết thời gian chờ.'));
      }, limit);
    });
    return Promise.race([fetch(url, requestOptions), timeout]).finally(function () {
      window.clearTimeout(timer);
    });
  }

  function openModal(signUp) {
    const modal = createModal();
    modal.dataset.mode = signUp ? 'signup' : 'signin';
    modal.querySelector('#authModalTitle').textContent = signUp ? 'Đăng ký' : 'Đăng nhập';
    modal.querySelector('#authNameField').classList.toggle('hidden', !signUp);
    modal.querySelector('#authSwitch').textContent = signUp
      ? 'Đã có tài khoản? Đăng nhập'
      : 'Chưa có tài khoản? Đăng ký';
    modal.classList.remove('hidden');
    modal.setAttribute('aria-hidden', 'false');
    const email = modal.querySelector('input[name="email"]');
    if (email) email.focus();
  }

  function requireAuth() {
    if (currentUser) return true;
    showNotice('Vui lòng đăng nhập hoặc đăng ký để thực hiện thao tác này.', true);
    openModal(false);
    return false;
  }

  async function request(path, options) {
    const response = await fetchWithTimeout(apiBase(activeApiHost) + path, Object.assign({
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' }
    }, options || {}), 8000);
    let body = null;
    try {
      body = await response.json();
    } catch (error) {
      body = null;
    }
    if (!response.ok) {
      const message = body && body.error && body.error.message
        ? body.error.message
        : 'Không thể kết nối máy chủ. Vui lòng thử lại.';
      const error = new Error(message);
      error.status = response.status;
      throw error;
    }
    return body;
  }

  async function checkSession() {
    const requestVersion = ++sessionCheckVersion;
    const hadSession = Boolean(currentUser);
    try {
      const user = await request('/me', { method: 'GET' });
      if (requestVersion !== sessionCheckVersion) return;
      setAuthState(normalizeAuthUser(user));
    } catch (error) {
      if (requestVersion !== sessionCheckVersion) return;
      if (error.status === 401 && !USE_SAME_ORIGIN_API) {
        const fallbackHost = API_HOSTS.find(function (host) { return host !== activeApiHost; });
        if (fallbackHost) {
          try {
            const response = await fetchWithTimeout(apiBase(fallbackHost) + '/me', { credentials: 'include' }, 8000);
            if (requestVersion !== sessionCheckVersion) return;
            if (response.ok) {
              activeApiHost = fallbackHost;
              setAuthState(normalizeAuthUser(await response.json()));
              return;
            }
          } catch (fallbackError) {
            // Continue with the signed-out state when neither local host has a session.
          }
        }
      }
      if (error.status === 401) {
        if (hadSession) {
          await invalidateExpiredSession();
        } else {
          setAuthState(null);
        }
        return;
      }
      setAuthState(null);
      // Static deployments can run without the optional FastAPI origin.
      // Keep the signed-out UI quiet for an unavailable API endpoint.
      if (error.status && error.status !== 401 && error.status !== 404) {
        showNotice('Không thể kiểm tra trạng thái đăng nhập.', true);
      }
    }
  }

  async function submitAuth(form, signUp) {
    const submit = form.querySelector('button[type="submit"]');
    const emailField = form.querySelector('input[name="email"], input[type="email"]');
    const passwordField = form.querySelector('input[name="password"], input[type="password"]');
    const nameField = form.querySelector('input[name="name"]');
    const payload = {
      full_name: String(nameField ? nameField.value : '').trim(),
      email: String(emailField ? emailField.value : '').trim(),
      password: String(passwordField ? passwordField.value : '')
    };
    if (!signUp) delete payload.full_name;
    if (submit) submit.disabled = true;
    try {
      const user = await request(signUp ? '/register' : '/login', {
        method: 'POST',
        body: JSON.stringify(payload)
      });
      sessionCheckVersion += 1;
      setAuthState(normalizeAuthUser(user));
      closeModal();
      showNotice(signUp ? 'Đăng ký thành công. Bạn đã được đăng nhập.' : 'Đăng nhập thành công.');
    } catch (error) {
      showNotice(error.message, true);
    } finally {
      if (submit) submit.disabled = false;
    }
  }

  async function logout() {
    try {
      await request('/logout', { method: 'POST' });
      setAuthState(null);
      window.location.reload();
    } catch (error) {
      showNotice(error.message, true);
    }
  }

  function handleClick(event) {
    const authButton = event.target.closest('[data-auth-action]');
    if (authButton) {
      event.preventDefault();
      event.stopImmediatePropagation();
      openModal(authButton.getAttribute('data-auth-action') === 'signup');
      return;
    }
    const logoutButton = event.target.closest('[data-auth-logout], [data-menu-action="logout"]');
    if (logoutButton) {
      event.preventDefault();
      event.stopImmediatePropagation();
      logout();
      return;
    }
    const menuAction = event.target.closest('[data-menu-action]');
    if (menuAction) {
      event.preventDefault();
      event.stopImmediatePropagation();
      const action = menuAction.getAttribute('data-menu-action');
      if (action === 'profile') {
        window.location.href = appPageUrl('profile.html');
      } else if (action === 'settings') {
        const settings = document.getElementById('settingsModal');
        if (settings) {
          settings.classList.remove('hidden');
          settings.setAttribute('aria-hidden', 'false');
        } else {
          showNotice('Trang này chưa có cài đặt tài khoản.', true);
        }
      }
      const menu = menuAction.closest('.user-menu');
      if (menu) menu.classList.add('hidden');
      const chip = document.getElementById('userChip');
      if (chip) chip.setAttribute('aria-expanded', 'false');
      return;
    }
    const chip = event.target.closest('#userChip');
    if (chip) {
      event.preventDefault();
      event.stopImmediatePropagation();
      const menu = document.getElementById('userMenu');
      if (menu) {
        const isHidden = menu.classList.contains('hidden');
        menu.classList.toggle('hidden', !isHidden);
        chip.setAttribute('aria-expanded', String(isHidden));
      }
      return;
    }
    const closeButton = event.target.closest('[data-close-auth]');
    if (closeButton) closeModal();
  }

  function handleSubmit(event) {
    if (event.target.id !== 'authForm') return;
    event.preventDefault();
    event.stopImmediatePropagation();
    submitAuth(event.target, event.target.closest('#authModal').dataset.mode === 'signup');
  }

  function initialize() {
    document.addEventListener('axis:components-ready', function () {
      setAuthState(currentUser);
    });
    document.addEventListener('click', handleClick, true);
    document.addEventListener('submit', handleSubmit, true);
    document.addEventListener('click', function (event) {
      const target = event.target.closest(
        '#addGoal, #savePlan, #clearPlan, .toggle-complete, .delete-goal, ' +
        '.roadmap-start, .roadmap-done, #runAssessment, #saveSuggestions, ' +
        '#saveProfileBtn, #portraitUpload, #pdfUpload, .add-to-plan, #saveSettings, ' +
        '#generateRoadmapBtn'
      );
      if (target && !requireAuth()) {
        event.preventDefault();
        event.stopImmediatePropagation();
      }
    }, true);
    document.addEventListener('click', function (event) {
      if (event.target.closest('#authSwitch')) {
        const modal = document.getElementById('authModal');
        openModal(!modal || modal.dataset.mode !== 'signup');
      }

    });
    document.addEventListener('change', function (event) {
      if ((event.target.id === 'portraitUpload' || event.target.id === 'pdfUpload') && !requireAuth()) {
        event.target.value = '';
      }
    }, true);
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') closeModal();
    });
    document.addEventListener('change', function (event) {
      if (event.target.id === 'portraitUpload') uploadAvatar(event.target.files && event.target.files[0]);
    });
    checkSession();
  }

  window.AxisAuth = {
    checkSession: checkSession,
    refreshUser: checkSession,
    logout: logout,
    isSignedIn: function () { return Boolean(currentUser); },
    getCurrentUser: function () { return currentUser ? Object.assign({}, currentUser) : null; },
    uploadDocument: uploadDocument,
    listDocuments: listDocuments,
    downloadDocument: downloadDocument,
    deleteDocument: deleteDocument,
    accountRequest: accountRequest,
    apiRequest: apiRequest,
    fetchWithTimeout: fetchWithTimeout,
    requireAuth: requireAuth,
    showNotice: showNotice
  };
  // Keep the legacy global available for pages that still use the AXIS naming.
  window.AXISAuth = window.AxisAuth;
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize, { once: true });
  } else {
    initialize();
  }
})();

(function loadAxisIconAdapter() {
  var authScript = document.querySelector('script[src$="auth.js"]');
  if (!authScript || document.querySelector('script[data-axis-icons]')) return;
  var iconScript = document.createElement('script');
  iconScript.src = new URL('icons.js?v=20260920-icons-fix', authScript.src).href;
  iconScript.setAttribute('data-axis-icons', 'true');
  document.head.appendChild(iconScript);
})();
