(function () {
  const PROFILE_KEY = 'futurepath.profile';
  const COMPLETION_KEY = 'futurepath.profile_completion';

  function readProfile() {
    try {
      return JSON.parse(localStorage.getItem(PROFILE_KEY) || '{}');
    } catch (error) {
      console.warn('Không thể đọc hồ sơ đã lưu.', error);
      return {};
    }
  }

  function writeProfile(profile) {
    try {
      localStorage.setItem(PROFILE_KEY, JSON.stringify(profile));
      localStorage.setItem(COMPLETION_KEY, String(calculateCompletion(profile)));
    } catch (error) {
      console.warn('Không thể lưu hồ sơ trên thiết bị.', error);
    }
  }

  function calculateCompletion(profile) {
    const fields = ['name', 'birthYear', 'className', 'email', 'phone', 'linkedin', 'goal', 'introduction'];
    const completed = fields.filter(function (field) {
      return String(profile[field] || '').trim() !== '';
    }).length;
    return completed ? Math.round((completed / fields.length) * 100) : 78;
  }

  function getProfileCompletion() {
    try {
      const stored = Number(localStorage.getItem(COMPLETION_KEY));
      return Number.isFinite(stored) && stored >= 0 && stored <= 100 ? stored : calculateCompletion(readProfile());
    } catch (error) {
      return calculateCompletion({});
    }
  }

  function syncProfileCompletion(root) {
    const scope = root || document;
    const value = getProfileCompletion();
    scope.querySelectorAll('[data-profile-completion]').forEach(function (element) {
      element.textContent = value + '%';
    });
    scope.querySelectorAll('[data-profile-progress]').forEach(function (element) {
      element.style.setProperty('--progress', value + '%');
    });
  }

  function initProfilePersistence() {
    const fields = document.querySelectorAll('[data-profile-field]');
    if (!fields.length) return;
    const profile = readProfile();
    fields.forEach(function (field) {
      const key = field.getAttribute('data-profile-field');
      if (profile[key]) field.value = profile[key];
      field.addEventListener('input', function () {
        profile[key] = field.value;
        writeProfile(profile);
      });
    });
    syncProfileCompletion();
  }

  window.FuturePathData = {
    getProfileCompletion: getProfileCompletion,
    syncProfileCompletion: syncProfileCompletion,
    initProfilePersistence: initProfilePersistence
  };

  document.addEventListener('DOMContentLoaded', function () {
    initProfilePersistence();
    syncProfileCompletion();
  });
})();
