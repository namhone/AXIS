(function () {
  'use strict';
  var names = {
    R: 'Thực tế', I: 'Nghiên cứu', A: 'Nghệ thuật',
    S: 'Xã hội', E: 'Quản lý', C: 'Nghiệp vụ'
  };
  function render() {
    var data = window.AxisData && window.AxisData.getProfile ? window.AxisData.getProfile() : {};
    var result = data.riasecResult;
    if (!result || !result.code) {
      try { result = JSON.parse(localStorage.getItem('axis_riasec_result:guest') || 'null'); } catch (error) {}
    }
    var code = document.getElementById('profileHollandCode');
    var summary = document.getElementById('riasecProfileSummary');
    var details = document.getElementById('profileRiasecDetails');
    if (!code || !summary || !details) return;
    if (!result || !result.code) {
      code.classList.add('is-empty');
      code.textContent = 'Chưa có mã Holland';
      return;
    }
    code.classList.remove('is-empty');
    code.textContent = result.code;
    summary.textContent = result.code.split('').map(function (letter) {
      return names[letter] || letter;
    }).join(' · ') + ' — ' + result.code.split('').map(function (letter) {
      return names[letter] || letter;
    }).join(', ') + '.';
    var best = result.code.split('').map(function (letter) {
      var aspects = result.aspects && result.aspects[letter];
      if (!aspects) return '';
      var aspect = Object.keys(aspects).sort(function (a, b) { return aspects[b].converted - aspects[a].converted; })[0];
      return names[letter] + ' · khía cạnh ' + aspect + ' (' + aspects[aspect].converted + '/100)';
    }).filter(Boolean);
    details.textContent = 'Khía cạnh mũi nhọn: ' + best.join(' · ') + '.';
  }
  document.addEventListener('DOMContentLoaded', render);
  document.addEventListener('axis:profile-hydrated', render);
  document.addEventListener('axis:profile-changed', render);
}());
