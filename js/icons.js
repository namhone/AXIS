(function () {
  'use strict';
  if (window.__axisIconsInitialized) return;
  window.__axisIconsInitialized = true;

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
    N01: 'code', N02: 'building-2', N03: 'stethoscope', N04: 'languages',
    N05: 'palette', N06: 'zap', N07: 'ruler', N08: 'scale',
    N09: 'graduation-cap', N10: 'hotel', N11: 'newspaper',
    N12: 'wallet', N13: 'sprout', N14: 'dna',
    N15: 'test-tube', N16: 'sprout', N17: 'heart-handshake',
    N18: 'languages', N19: 'truck', N20: 'plane',
    N21: 'brain-circuit', N22: 'wrench', N23: 'trending-up', N24: 'shield-check'
  };

  function loadLucide() {
    if (window.lucide) return Promise.resolve();
    return new Promise(function (resolve) {
      var script = document.createElement('script');
      script.src = 'https://unpkg.com/lucide@0.468.0/dist/umd/lucide.js';
      script.integrity = 'sha384-LtmWBcrD5iuFIR4sFphS8IiiaftkypL5dJzLKywbyd9ATLB7ZbPz3JYnI9nvXHkV';
      script.crossOrigin = 'anonymous';
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
      if (window.lucide && !element.querySelector('svg')) {
        element.textContent = '';
        needsRender = true;
      }
    });
    document.querySelectorAll('.career-card[data-career-code] .career-icon, .career-icon[data-lucide]').forEach(function (element) {
      var careerCard = element.closest('[data-career-code]');
      var code = careerCard ? careerCard.getAttribute('data-career-code') : '';
      var iconName = careerByCode[code] || 'help-circle';
      if (element.getAttribute('data-lucide') !== iconName) {
        element.setAttribute('data-lucide', iconName);
        needsRender = true;
      }
      if (window.lucide && !element.querySelector('svg')) {
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
    document.querySelectorAll('[data-lucide]').forEach(function (element) {
      if (!element.querySelector('svg')) {
        element.textContent = '';
        needsRender = true;
      }
    });
    if (needsRender && window.lucide) {
      window.lucide.createIcons({ attrs: { 'stroke-width': 1.75 } });
    }
  }

  function initialize() {
    var renderScheduled = false;
    var rendering = false;
    function scheduleRender() {
      if (renderScheduled || rendering) return;
      renderScheduled = true;
      window.requestAnimationFrame(function () {
        renderScheduled = false;
        rendering = true;
        try {
          renderIcons();
        } finally {
          rendering = false;
        }
      });
    }
    loadLucide().then(scheduleRender);
    var observer = new MutationObserver(function (records) {
      var hasNewContent = records.some(function (record) {
        return Array.prototype.some.call(record.addedNodes, function (node) {
          return node.nodeType === 1 && node.tagName !== 'SVG';
        });
      });
      if (hasNewContent) scheduleRender();
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize, { once: true });
  } else {
    initialize();
  }
})();