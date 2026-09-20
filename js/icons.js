(function () {
  'use strict';

  var menuByPath = {
    'dashboard.html': 'layout-dashboard',
    'profile.html': 'user-check',
    'assessment.html': 'sparkles',
    'development.html': 'trending-up',
    'careers.html': 'briefcase',
    'about.html': 'info',
    'guide.html': 'book-open'
  };

  var careerByCode = {
    N01: 'it_software', N02: 'business_admin', N03: 'medicine_health', N04: 'languages_trans',
    N05: 'design_uiux', N06: 'automation_ee', N07: 'architecture_civil', N08: 'law_legal',
    N09: 'education_pedagogy', N10: 'hospitality_tourism', N11: 'journalism_media',
    N12: 'finance_banking', N13: 'agriculture_env', N14: 'biotech_food',
    N15: 'chemistry_materials', N16: 'agriculture_env', N17: 'psychology_social',
    N18: 'languages_trans', N19: 'logistics_supply', N20: 'aviation_maritime',
    N21: 'ai_data', N22: 'mechanical_semiconductor', N23: 'trending-up', N24: 'security_defense'
  };

  function loadLucide() {
    if (window.lucide) return Promise.resolve();
    return new Promise(function (resolve) {
      var script = document.createElement('script');
      script.src = 'https://unpkg.com/lucide@0.468.0/dist/umd/lucide.js';
      script.onload = resolve;
      script.onerror = resolve;
      document.head.appendChild(script);
    });
  }

  function menuName(link) {
    var path = (link.getAttribute('href') || '').split('/').pop().split('?')[0];
    return menuByPath[path] || 'briefcase';
  }

  function renderIcons() {
    var needsRender = false;
    document.querySelectorAll('.nav-item .nav-ico').forEach(function (element) {
      var link = element.closest('.nav-item');
      var iconName = link ? menuName(link) : 'briefcase';
      if (element.getAttribute('data-lucide') !== iconName) {
        element.setAttribute('data-lucide', iconName);
        needsRender = true;
      }
      if (!element.querySelector('svg')) {
        element.textContent = '';
        needsRender = true;
      }
    });
    document.querySelectorAll('.career-card[data-career-code] .career-icon').forEach(function (element) {
      var code = element.closest('[data-career-code]').getAttribute('data-career-code');
      var iconName = careerByCode[code] || 'help-circle';
      if (element.getAttribute('data-lucide') !== iconName) {
        element.setAttribute('data-lucide', iconName);
        needsRender = true;
      }
      if (!element.querySelector('svg')) {
        element.textContent = '';
        needsRender = true;
      }
    });
    document.querySelectorAll('[data-career-card] .career-icon').forEach(function (element) {
      if (!element.hasAttribute('data-lucide')) {
        element.setAttribute('data-lucide', 'help-circle');
        element.textContent = '';
        needsRender = true;
      }
    });
    if (needsRender && window.lucide) {
      window.lucide.createIcons({ attrs: { 'stroke-width': 1.75 } });
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadLucide().then(renderIcons);
    var observer = new MutationObserver(function (records) {
      var hasNewContent = records.some(function (record) {
        return Array.prototype.some.call(record.addedNodes, function (node) {
          return node.nodeType === 1 && node.tagName !== 'SVG';
        });
      });
      if (hasNewContent) renderIcons();
    });
    observer.observe(document.body, { childList: true, subtree: true });
  });
})();