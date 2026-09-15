(function () {
  'use strict';

  function replaceText(node) {
    if (node.nodeType === Node.TEXT_NODE) {
      node.nodeValue = node.nodeValue.replace(/FuturePath/g, 'AXIS');
      return;
    }
    if (node.nodeType !== Node.ELEMENT_NODE || node.tagName === 'SCRIPT' || node.tagName === 'STYLE') return;
    Array.prototype.forEach.call(node.childNodes, replaceText);
  }

  document.addEventListener('DOMContentLoaded', function () {
    replaceText(document.body);
    if (document.title) document.title = document.title.replace(/FuturePath/g, 'AXIS');
  });
})();
