(function () {
  'use strict';

  var pendingLoad = null;
  var source = 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js';
  var integrity = 'sha384-JcnsjUPPylna1s1fvi1u12X5qjY5OL56iySh75FdtrwhO/SWXgMjoVqcKyIIWOLk';

  function load() {
    if (window.jspdf && window.jspdf.jsPDF) {
      return Promise.resolve(window.jspdf.jsPDF);
    }
    if (pendingLoad) return pendingLoad;

    pendingLoad = new Promise(function (resolve, reject) {
      var script = document.createElement('script');
      var settled = false;
      var timeoutId = window.setTimeout(function () {
        fail(new Error('PDF library request timed out'));
      }, 15000);

      function fail(error) {
        if (settled) return;
        settled = true;
        window.clearTimeout(timeoutId);
        script.remove();
        pendingLoad = null;
        reject(error);
      }

      function succeed(jsPDF) {
        if (settled) return;
        settled = true;
        window.clearTimeout(timeoutId);
        resolve(jsPDF);
      }

      script.src = source;
      script.integrity = integrity;
      script.crossOrigin = 'anonymous';
      script.onload = function () {
        if (!window.jspdf || !window.jspdf.jsPDF) {
          fail(new Error('PDF library loaded without the jsPDF API'));
          return;
        }
        succeed(window.jspdf.jsPDF);
      };
      script.onerror = function () {
        fail(new Error('Unable to load PDF library'));
      };
      document.head.appendChild(script);
    });

    return pendingLoad;
  }

  window.AxisPdf = { load: load };
})();
