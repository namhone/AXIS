(function () {
  'use strict';

  var script = document.currentScript;
  var componentBase = new URL('../components/', script && script.src ? script.src : document.baseURI);
  var siteRoot = new URL(document.body.classList.contains('home-page') ? './' : '../', document.baseURI);
  var componentReadyDispatched = false;

  function currentPath() {
    return window.location.pathname.replace(/\/+$/, '') || '/';
  }

  function resolvePath(path) {
    return new URL(path, siteRoot).href;
  }

  function markActive(element) {
    var nav = element.querySelector('.header-nav');
    element.querySelectorAll('[data-path]').forEach(function (link) {
      var href = resolvePath(link.dataset.path);
      link.href = href;
      link.classList.toggle('active', new URL(href).pathname.replace(/\/+$/, '') === currentPath());
    });
    if (nav) {
      nav.scrollLeft = 0;
      requestAnimationFrame(function () {
        nav.scrollLeft = 0;
      });
    }
  }

  function setupMobileMenu(host) {
    var button = host.querySelector('.mobile-menu-button');
    var nav = host.querySelector('.header-nav');
    if (!button || !nav) return;
    var originalParent = nav.parentNode;
    var originalNextSibling = nav.nextSibling;

    function closeMenu() {
      nav.classList.remove('is-mobile-open', 'mobile-nav-portal');
      if (originalNextSibling && originalNextSibling.parentNode === originalParent) {
        originalParent.insertBefore(nav, originalNextSibling);
      } else if (nav.parentNode !== originalParent) {
        originalParent.appendChild(nav);
      }
      document.body.classList.remove('mobile-nav-open');
      button.setAttribute('aria-expanded', 'false');
      button.setAttribute('aria-label', 'Mở menu');
      button.textContent = '☰';
    }

    button.addEventListener('click', function () {
      var isOpen = nav.classList.toggle('is-mobile-open');
      if (isOpen) {
        document.body.appendChild(nav);
        nav.classList.add('mobile-nav-portal');
      } else {
        closeMenu();
        return;
      }
      document.body.classList.toggle('mobile-nav-open', isOpen);
      button.setAttribute('aria-expanded', String(isOpen));
      button.setAttribute('aria-label', isOpen ? 'Đóng menu' : 'Mở menu');
      button.textContent = isOpen ? '×' : '☰';
    });
    nav.addEventListener('click', function (event) {
      if (!event.target.closest('a')) return;
      closeMenu();
    });
    document.addEventListener('keydown', function (event) {
      if (event.key !== 'Escape' || !nav.classList.contains('is-mobile-open')) return;
      closeMenu();
    });
    document.addEventListener('click', function (event) {
      if (!nav.classList.contains('is-mobile-open') || nav.contains(event.target) || button.contains(event.target)) return;
      closeMenu();
    });
  }

  function removeLegacyMobileMenu() {
    document.querySelectorAll('.mobile-nav-overlay').forEach(function (overlay) {
      overlay.remove();
    });
  }

  function watchLegacyMobileMenu() {
    if (!window.MutationObserver || !document.body) return;
    removeLegacyMobileMenu();
    var observer = new MutationObserver(function () {
      removeLegacyMobileMenu();
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  function showComponentError(host) {
    host.replaceChildren();
    host.setAttribute('aria-busy', 'false');
  }

  function loadComponent(host, name) {
    if (host.dataset.componentLoaded === name) return Promise.resolve();
    host.setAttribute('aria-busy', 'true');
    var controller = typeof AbortController === 'function' ? new AbortController() : null;
    var timeout;
    var timeoutPromise = new Promise(function (_, reject) {
      timeout = window.setTimeout(function () {
        if (controller) controller.abort();
        reject(new Error('Component request timed out: ' + name));
      }, 10000);
    });
    var request = fetch(new URL(name + '.html', componentBase), controller ? { signal: controller.signal } : undefined);
    return Promise.race([request, timeoutPromise])
      .then(function (response) {
        if (!response.ok) throw new Error('HTTP ' + response.status);
        return response.text();
      })
      .then(function (markup) {
        host.innerHTML = markup;
        if (name === 'header') {
          removeLegacyMobileMenu();
          markActive(host);
          setupMobileMenu(host);
        }
        if (name === 'footer') {
          host.querySelectorAll('form.contact-form').forEach(function (form) {
            form.addEventListener('submit', function (event) {
              event.preventDefault();
              alert('Cảm ơn! Chúng tôi sẽ liên hệ sớm.');
              form.reset();
            });
          });
        }
        host.dataset.componentLoaded = name;
        host.setAttribute('aria-busy', 'false');
      })
      .catch(function (error) {
        showComponentError(host);
        host.setAttribute('data-component-error', name);
        console.error('Unable to load shared component "' + name + '":', error);
      })
      .finally(function () {
        window.clearTimeout(timeout);
      });
  }

  class AppHeader extends HTMLElement {
    connectedCallback() {
      loadComponent(this, 'header').then(function () {
        if (!componentReadyDispatched) {
          componentReadyDispatched = true;
          document.dispatchEvent(new CustomEvent('futurepath:components-ready'));
        }
      });
    }
  }

  class AppFooter extends HTMLElement {
    connectedCallback() {
      loadComponent(this, 'footer');
    }
  }

  customElements.define('app-header', AppHeader);
  customElements.define('app-footer', AppFooter);
  watchLegacyMobileMenu();
})();
