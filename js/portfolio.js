(function () {
  'use strict';

  var templates = {
    stem: { label: 'STEM / Engineering', accent: 'Kỹ thuật & nghiên cứu' },
    academic: { label: 'Academic / Scholarship', accent: 'Học thuật & học bổng' },
    developer: { label: 'Developer', accent: 'Sản phẩm & công nghệ' },
    creative: { label: 'Creative', accent: 'Ý tưởng & sáng tạo' }
  };
  var current = 'stem';

  function value(profile, key) {
    var item = profile && profile[key];
    return item == null ? '' : String(item).trim();
  }
  function esc(text) {
    return String(text || '').replace(/[&<>"']/g, function (character) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[character];
    });
  }
  function fallback(text) { return text || 'Chưa cập nhật'; }
  function block(title, body, meta) {
    return '<section class="portfolio-block"><h3>' + esc(title) + '</h3>' +
      '<p class="portfolio-meta">' + esc(fallback(meta)) + '</p>' +
      '<p>' + esc(fallback(body)) + '</p></section>';
  }
  function render(profile) {
    var config = templates[current] || templates.stem;
    var name = value(profile, 'name');
    var intro = value(profile, 'introduction');
    var goal = value(profile, 'goal');
    var contact = [value(profile, 'email'), value(profile, 'phone'), value(profile, 'linkedin')].filter(Boolean).join(' · ');
    var education = [value(profile, 'className'), value(profile, 'birthYear')].filter(Boolean).join(' · ');
    var certificates = Array.isArray(profile.certificateRecords) && profile.certificateRecords.length
      ? profile.certificateRecords.map(function (item) { return [item.name, item.score, item.issueDate].filter(Boolean).join(' · '); }).join(' | ')
      : [value(profile, 'certificateName'), value(profile, 'certificateScore'), value(profile, 'certificateIssueDate')].filter(Boolean).join(' · ');
    var sections = '';
    ['education', 'project', 'achievement', 'activity', 'skills', 'interests'].forEach(function (section) {
      if (section === 'project') sections += block('Dự án', value(profile, 'projectDescription'), [value(profile, 'projectName'), value(profile, 'projectType')].filter(Boolean).join(' · '));
      if (section === 'achievement') sections += block('Thành tích', value(profile, 'examDescription'), [value(profile, 'examType'), value(profile, 'examSubject'), value(profile, 'awardRank'), value(profile, 'examYear')].filter(Boolean).join(' · '));
      if (section === 'education') sections += block('Học tập', [value(profile, 'gpa10'), value(profile, 'gpa11'), value(profile, 'gpa12')].filter(Boolean).join(' · '), education);
      if (section === 'education') sections += block('Chứng chỉ', certificates);
      if (section === 'skills') sections += block('Kỹ năng', value(profile, 'skills') || value(profile, 'supportingSkills'));
      if (section === 'activity') sections += block('Hoạt động', value(profile, 'activityImpact'), [value(profile, 'activityName'), value(profile, 'activityRole')].filter(Boolean).join(' · '));
      if (section === 'interests') sections += block('Sở thích & mối quan tâm', value(profile, 'interests'));
    });
    if (!sections) sections = '<p class="portfolio-empty">Chưa có dữ liệu để hiển thị. Hãy cập nhật hồ sơ năng lực.</p>';
    document.getElementById('portfolioPreview').innerHTML =
      '<div class="portfolio-sheet portfolio-sheet--' + current + '">' +
      '<header class="portfolio-cover"><p class="portfolio-kicker">' + esc(config.accent) + '</p>' +
      '<h2>' + esc(fallback(name)) + '</h2><p class="portfolio-goal">' + esc(fallback(goal)) + '</p>' +
      (contact ? '<p class="portfolio-contact">' + esc(contact) + '</p>' : '') +
      '</header><div class="portfolio-intro">' + (intro ? '<p>' + esc(intro) + '</p>' : '<p class="portfolio-muted">Chưa cập nhật phần giới thiệu.</p>') + '</div>' +
      '<div class="portfolio-sections">' + sections + '</div>' +
      '<footer><span>' + config.label + '</span><span>FuturePath</span></footer></div>';
    document.getElementById('portfolioStatus').textContent = config.label + ' · Xem trước trực tiếp';
  }

  function refresh() {
    var profile = window.FuturePathData && window.FuturePathData.getProfile ? window.FuturePathData.getProfile() : {};
    render(profile);
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-template]').forEach(function (button) {
      button.addEventListener('click', function () {
        var nextTemplate = button.getAttribute('data-template');
        if (!templates[nextTemplate]) return;
        current = nextTemplate;
        document.querySelectorAll('[data-template]').forEach(function (item) {
          item.classList.toggle('is-selected', item === button);
          item.setAttribute('aria-pressed', item === button ? 'true' : 'false');
        });
        refresh();
      });
    });
    var printButton = document.getElementById('printPortfolio');
    var motionToggle = document.getElementById('previewMotion');
    if (printButton) printButton.addEventListener('click', function () { window.print(); });
    if (motionToggle) motionToggle.addEventListener('change', function (event) {
      document.body.classList.toggle('portfolio-motion', event.target.checked);
    });
    document.addEventListener('futurepath:profile-changed', refresh);
    document.addEventListener('futurepath:profile-hydrated', refresh);
    var authReady = false;
    document.addEventListener('futurepath:auth-state', function (event) {
      authReady = true;
      refresh();
      var status = document.getElementById('portfolioStatus');
      if (status && !event.detail.signedIn) status.textContent = 'Đăng nhập để tạo portfolio từ hồ sơ của bạn';
    });
    var status = document.getElementById('portfolioStatus');
    if (status) status.textContent = 'Đang đồng bộ hồ sơ tài khoản…';
    if (authReady) refresh();
  });
})();
