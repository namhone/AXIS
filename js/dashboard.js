(function () {
  'use strict';

  var ROC = [0.4567, 0.2567, 0.1567, 0.09, 0.04];
  var dimensions = [
    { key: 'S1', label: 'Học thuật', description: 'GPA và môn cốt lõi', value: 0 },
    { key: 'S2', label: 'Ngoại ngữ', description: 'Chứng chỉ quy đổi', value: 0 },
    { key: 'S3', label: 'Thành tích', description: 'Giải thưởng học thuật', value: 0 },
    { key: 'S4', label: 'Tính cách', description: 'Holland / RIASEC', value: 0, readonly: true },
    { key: 'S5', label: 'Hoạt động', description: 'Ngoại khóa và lãnh đạo', value: 0, readonly: true }
  ];
  var subjects = [
    ['Toán', 'Math'], ['Ngữ văn', 'Literature'], ['Tiếng Anh', 'English'],
    ['Vật lí', 'Physics'], ['Hóa học', 'Chemistry'], ['Sinh học', 'Biology'],
    ['Tin học', 'Informatics'], ['Lịch sử', 'History'], ['Địa lý', 'Geography'], ['GDKT&PL', 'Civics']
  ];
  var fallbackBenchmarks = [
    { code: 'N03', name: 'Y dược & Khoa học Sức khỏe', need: [8.2, 6.2, 6.8, 8, 5.5], priority: ['S1', 'S3', 'S4', 'S2', 'S5'] },
    { code: 'N01', name: 'Máy tính & Công nghệ thông tin', need: [8, 6.5, 5.8, 7.2, 5], priority: ['S1', 'S2', 'S3', 'S4', 'S5'] },
    { code: 'N06', name: 'Kỹ thuật & Tự động hóa', need: [7.8, 5.8, 6, 7, 5.8], priority: ['S1', 'S3', 'S4', 'S2', 'S5'] }
  ];
  var benchmarks = fallbackBenchmarks.slice();
  var currentProfile = {};
  var renderTimer = 0;
  var evaluationRequest = null;
  var lastEvaluationPayload = '';

  function clamp(value) { return Math.max(0, Math.min(10, number(value))); }
  function number(value) {
    var parsed = Number.parseFloat(String(value == null ? '' : value).trim().replace(',', '.'));
    return Number.isFinite(parsed) ? parsed : 0;
  }
  function inputValues() {
    return dimensions.reduce(function (result, item) {
      result[item.key] = item.value;
      return result;
    }, {});
  }
  function rocWeightsFor(benchmark) {
    var weights = {};
    var priority = Array.isArray(benchmark.priority) ? benchmark.priority : [];
    priority.forEach(function (key, index) {
      if (dimensions.some(function (dimension) { return dimension.key === key; })) {
        weights[key] = (weights[key] || 0) + (ROC[index] || 0);
      }
    });
    return weights;
  }
  function scoreFor(values, benchmark) {
    var total = 0;
    var weights = rocWeightsFor(benchmark);
    Object.keys(weights).forEach(function (key) { total += weights[key] * number(values[key]); });
    return total * 10;
  }
  function gapFor(values, benchmark) {
    var weighted = 0;
    var weights = rocWeightsFor(benchmark);
    dimensions.forEach(function (dimension, index) {
      var required = number(Array.isArray(benchmark.need) ? benchmark.need[index] : 0);
      var key = dimension.key;
      weighted += (weights[key] || 0) * Math.pow(Math.max(0, required - number(values[key])), 2);
    });
    return Math.sqrt(weighted);
  }
  function scoreClass(score) { return score >= 80 ? 'is-high' : score >= 60 ? 'is-medium' : 'is-low'; }
  function profileScore(key, suffix) {
    var values = Object.keys(currentProfile).map(function (name) {
      return name.indexOf(key) === 0 && (!suffix || name.indexOf(suffix) > -1) ? number(currentProfile[name]) : 0;
    }).filter(function (value) { return value > 0; });
    return values;
  }
  function academicScore() {
    var values = profileScore('score');
    if (values.length) return values.reduce(function (sum, value) { return sum + value; }, 0) / values.length;
    var gpas = ['gpa10', 'gpa11', 'gpa12'].map(function (key) { return number(currentProfile[key]); }).filter(function (value) { return value > 0; });
    return gpas.length ? gpas.reduce(function (sum, value) { return sum + value; }, 0) / gpas.length : 0;
  }
  function certificateScore() {
    if (currentProfile.certificateUseHighSchool) return clamp(number(currentProfile.highSchoolLanguageScore));
    var records = Array.isArray(currentProfile.certificateRecords) ? currentProfile.certificateRecords : [];
    var recordScores = records.map(function (record) {
      if (window.AxisCertificates && window.AxisCertificates.isExpired(record.issueDate)) return 0;
      return window.AxisCertificates ? window.AxisCertificates.convertCertificateToNormalizedScore(
        record.language,
        record.name,
        record.score,
        currentProfile.highSchoolLanguageScore
      ) : 0;
    });
    var currentScore = window.AxisCertificates ? window.AxisCertificates.convertCertificateToNormalizedScore(
      currentProfile.certificateLanguage,
      currentProfile.certificateName,
      currentProfile.certificateScore,
      currentProfile.highSchoolLanguageScore
    ) : 0;
    return Math.max.apply(Math, recordScores.concat([currentScore, 0]));
  }
  function renderInputs() {
    var academic = document.getElementById('axisAcademicInputs');
    var language = document.getElementById('axisLanguageInputs');
    var readonly = document.getElementById('axisReadonlyInputs');
    academic.innerHTML = subjects.map(function (item) {
      return '<label class="axis-subject-input"><span>' + item[0] + '</span><output id="axis-subject-output-' + item[1] + '">0.0</output><input type="range" min="0" max="10" step="0.1" value="0" data-subject="' + item[1] + '"></label>';
    }).join('');
    language.innerHTML = '<label class="axis-certificate-input"><span>Ngôn ngữ</span><select id="axisCertificateLanguage"><option value="">Chọn ngôn ngữ</option></select></label>' +
      '<label class="axis-certificate-input"><span>Chứng chỉ</span><select id="axisCertificateType"><option value="">Chọn ngôn ngữ trước</option></select></label>' +
      '<label class="axis-certificate-input"><span>Điểm / cấp độ</span><input id="axisCertificateScore" disabled placeholder="Chọn chứng chỉ trước"></label>' +
      '<label class="axis-certificate-input"><span>Điểm Ngoại ngữ THPT</span><input id="axisHighSchoolLanguageScore" type="text" inputmode="decimal" min="0" max="10" step="0.1" placeholder="0–10"></label>';
    readonly.innerHTML = dimensions.filter(function (item) { return item.readonly; }).map(function (item) {
      return '<div class="axis-readonly-badge"><span>' + item.key + ' · ' + item.label + '</span><strong id="axis-readonly-' + item.key + '">0.0/10</strong><small>Đồng bộ từ hồ sơ</small></div>';
    }).join('');
    academic.querySelectorAll('input').forEach(function (input) {
      input.addEventListener('input', function () {
        var output = document.getElementById('axis-subject-output-' + input.dataset.subject);
        output.textContent = Number(input.value).toFixed(1);
        updateScores();
      });
    });
    var languageSelect = document.getElementById('axisCertificateLanguage');
    var typeSelect = document.getElementById('axisCertificateType');
    var scoreInput = document.getElementById('axisCertificateScore');
    function fillTypes() {
      var item = window.AxisCertificates && window.AxisCertificates.LANGUAGES.find(function (language) { return language.value === languageSelect.value; });
      typeSelect.innerHTML = '<option value="">Chọn chứng chỉ</option>' + (item ? item.certificates.map(function (cert) { return '<option value="' + cert[1] + '">' + cert[0] + '</option>'; }).join('') : '');
      scoreInput.value = '';
      scoreInput.disabled = !item || !typeSelect.value;
      scoreInput.type = 'text';
      updateScores();
    }
    function updateScoreControl() {
      var numeric = window.AxisCertificates && window.AxisCertificates.NUMERIC[typeSelect.value];
      var levels = window.AxisCertificates && window.AxisCertificates.LEVELS[typeSelect.value];
      scoreInput.outerHTML = numeric ? '<input id="axisCertificateScore" type="text" inputmode="decimal" min="' + numeric[0] + '" max="' + numeric[1] + '" step="' + numeric[2] + '" placeholder="' + numeric[3] + '">' : '<select id="axisCertificateScore"><option value="">Chọn cấp độ</option>' + (levels || []).map(function (level) { return '<option value="' + level[1] + '">' + level[0] + '</option>'; }).join('') + '</select>';
      scoreInput = document.getElementById('axisCertificateScore');
      scoreInput.disabled = !typeSelect.value;
      scoreInput.addEventListener('input', updateScores);
      scoreInput.addEventListener('change', updateScores);
      updateScores();
    }
    languageSelect.innerHTML = '<option value="">Chọn ngôn ngữ</option>' + (window.AxisCertificates ? window.AxisCertificates.LANGUAGES.map(function (item) { return '<option value="' + item.value + '">' + item.label + '</option>'; }).join('') : '');
    languageSelect.addEventListener('change', fillTypes);
    typeSelect.addEventListener('change', updateScoreControl);
    document.getElementById('axisHighSchoolLanguageScore').addEventListener('input', function () {
      updateScores();
    });
    document.getElementById('axisAchievementSelect').addEventListener('change', updateScores);
  }
  function applyProfile(profile) {
    currentProfile = profile || {};
    var academic = academicScore();
    dimensions[0].value = clamp(academic);
    dimensions[1].value = certificateScore();
    var achievements = ['awardRank', 'examDescription', 'examType'].filter(function (key) { return currentProfile[key]; }).length;
    dimensions[2].value = achievements ? clamp(4 + achievements * 2) : 0;
    var riasec = currentProfile.riasecScores || {};
    var riasecValues = Object.keys(riasec).map(function (key) { return number(riasec[key]); });
    dimensions[3].value = riasecValues.length ? clamp(Math.max.apply(Math, riasecValues)) : 0;
    dimensions[4].value = currentProfile.activityRole || currentProfile.activityName ? 7 : 0;
    var academicOutput = document.getElementById('axisAcademicOutput');
    if (academicOutput) academicOutput.textContent = academic.toFixed(1) + '/10';
    document.querySelectorAll('[data-subject]').forEach(function (input) {
      var prefix = 'score' + (currentProfile.className === 'Lớp 10' ? '9' : currentProfile.className === 'Lớp 11' ? '10' : '11');
      var value = number(currentProfile[prefix + input.dataset.subject]);
      input.value = value;
      var output = document.getElementById('axis-subject-output-' + input.dataset.subject);
      if (output) output.textContent = value.toFixed(1);
    });
    var languageSelect = document.getElementById('axisCertificateLanguage');
    if (languageSelect) {
      languageSelect.value = currentProfile.certificateLanguage || '';
      languageSelect.dispatchEvent(new Event('change'));
      var typeSelect = document.getElementById('axisCertificateType');
      typeSelect.value = currentProfile.certificateName || '';
      typeSelect.dispatchEvent(new Event('change'));
      var scoreInput = document.getElementById('axisCertificateScore');
      if (scoreInput) {
        scoreInput.value = currentProfile.certificateScore || '';
        scoreInput.dispatchEvent(new Event('input'));
      }
    }
    dimensions.filter(function (item) { return item.readonly; }).forEach(function (item) {
      var target = document.getElementById('axis-readonly-' + item.key);
      if (target) target.textContent = item.value.toFixed(1) + '/10';
    });
    render();
  }
  function updateScores() {
    var subjectValues = Array.prototype.slice.call(document.querySelectorAll('[data-subject]')).map(function (input) { return number(input.value); }).filter(function (value) { return value > 0; });
    dimensions[0].value = subjectValues.length ? subjectValues.reduce(function (sum, value) { return sum + value; }, 0) / subjectValues.length : dimensions[0].value;
    var scoreInput = document.getElementById('axisCertificateScore');
    var typeSelect = document.getElementById('axisCertificateType');
    var hsInput = document.getElementById('axisHighSchoolLanguageScore');
    if (scoreInput && typeSelect) dimensions[1].value = window.AxisCertificates ? window.AxisCertificates.convertCertificateToNormalizedScore('', typeSelect.value, scoreInput.value, number(hsInput && hsInput.value)) : 0;
    dimensions[2].value = clamp(document.querySelectorAll('#axisAchievementSelect input:checked').length * 2.5);
    document.getElementById('axisAcademicOutput').textContent = dimensions[0].value.toFixed(1) + '/10';
    render();
  }
  function syncServerEvaluation() {
    if (!window.AxisAuth || !window.AxisAuth.isSignedIn()) return;
    var payload = JSON.stringify({ scores: inputValues(), benchmarks: benchmarks.slice(0, 24) });
    if (payload === lastEvaluationPayload || evaluationRequest) return;
    window.clearTimeout(renderTimer);
    renderTimer = window.setTimeout(function () {
      evaluationRequest = window.AxisAuth.apiRequest('/axis/evaluate', {
        method: 'POST',
        body: payload
      }).then(function () {
        lastEvaluationPayload = payload;
      }).catch(function () {
        // A later input change can retry the failed evaluation.
      }).finally(function () {
        evaluationRequest = null;
      });
    }, 350);
  }
  function render() {
    var values = inputValues();
    var ranked = benchmarks.map(function (benchmark) { return { benchmark: benchmark, score: scoreFor(values, benchmark), gap: gapFor(values, benchmark) }; }).sort(function (a, b) { return b.score - a.score; });
    var average = ranked.length ? ranked.reduce(function (sum, item) { return sum + item.score; }, 0) / ranked.length : 0;
    document.getElementById('axisOverallScore').textContent = Math.round(average) + '%';
    document.getElementById('axisSummaryList').innerHTML = dimensions.map(function (item) { return '<div><span><b>' + item.key + '</b> ' + item.label + '</span><strong>' + item.value.toFixed(1) + '/10</strong></div>'; }).join('');
    var careerResults = document.getElementById('axisCareerResults');
    careerResults.innerHTML = ranked.map(function (item, index) {
      var score = Math.round(item.score);
      return '<article class="axis-career-row' + (index >= 3 ? ' axis-career-row--extra' : '') + '"><div class="axis-rank">' + String(index + 1).padStart(2, '0') + '</div><div><span class="eyebrow">' + item.benchmark.code + '</span><h3>' + item.benchmark.name + '</h3><p>GAP rủi ro: ' + item.gap.toFixed(2) + '</p></div><div class="axis-match ' + scoreClass(score) + '"><strong>' + score + '%</strong><span>' + (score >= 80 ? 'Tương thích cao' : score >= 60 ? 'Có thể phát triển' : 'Cần bổ khuyết') + '</span></div></article>';
    }).join('');
    if (ranked.length > 3) {
      careerResults.insertAdjacentHTML('beforeend', '<button class="ghost-btn axis-career-toggle" type="button" aria-expanded="false">Xem thêm ngành <span aria-hidden="true">↓</span></button>');
    }
    var labels = { S1: 'Học thuật', S2: 'Ngoại ngữ', S3: 'Thành tích', S4: 'RIASEC', S5: 'Ngoại khóa' };
    document.getElementById('axisGapResults').innerHTML = ranked.slice(0, 3).map(function (item) {
      var details = dimensions.map(function (dimension, index) {
        var target = number(Array.isArray(item.benchmark.need) ? item.benchmark.need[index] : 0);
        var actual = number(values[dimension.key]);
        var gap = Math.max(0, target - actual);
        return '<li><span>' + labels[dimension.key] + '</span><strong>' + actual.toFixed(1) + '/' + target.toFixed(1) + '</strong><small>Gap ' + gap.toFixed(1) + '</small></li>';
      }).join('');
      return '<article class="axis-gap-card"><span class="eyebrow">' + item.benchmark.code + ' · ' + item.benchmark.name + '</span><ul class="axis-gap-detail-list">' + details + '</ul><p class="axis-advice">Ưu tiên kỹ năng có gap lớn nhất trong 4 tuần tới.</p></article>';
    }).join('');
    syncServerEvaluation();
  }
  document.addEventListener('DOMContentLoaded', function () {
    renderInputs();
    render();
    document.getElementById('axisCareerResults').addEventListener('click', function (event) {
      var toggle = event.target.closest('.axis-career-toggle');
      if (!toggle) return;
      var expanded = toggle.getAttribute('aria-expanded') === 'true';
      toggle.setAttribute('aria-expanded', expanded ? 'false' : 'true');
      toggle.innerHTML = expanded ? 'Xem thêm ngành <span aria-hidden="true">↓</span>' : 'Thu gọn danh sách <span aria-hidden="true">↑</span>';
      document.getElementById('axisCareerResults').classList.toggle('is-expanded', !expanded);
    });
    document.addEventListener('axis:profile-hydrated', function () {
      if (window.AxisData && window.AxisData.getProfile) applyProfile(window.AxisData.getProfile());
    });
    if (window.AxisAuth) window.AxisAuth.apiRequest('/axis/benchmarks').then(function (items) {
      if (Array.isArray(items) && items.length) {
        benchmarks = items.map(function (item) {
          return { code: item.code, name: item.name, need: dimensions.map(function (dimension) { var requirement = item.requirements && item.requirements[dimension.key]; return requirement ? number(requirement.target || requirement.maximum || 0) : 0; }), priority: Array.isArray(item.roc_order) ? item.roc_order : dimensions.map(function (dimension) { return dimension.key; }) };
        });
        render();
      }
    }).catch(function () {});
  });
})();
