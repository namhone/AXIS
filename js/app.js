(function () {
  'use strict';

  var profile = {};
  var accountId = '';
  var hydrationVersion = 0;
  var hasUnsavedChanges = false;
  var completionFields = ['name', 'birthYear', 'className', 'email', 'phone', 'linkedin', 'goal', 'introduction'];

  function normalizeProfile(data) {
    var normalized = data && typeof data === 'object' ? Object.assign({}, data) : {};
    if (!normalized.examSubject && normalized.subject) normalized.examSubject = normalized.subject;
    if (!normalized.subject && normalized.examSubject) normalized.subject = normalized.examSubject;
    return normalized;
  }

  function profileStorageKey(userId) {
    return userId ? 'futurepath_profile:' + userId : '';
  }

  function readLocalProfile(userId) {
    var key = profileStorageKey(userId);
    if (!key) return {};
    try {
      return normalizeProfile(JSON.parse(localStorage.getItem(key) || '{}'));
    } catch (error) {
      return {};
    }
  }

  function persistLocalProfile() {
    var key = profileStorageKey(accountId);
    if (!key) return;
    try {
      localStorage.setItem(key, JSON.stringify(profile));
    } catch (error) {
      // Storage can be unavailable in private browsing; the in-memory profile still works.
    }
  }

  function completion(data) {
    var count = completionFields.filter(function (key) {
      return String(data[key] || '').trim() !== '';
    }).length;
    return count ? Math.round(count / completionFields.length * 100) : 0;
  }

  function syncCompletion() {
    var value = completion(profile);
    document.querySelectorAll('[data-profile-completion]').forEach(function (element) {
      element.textContent = value + '%';
    });
    document.querySelectorAll('[data-profile-progress]').forEach(function (element) {
      element.style.setProperty('--progress', value + '%');
    });
  }

  function numeric(value) {
    var parsed = Number.parseFloat(String(value == null ? '' : value).trim().replace(',', '.'));
    return Number.isFinite(parsed) ? parsed : null;
  }

  function isSubjectScoreKey(key) {
    return /^score(?:9|10|11|12)[A-Za-z]+$/.test(key);
  }

  function normalizeScoreField(field, value) {
    var key = field.getAttribute('data-profile-field') || '';
    var isSubjectScore = isSubjectScoreKey(key);
    var isTenPointScore = isSubjectScore || key === 'highSchoolLanguageScore' || /^gpa(?:9|10|11|12)$/.test(key);
    var isEntranceScore = key === 'entranceScore';
    if (!isTenPointScore && !isEntranceScore) return value;
    if (value === '' || value == null) return value;
    var parsed = numeric(value);
    if (!Number.isFinite(parsed)) return '';
    var step = isEntranceScore ? 0.01 : 0.1;
    var maximum = isEntranceScore ? 30 : 10;
    parsed = Math.min(maximum, Math.max(0, parsed));
    var decimals = isEntranceScore ? 2 : 1;
    return (Math.round(parsed / step) * step).toFixed(decimals).replace(/\.0+$/, '');
  }

  function recalculateAcademic() {
    var years = ['9', '10', '11', '12'];
    years.forEach(function (year) {
      var values = ['Math', 'Literature', 'English', 'Physics', 'Chemistry', 'Biology', 'Informatics', 'History', 'Geography', 'Civics']
        .map(function (subject) { return numeric(profile['score' + year + subject]); })
        .filter(function (value) { return value !== null && value >= 0; });
      if (values.length) profile['gpa' + year] = (values.reduce(function (sum, value) { return sum + value; }, 0) / values.length).toFixed(2);
      var gpaField = document.querySelector('[data-profile-field="gpa' + year + '"]');
      if (gpaField) gpaField.value = profile['gpa' + year] || '';
    });
    var combinations = {
      A00: ['Math', 'Physics', 'Chemistry'],
      A01: ['Math', 'Physics', 'English'],
      B00: ['Math', 'Chemistry', 'Biology'],
      C00: ['Literature', 'History', 'Geography'],
      D01: ['Math', 'Literature', 'English']
    };
    var selected = combinations[profile.entranceCombination];
    if (selected) {
      var entranceYear = profile.className === 'Lớp 10' ? '9' : profile.className === 'Lớp 11' ? '10' : '11';
      var entranceValues = selected.map(function (subject) { return numeric(profile['score' + entranceYear + subject]); }).filter(function (value) { return value !== null; });
      if (entranceValues.length === 3) profile.entranceScore = entranceValues.reduce(function (sum, value) { return sum + value; }, 0).toFixed(2);
    }
    var entranceField = document.querySelector('[data-profile-field="entranceScore"]');
    if (entranceField) entranceField.value = profile.entranceScore || '';
  }

  function initProfile() {
    var fields = document.querySelectorAll('[data-profile-field]');
    if (!fields.length) return;
    fields.forEach(function (field) {
      var key = field.getAttribute('data-profile-field');
      if (key.indexOf('score') === 0 || key.indexOf('gpa') === 0 || key === 'entranceScore' || key === 'highSchoolLanguageScore') {
        if (isSubjectScoreKey(key)) {
          field.type = 'text';
          field.inputMode = 'decimal';
        }
        field.min = '0';
        field.max = key === 'entranceScore' ? '30' : '10';
        field.step = key === 'entranceScore' ? '0.01' : '0.1';
      }
      if (field.type === 'checkbox') field.checked = Boolean(profile[key]);
      else field.value = normalizeScoreField(field, profile[key] == null ? '' : profile[key]);
      if (key === 'name' || key === 'email') {
        field.readOnly = true;
        field.setAttribute('aria-readonly', 'true');
      }
      if (field.dataset.profileBound === 'true') return;
      field.dataset.profileBound = 'true';
      function updateValue(event) {
        var isTypingSubjectScore = isSubjectScoreKey(key) && event.type === 'input';
        if (field.type === 'checkbox') {
          profile[key] = field.checked;
        } else if (isTypingSubjectScore) {
          // Keep an unfinished decimal such as "9," while the user is typing.
          profile[key] = field.value.replace(/[^\d.,]/g, '');
        } else {
          profile[key] = normalizeScoreField(field, field.value);
          field.value = profile[key];
        }
        if (key.indexOf('score') === 0 || key === 'className' || key === 'entranceCombination') recalculateAcademic();
        persistLocalProfile();
        hasUnsavedChanges = true;
        document.dispatchEvent(new CustomEvent('futurepath:profile-changed'));
        syncCompletion();
      }
      field.addEventListener('input', updateValue);
      field.addEventListener('change', updateValue);
    });
    recalculateAcademic();
    document.dispatchEvent(new CustomEvent('futurepath:profile-hydrated'));
    syncCompletion();
  }

  async function saveProfile() {
    if (!window.FuturePathAuth || !window.FuturePathAuth.isSignedIn()) {
      throw new Error('Vui lòng đăng nhập để lưu hồ sơ.');
    }
    if (!accountId) {
      throw new Error('Phiên tài khoản chưa sẵn sàng. Vui lòng thử lại.');
    }
    document.querySelectorAll('[data-profile-field]').forEach(function (field) {
      var key = field.getAttribute('data-profile-field');
      var value = field.type === 'checkbox' ? field.checked : normalizeScoreField(field, field.value);
      if (field.type !== 'checkbox') field.value = value;
      // A dynamic select can briefly have no matching option while it is hydrated.
      if (field.tagName === 'SELECT' && !value && profile[key]) value = profile[key];
      profile[key] = value;
    });
    profile = normalizeProfile(await window.FuturePathAuth.apiRequest('/profile', {
      method: 'PUT',
      body: JSON.stringify(profile)
    }));
    hasUnsavedChanges = false;
    persistLocalProfile();
    document.dispatchEvent(new CustomEvent('futurepath:profile-changed'));
    initProfile();
    if (window.FuturePathAuth.refreshUser) await window.FuturePathAuth.refreshUser();
    return profile;
  }

  async function hydrateProfile() {
    if (!window.FuturePathAuth || !window.FuturePathAuth.isSignedIn()) return;
    var version = ++hydrationVersion;
    var expectedAccountId = accountId;
    var serverProfile = normalizeProfile(await window.FuturePathAuth.apiRequest('/profile'));
    if (
      version !== hydrationVersion ||
      accountId !== expectedAccountId ||
      !window.FuturePathAuth.isSignedIn()
    ) return;
    profile = serverProfile;
    hasUnsavedChanges = false;
    persistLocalProfile();
    document.dispatchEvent(new CustomEvent('futurepath:profile-changed'));
    initProfile();
  }

  window.FuturePathData = {
    getProfileCompletion: function () { return completion(profile); },
    getProfile: function () { return Object.assign({}, profile); },
    setProfileValue: function (key, value) {
      if (!key) return;
      profile[key] = value;
      persistLocalProfile();
      hasUnsavedChanges = true;
      document.dispatchEvent(new CustomEvent('futurepath:profile-changed'));
    },
    hasUnsavedChanges: function () { return hasUnsavedChanges; },
    markProfileDirty: function () {
      hasUnsavedChanges = true;
      document.dispatchEvent(new CustomEvent('futurepath:profile-changed'));
    },
    syncProfileCompletion: syncCompletion,
    initProfilePersistence: initProfile,
    hydrateProfile: hydrateProfile,
    saveProfile: saveProfile
  };
  // Keep the legacy global available for page-level scripts during the migration.
  window.AXISData = window.FuturePathData;

  document.addEventListener('DOMContentLoaded', function () {
    initProfile();
    document.addEventListener('futurepath:auth-state', function (event) {
      if (event.detail.signedIn) {
        hydrationVersion += 1;
        accountId = event.detail.user && event.detail.user.id ? String(event.detail.user.id) : '';
        hasUnsavedChanges = false;
        profile = readLocalProfile(accountId);
        if (event.detail.user) {
          profile.name = event.detail.user.full_name || '';
          profile.email = event.detail.user.email || '';
          initProfile();
        }
        hydrateProfile().catch(function (error) {
          var status = document.getElementById('profileSaveStatus');
          if (status) status.textContent = error.message || 'Không thể tải hồ sơ tài khoản.';
        });
      }
      else {
        hydrationVersion += 1;
        accountId = '';
        hasUnsavedChanges = false;
        profile = {};
        try {
          localStorage.removeItem('futurepath_profile');
        } catch (error) {
          // Ignore unavailable browser storage while clearing the signed-out state.
        }
        initProfile();
      }
    });
    window.addEventListener('beforeunload', function (event) {
      if (!hasUnsavedChanges) return;
      event.preventDefault();
      event.returnValue = 'Bạn có thay đổi chưa lưu. Nếu rời hoặc tải lại trang, dữ liệu có thể bị mất.';
      return event.returnValue;
    });
  });
})();
