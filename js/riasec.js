(function () {
  'use strict';

  var GROUPS = [
    { code: 'R', name: 'Thực tế', description: 'Thích làm việc với công cụ, máy móc, vật liệu và kết quả cụ thể.' },
    { code: 'I', name: 'Nghiên cứu', description: 'Thích quan sát, phân tích, đặt câu hỏi và tìm lời giải bằng dữ liệu.' },
    { code: 'A', name: 'Nghệ thuật', description: 'Thích sáng tạo, thể hiện ý tưởng và tạo ra những cách làm riêng.' },
    { code: 'S', name: 'Xã hội', description: 'Thích hỗ trợ, hướng dẫn, hợp tác và tạo ảnh hưởng tích cực đến người khác.' },
    { code: 'E', name: 'Quản lý', description: 'Thích dẫn dắt, thuyết phục, tổ chức nguồn lực và biến ý tưởng thành kết quả.' },
    { code: 'C', name: 'Nghiệp vụ', description: 'Thích hệ thống, quy trình, sự chính xác và cách làm rõ ràng.' }
  ];
  var QUESTIONS_PER_ASPECT = 2;
  var ASPECTS_PER_GROUP = 5;
  var QUESTIONS_PER_GROUP = QUESTIONS_PER_ASPECT * ASPECTS_PER_GROUP;
  var TOTAL_QUESTIONS = GROUPS.length * QUESTIONS_PER_GROUP;
  var MIN_EVALUATION_COMPLETION = 0.6;
  var state = { bank: {}, sourceBank: {}, groupIndex: 0, answers: {}, result: null, draftLoaded: false };
  var storageKey = 'axis_riasec_draft_v2';
  var usedQuestionsKey = 'axis_riasec_used_questions';
  var submitTimer = null;
  var accountSyncTimer = null;
  var submitPreviousOverflow = '';

  function $(id) { return document.getElementById(id); }
  function signedInId() {
    var user = window.AxisAuth && window.AxisAuth.getCurrentUser ? window.AxisAuth.getCurrentUser() : null;
    return user && user.id ? String(user.id) : 'guest';
  }
  function keyForUser() { return storageKey + ':' + signedInId(); }
  function usedQuestionsKeyForUser() { return usedQuestionsKey + ':' + signedInId(); }
  function getUsedQuestionIds(sourceBank) {
    var available = {};
    GROUPS.forEach(function (group) {
      (sourceBank[group.code] || []).forEach(function (question) {
        available[question.id] = true;
      });
    });
    try {
      var stored = JSON.parse(localStorage.getItem(usedQuestionsKeyForUser()) || '[]');
      return Array.isArray(stored) ? stored.filter(function (id) { return available[id]; }) : [];
    } catch (error) {
      return [];
    }
  }
  function rememberSelectedQuestions() {
    var used = getUsedQuestionIds(state.sourceBank);
    var selectedIds = [];
    GROUPS.forEach(function (group) {
      (state.bank[group.code] || []).forEach(function (question) {
        selectedIds.push(question.id);
      });
    });
    try {
      localStorage.setItem(usedQuestionsKeyForUser(), JSON.stringify(
        Array.from(new Set(used.concat(selectedIds)))
      ));
    } catch (error) {}
  }
  function saveDraft(syncAccount) {
    var progress = {
      answered: totalAnswered(),
      total: TOTAL_QUESTIONS,
      completion: Math.round(totalAnswered() / TOTAL_QUESTIONS * 100),
      updatedAt: new Date().toISOString()
    };
    try {
      localStorage.setItem(keyForUser(), JSON.stringify({
        answers: state.answers,
        progress: progress,
        groupIndex: state.groupIndex,
        questions: state.bank,
        version: 2
      }));
    } catch (error) {}
    if (syncAccount) {
      if (accountSyncTimer) window.clearTimeout(accountSyncTimer);
      accountSyncTimer = window.setTimeout(function () {
        accountSyncTimer = null;
        if (!window.AxisAuth || !window.AxisAuth.isSignedIn() || !window.AxisData) return;
        var answered = totalAnswered();
        var latestProgress = {
          answered: answered,
          total: TOTAL_QUESTIONS,
          completion: Math.round(answered / TOTAL_QUESTIONS * 100),
          updatedAt: new Date().toISOString()
        };
        window.AxisData.setProfileValue('riasecDraft', {
          answers: Object.assign({}, state.answers),
          groupIndex: state.groupIndex,
          progress: latestProgress
        });
        window.AxisData.setProfileValue('riasecProgress', latestProgress);
        if (window.AxisData.saveProfile) window.AxisData.saveProfile().catch(function () {});
      }, 900);
    }
    var status = $('draftStatus');
    if (status) status.textContent = 'Đã tự động lưu nháp';
  }
  function loadDraft() {
    state.draftLoaded = false;
    try {
      var draft = JSON.parse(localStorage.getItem(keyForUser()) || '{}');
      if (!draft.answers && window.AxisData && window.AxisData.getProfile) {
        draft = window.AxisData.getProfile().riasecDraft || {};
      }
      var compatibleDraft = draft.version === 2 && draft.questions && GROUPS.every(function (group) {
        return Array.isArray(draft.questions[group.code]) &&
          draft.questions[group.code].length === QUESTIONS_PER_GROUP &&
          Array.from({ length: ASPECTS_PER_GROUP }, function (_, index) {
            return draft.questions[group.code].filter(function (question) { return question.aspect === index + 1; }).length;
          }).every(function (count) { return count === QUESTIONS_PER_ASPECT; });
      });
      if (compatibleDraft) {
        state.answers = draft.answers || {};
        state.groupIndex = Number.isInteger(draft.groupIndex) ? Math.min(5, Math.max(0, draft.groupIndex)) : 0;
        state.bank = draft.questions;
        state.draftLoaded = true;
      } else {
        state.answers = {};
        state.groupIndex = 0;
        try { localStorage.removeItem(keyForUser()); } catch (error) {}
      }
    } catch (error) {}
  }
  function randomSample(items, count) {
    var shuffled = items.slice();
    for (var index = shuffled.length - 1; index > 0; index -= 1) {
      var swapIndex = Math.floor(Math.random() * (index + 1));
      var current = shuffled[index];
      shuffled[index] = shuffled[swapIndex];
      shuffled[swapIndex] = current;
    }
    return shuffled.slice(0, count);
  }
  function parseQuestionBank(text) {
    var bank = {};
    var matcher = /([RIASEC])(\d+)\.\s*([\s\S]*?)(?=[RIASEC]\d+\.\s|$)/g;
    var match;
    while ((match = matcher.exec(text))) {
      var code = match[1];
      var number = Number(match[2]);
      if (!bank[code]) bank[code] = [];
      bank[code].push({
        id: code + number,
        text: match[3]
          .replace(/\s*Khía cạnh\s+\d+\s*:[^\n]*(?:\n|$)/gi, ' ')
          .replace(/\s+/g, ' ')
          .trim(),
        aspect: Math.floor((number - 1) / 20) + 1
      });
    }
    return { source: bank, selected: selectQuestions(bank) };
  }
  function selectQuestions(sourceBank) {
    var used = getUsedQuestionIds(sourceBank);
    var usedLookup = {};
    used.forEach(function (id) { usedLookup[id] = true; });
    var allIds = [];
    GROUPS.forEach(function (group) {
      (sourceBank[group.code] || []).forEach(function (question) { allIds.push(question.id); });
    });
    if (allIds.length && allIds.every(function (id) { return usedLookup[id]; })) {
      used = [];
      usedLookup = {};
      try { localStorage.removeItem(usedQuestionsKeyForUser()); } catch (error) {}
    }
    var selectedBank = {};
    GROUPS.forEach(function (group) {
      var source = sourceBank[group.code] || [];
      var selected = [];
      for (var aspect = 1; aspect <= 5; aspect += 1) {
        var aspectQuestions = source.filter(function (question) { return question.aspect === aspect; });
        var unused = aspectQuestions.filter(function (question) { return !usedLookup[question.id]; });
        var aspectSelection = randomSample(unused, Math.min(QUESTIONS_PER_ASPECT, unused.length));
        if (aspectSelection.length < QUESTIONS_PER_ASPECT) {
          var selectedLookup = {};
          aspectSelection.forEach(function (question) { selectedLookup[question.id] = true; });
          aspectSelection = aspectSelection.concat(randomSample(
            aspectQuestions.filter(function (question) { return !selectedLookup[question.id]; }),
            QUESTIONS_PER_ASPECT - aspectSelection.length
          ));
        }
        selected = selected.concat(aspectSelection);
      }
      selectedBank[group.code] = randomSample(selected, selected.length);
    });
    return selectedBank;
  }
  function setVisibility(id, visible) { $(id).classList.toggle('hidden', !visible); }
  function renderTabs() {
    $('groupTabs').innerHTML = GROUPS.map(function (group, index) {
      return '<button type="button" class="riasec-tab' + (index === state.groupIndex ? ' active' : '') + '" data-group-index="' + index + '">' + group.code + '<span>' + group.name + '</span></button>';
    }).join('');
    $('groupTabs').querySelectorAll('[data-group-index]').forEach(function (button) {
      button.addEventListener('click', function () {
        state.groupIndex = Number(button.dataset.groupIndex);
        saveDraft(true);
        renderQuestion();
      });
    });
  }
  function renderAnsweredQuestions() {
    var activeQuestions = state.bank[GROUPS[state.groupIndex].code] || [];
    var totalAnsweredQuestions = totalAnswered();
    var completion = Math.round(totalAnsweredQuestions / TOTAL_QUESTIONS * 100);
    $('riasecProgressBar').style.width = completion + '%';
    $('answeredQuestions').innerHTML = activeQuestions.map(function (question, index) {
      var done = state.answers[question.id] ? ' is-answered' : '';
      return '<button type="button" class="riasec-question-dot' + done + ' is-current-group" data-question-index="' + index + '" title="Câu ' + (index + 1) + (done ? ' đã trả lời' : ' chưa trả lời') + '">Câu ' + (index + 1) + '</button>';
    }).join('');
    $('answeredQuestions').querySelectorAll('[data-question-index]').forEach(function (button) {
      button.addEventListener('click', function () {
        var targetQuestion = Number(button.dataset.questionIndex);
        var target = $('questionList').querySelector('[data-question-index="' + targetQuestion + '"]');
        if (target) target.scrollIntoView({ behavior: 'smooth', block: 'center' });
      });
    });
  }
  function renderQuestion() {
    var group = GROUPS[state.groupIndex];
    var groupQuestions = state.bank[group.code];
    $('groupEyebrow').textContent = 'NHÓM ' + group.code;
    $('groupTitle').textContent = group.name;
    $('questionList').innerHTML = groupQuestions.map(function (question, index) {
      return '<article class="riasec-question" data-question-index="' + index + '" style="--question-index:' + index + '">' +
        '<div class="riasec-question-heading"><span class="riasec-question-number">Câu ' + (index + 1) + '</span></div>' +
        '<h3>' + question.text + '</h3>' +
        '<div class="riasec-scale" role="radiogroup" aria-label="Mức độ phù hợp câu ' + (index + 1) + '">' +
        [1, 2, 3, 4, 5].map(function (value) {
          var faces = ['😣', '🙁', '😐', '🙂', '😄'];
          var labels = ['Hoàn toàn không đúng', 'Không đúng', 'Phân vân', 'Khá đúng', 'Rất đúng'];
          var checked = Number(state.answers[question.id]) === value ? ' checked' : '';
          return '<label class="riasec-option"><input type="radio" name="riasec-' + question.id + '" value="' + value + '"' + checked + '><strong aria-hidden="true">' + faces[value - 1] + '</strong><span>' + labels[value - 1] + '</span></label>';
        }).join('') + '</div></article>';
    }).join('');
    $('questionList').querySelectorAll('input').forEach(function (input) {
      input.addEventListener('change', function () {
        state.answers[input.name.replace('riasec-', '')] = Number(input.value);
        saveDraft();
        renderAnsweredQuestions();
      });
    });
    renderAnsweredQuestions();
    renderTabs();
  }
  function totalAnswered() {
    var count = 0;
    GROUPS.forEach(function (group) {
      (state.bank[group.code] || []).forEach(function (question) {
        if (state.answers[question.id]) count += 1;
      });
    });
    return count;
  }
  function closeSubmitDialog() {
    if (submitTimer) window.clearInterval(submitTimer);
    submitTimer = null;
    setVisibility('submitModal', false);
    $('submitModal').setAttribute('aria-hidden', 'true');
    document.body.classList.remove('riasec-submit-open');
    document.body.style.overflow = submitPreviousOverflow;
  }
  function openSubmitDialog() {
    if (!$('submitModal') || !$('confirmSubmit') || !$('submitCountdown')) return;
    var completion = Math.round(totalAnswered() / TOTAL_QUESTIONS * 100);
    var countdown = 5;
    setVisibility('submitModal', true);
    $('submitModal').setAttribute('aria-hidden', 'false');
    submitPreviousOverflow = document.body.style.overflow;
    document.body.classList.add('riasec-submit-open');
    document.body.style.overflow = 'hidden';
    $('submitWarning').textContent = completion === 100
      ? 'Bài đã hoàn thiện 100%. Hãy xác nhận để lưu thông tin, tính điểm và tạo nhận xét.'
      : 'Bài mới hoàn thiện ' + completion + '%. Nếu nộp lúc này, thông tin còn thiếu có thể khiến kết quả và nhận xét không chính xác.';
    $('submitCountdown').textContent = 'Vui lòng chờ ' + countdown + ' giây...';
    $('confirmSubmit').disabled = true;
    $('cancelSubmit').classList.add('hidden');
    if (submitTimer) window.clearInterval(submitTimer);
    submitTimer = window.setInterval(function () {
      countdown -= 1;
      if (countdown > 0) {
        $('submitCountdown').textContent = 'Vui lòng chờ ' + countdown + ' giây...';
        return;
      }
      window.clearInterval(submitTimer);
      submitTimer = null;
      $('submitCountdown').textContent = 'Bạn có thể xác nhận nộp bài.';
      $('confirmSubmit').disabled = false;
      $('cancelSubmit').classList.remove('hidden');
    }, 1000);
  }
  function submitTest() {
    closeSubmitDialog();
    showResult();
    try { localStorage.removeItem(keyForUser()); } catch (error) {}
  }
  function toggleControls() {
    var content = $('riasecControlContent');
    var button = $('toggleRiasecControls');
    var layout = document.querySelector('.riasec-assessment-layout');
    if (!content || !button) return;
    var hidden = content.classList.toggle('hidden');
    if (layout) layout.classList.toggle('controls-collapsed', hidden);
    button.setAttribute('aria-expanded', String(!hidden));
    content.setAttribute('aria-hidden', String(hidden));
    button.textContent = hidden ? 'Hi\u1ec7n b\u1ea3ng \u0111i\u1ec1u khi\u1ec3n' : '\u1ea8n b\u1ea3ng \u0111i\u1ec1u khi\u1ec3n';
  }
  function handleSubmitKeydown(event) {
    if (event.key === 'Escape' && !$('submitModal').classList.contains('hidden')) {
      closeSubmitDialog();
    }
  }
  function calculateResult() {
    var scores = {};
    var aspects = {};
    GROUPS.forEach(function (group) {
      var groupQuestions = state.bank[group.code];
      var answeredGroupQuestions = groupQuestions.filter(function (question) { return state.answers[question.id]; });
      var groupTotal = answeredGroupQuestions.reduce(function (sum, question) { return sum + Number(state.answers[question.id]); }, 0);
      scores[group.code] = answeredGroupQuestions.length
        ? Math.round(groupTotal / answeredGroupQuestions.length * 20)
        : 0;
      aspects[group.code] = {};
      for (var aspect = 1; aspect <= 5; aspect += 1) {
        var aspectQuestions = groupQuestions.filter(function (question) { return question.aspect === aspect && state.answers[question.id]; });
        var actual = aspectQuestions.reduce(function (sum, question) { return sum + Number(state.answers[question.id]); }, 0);
        aspects[group.code][aspect] = {
          actual: actual,
          answered: aspectQuestions.length,
          converted: aspectQuestions.length ? Math.round(actual / aspectQuestions.length * 20) : 0
        };
      }
    });
    var ranking = GROUPS.map(function (group) { return group.code; }).sort(function (a, b) { return scores[b] - scores[a] || a.localeCompare(b); });
    var answered = totalAnswered();
    return {
      code: ranking.slice(0, 3).join(''),
      scores: scores,
      aspects: aspects,
      answered: answered,
      totalQuestions: TOTAL_QUESTIONS,
      completion: Math.round(answered / TOTAL_QUESTIONS * 100),
      completedAt: new Date().toISOString()
    };
  }
  function persistResult(result) {
    state.result = result;
    try { localStorage.setItem('axis_riasec_result:' + signedInId(), JSON.stringify(result)); } catch (error) {}
    if (window.AxisData && window.AxisData.setProfileValue) {
      window.AxisData.setProfileValue('riasecResult', result);
      window.AxisData.setProfileValue('riasecScores', result.scores);
      window.AxisData.setProfileValue('hollandCode', result.code);
      window.AxisData.setProfileValue('personality', buildPersonality(result));
      window.AxisData.setProfileValue('riasecProgress', {
        answered: result.answered,
        total: result.totalQuestions,
        completion: result.completion,
        completedAt: result.completedAt
      });
      if (window.AxisData.saveProfile && window.AxisAuth && window.AxisAuth.isSignedIn()) {
        return window.AxisData.saveProfile().then(function () {
          return syncCareerMatches();
        }).catch(function (error) {
          var status = $('draftStatus');
          if (status) status.textContent = 'Đã lưu trên thiết bị; chưa đồng bộ máy chủ: ' + error.message;
        });
      }
    }
    return Promise.resolve();
  }
  function buildPersonality(result) {
    return result.code.split('').map(function (code) {
      var group = GROUPS.find(function (item) { return item.code === code; });
      return group ? group.name + ': ' + group.description : '';
    }).join(' ');
  }
  function showResult() {
    var result = calculateResult();
    state.result = result;
    persistResult(result).then(function () {
      if (result.completion >= MIN_EVALUATION_COMPLETION * 100 && state.result === result) requestRiasecEvaluation(result);
    });
    renderResult(result);
  }
  function renderResult(result) {
    var isEligible = renderEvaluationState(result);
    $('hollandCode').textContent = result.code;
    $('resultTitle').textContent = 'Bạn nổi bật ở nhóm ' + result.code;
    $('resultSummary').textContent = result.code.split('').map(function (code) { return GROUPS.find(function (group) { return group.code === code; }).description; }).join(' ');
    if (!isEligible) {
      $('hollandCode').textContent = '—';
      $('resultTitle').textContent = 'Chưa đủ dữ liệu để đánh giá';
      $('resultSummary').textContent = 'Kết quả tạm thời chưa được dùng để kết luận tính cách hoặc mức độ phù hợp với nhóm ngành.';
    }
    $('scoreList').innerHTML = GROUPS.slice().sort(function (a, b) { return result.scores[b.code] - result.scores[a.code]; }).map(function (group) {
      var score = result.scores[group.code];
      return '<div class="riasec-score-row"><span><strong>' + group.code + '</strong> ' + group.name + '</span><b>' + score + '/100</b><i><em style="width:' + score + '%"></em></i></div>';
    }).join('');
    $('aspectList').innerHTML = result.code.split('').map(function (code) {
      var best = Object.keys(result.aspects[code]).sort(function (a, b) { return result.aspects[code][b].converted - result.aspects[code][a].converted; })[0];
      return '<div class="riasec-aspect-row"><strong>' + code + ' · Khía cạnh ' + best + '</strong><span>' + result.aspects[code][best].converted + '/100 quy đổi</span></div>';
    }).join('');
    if (result.aiEvaluation) {
      $('riasecAiOverall').textContent = result.aiEvaluation.overall || '';
      $('riasecAiDirection').textContent = result.aiEvaluation.direction || '';
      $('riasecAiSummary').textContent = result.aiEvaluation.summary || '';
      $('riasecEvaluationNotice').textContent = 'Đã khôi phục kết quả đánh giá đã lưu.';
    } else if (!isEligible) {
      $('riasecAiOverall').textContent = '';
      $('riasecAiDirection').textContent = '';
      $('riasecAiSummary').textContent = '';
    }
    renderCareerMatches(Array.isArray(result.careerMatches) ? result.careerMatches : []);
    setVisibility('riasecQuestionnaire', false);
    setVisibility('riasecResult', true);
  }
  function readSavedResult() {
    try {
      var result = JSON.parse(localStorage.getItem('axis_riasec_result:' + signedInId()) || 'null');
      if (!result && signedInId() !== 'guest' && window.AxisData && window.AxisData.getProfile) {
        result = window.AxisData.getProfile().riasecResult || null;
      }
      if (!result || !/^[RIASEC]{3}$/.test(result.code || '') || !result.scores || !result.aspects) return null;
      if (!GROUPS.every(function (group) {
        return Number.isFinite(Number(result.scores[group.code])) &&
          result.aspects[group.code] && Array.from({ length: ASPECTS_PER_GROUP }, function (_, index) {
            return result.aspects[group.code][String(index + 1)] && Number.isFinite(Number(result.aspects[group.code][String(index + 1)].converted));
          }).every(Boolean);
      })) return null;
      return result;
    } catch (error) {
      return null;
    }
  }
  function restoreSavedResult() {
    var savedResult = readSavedResult();
    if (savedResult) {
      if (state.result && state.result.completedAt === savedResult.completedAt) return;
      state.result = savedResult;
      renderResult(savedResult);
      return;
    }
    if (state.result) {
      state.result = null;
      setVisibility('riasecResult', false);
      setVisibility('riasecWelcome', true);
      setVisibility('riasecQuestionnaire', false);
    }
  }
  function renderEvaluationState(result) {
    var notice = $('riasecEvaluationNotice');
    var matches = $('riasecCareerMatches');
    var aiEvaluation = $('riasecAiEvaluation');
    if (result.completion < MIN_EVALUATION_COMPLETION * 100) {
      notice.className = 'riasec-evaluation-notice';
      notice.textContent = 'Chưa thể đánh giá đáng tin cậy vì bạn mới hoàn thành ' + result.completion + '% bài làm. Hãy trả lời thêm ít nhất ' + Math.ceil(MIN_EVALUATION_COMPLETION * TOTAL_QUESTIONS) + '/' + TOTAL_QUESTIONS + ' câu để nhận phân tích tính cách và mức độ phù hợp ngành.';
      matches.classList.add('hidden');
      if (aiEvaluation) aiEvaluation.classList.add('hidden');
      $('riasecResultDetails').classList.add('hidden');
      return false;
    }
    notice.className = 'riasec-evaluation-notice is-ready';
    notice.textContent = 'Điểm Holland đã được tính từ câu trả lời. Đang chuẩn bị nhận xét AI về điểm số và các khía cạnh.';
    if (aiEvaluation) aiEvaluation.classList.remove('hidden');
    matches.classList.remove('hidden');
    $('riasecResultDetails').classList.remove('hidden');
    return true;
  }
  function requestRiasecEvaluation(result) {
    var overall = $('riasecAiOverall');
    var direction = $('riasecAiDirection');
    var summary = $('riasecAiSummary');
    if (direction) direction.textContent = '';
    if (summary) summary.textContent = '';
    if (!window.AxisAuth || !window.AxisAuth.isSignedIn() || !window.AxisAuth.apiRequest) {
      $('riasecEvaluationNotice').textContent = 'Mã Holland đã được tính. Đăng nhập để nhận nhận xét AI về điểm số và các khía cạnh.';
      return;
    }
    if (overall) overall.textContent = 'Đang phân tích điểm số và khía cạnh...';
    window.AxisAuth.apiRequest('/ai/riasec-evaluation', {
      method: 'POST',
      body: JSON.stringify({
        scores: result.scores,
        aspect_scores: Object.keys(result.aspects).reduce(function (groups, code) {
          groups[code] = Object.keys(result.aspects[code]).reduce(function (aspects, aspect) {
            aspects[aspect] = result.aspects[code][aspect].converted;
            return aspects;
          }, {});
          return groups;
        }, {}),
        aspect_answered: Object.keys(result.aspects).reduce(function (groups, code) {
          groups[code] = Object.keys(result.aspects[code]).reduce(function (aspects, aspect) {
            aspects[aspect] = result.aspects[code][aspect].answered;
            return aspects;
          }, {});
          return groups;
        }, {}),
        completion: result.completion
      })
    }, 65000).then(function (evaluation) {
      if (state.result !== result) return;
      if (overall) overall.textContent = evaluation.overall;
      if (direction) direction.textContent = evaluation.direction;
      if (summary) summary.textContent = evaluation.summary;
      result.aiEvaluation = evaluation;
      try { localStorage.setItem('axis_riasec_result:' + signedInId(), JSON.stringify(result)); } catch (error) {}
      if (window.AxisData && window.AxisData.setProfileValue) {
        window.AxisData.setProfileValue('riasecResult', result);
        return window.AxisData.saveProfile ? window.AxisData.saveProfile() : undefined;
      }
      return undefined;
    }).catch(function (error) {
      if (state.result !== result) return;
      if (overall) overall.textContent = 'Chưa thể tạo nhận xét AI: ' + error.message;
      if (direction) direction.textContent = '';
      if (summary) summary.textContent = '';
    });
  }
  function syncCareerMatches() {
    if (!window.AxisAuth || !window.AxisAuth.isSignedIn() || !window.AxisAuth.apiRequest) return Promise.resolve();
    return window.AxisAuth.apiRequest('/assessments/run', { method: 'POST' }).then(function (matchResult) {
      var matches = matchResult && (matchResult.top5 || matchResult.results);
      if (!Array.isArray(matches)) return;
      state.result.careerMatches = matches.slice(0, 5);
      try { localStorage.setItem('axis_riasec_result:' + signedInId(), JSON.stringify(state.result)); } catch (error) {}
      if (window.AxisData && window.AxisData.setProfileValue) {
        window.AxisData.setProfileValue('careerMatches', matches.slice(0, 5));
        return window.AxisData.saveProfile ? window.AxisData.saveProfile() : undefined;
      }
      return undefined;
    }).then(function () {
      renderCareerMatches(state.result.careerMatches || []);
    }).catch(function (error) {
      renderCareerMatches([]);
      var notice = $('riasecEvaluationNotice');
      notice.textContent += ' Chưa tải được kết quả ngành từ máy chủ: ' + error.message;
    });
  }
  function renderCareerMatches(matches) {
    var list = $('careerMatchList');
    if (!list || !matches.length) return;
    list.innerHTML = matches.map(function (item) {
      var score = Number(item.score || item.match_score || 0);
      return '<article class="riasec-career-match"><div><strong>' + item.name + '</strong><span>' + (item.code || '') + '</span></div><b>' + score.toFixed(1) + '%</b><i><em style="width:' + Math.max(0, Math.min(100, score)) + '%"></em></i></article>';
    }).join('');
  }
  function start() {
    loadDraft();
    if (!state.draftLoaded) rememberSelectedQuestions();
    setVisibility('riasecWelcome', false);
    setVisibility('riasecQuestionnaire', true);
    renderQuestion();
  }
  function next() {
    var groupQuestions = state.bank[GROUPS[state.groupIndex].code];
    var unanswered = groupQuestions.filter(function (question) { return !state.answers[question.id]; });
    if (unanswered.length) {
      alert('Bạn hãy trả lời đủ ' + QUESTIONS_PER_GROUP + ' câu trong nhóm trước khi tiếp tục.');
      var firstUnanswered = $('questionList').querySelector('.riasec-question:nth-child(' + (groupQuestions.indexOf(unanswered[0]) + 1) + ')');
      if (firstUnanswered) firstUnanswered.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }
    if (state.groupIndex < 5) {
      state.groupIndex += 1;
      saveDraft(true);
      renderQuestion();
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }
    showResult();
  }
  async function init() {
    if (!$('riasecApp') || !$('startRiasec') || !$('questionList') || !$('submitModal')) return;
    $('startRiasec').disabled = true;
    try {
      var response = await fetch('../cauhoi.txt', { cache: 'no-store' });
      if (!response.ok) throw new Error('Không thể tải ngân hàng câu hỏi.');
      var parsedBank = parseQuestionBank(await response.text());
      state.sourceBank = parsedBank.source;
      state.bank = parsedBank.selected;
      var valid = GROUPS.every(function (group) {
        return state.bank[group.code].length === QUESTIONS_PER_GROUP &&
          Array.from({ length: ASPECTS_PER_GROUP }, function (_, index) {
            return state.bank[group.code].filter(function (question) { return question.aspect === index + 1; }).length;
          }).every(function (count) { return count === QUESTIONS_PER_ASPECT; });
      });
      if (!valid) throw new Error('Ngân hàng câu hỏi chưa đủ 6 nhóm RIASEC.');
      $('riasecLoadStatus').textContent = 'Đã sẵn sàng. Bạn có thể bắt đầu bất cứ lúc nào.';
      $('startRiasec').disabled = false;
    } catch (error) {
      $('riasecLoadStatus').textContent = error.message;
    }
    $('startRiasec').addEventListener('click', start);
    $('nextGroup').addEventListener('click', next);
    $('submitRiasec').addEventListener('click', openSubmitDialog);
    $('confirmSubmit').addEventListener('click', submitTest);
    $('cancelSubmit').addEventListener('click', closeSubmitDialog);
    $('submitModal').querySelector('[data-close-submit]').addEventListener('click', closeSubmitDialog);
    $('toggleRiasecControls').addEventListener('click', toggleControls);
    document.addEventListener('keydown', handleSubmitKeydown);
    window.addEventListener('beforeunload', function (event) {
      if (totalAnswered() === 0 || state.result) return;
      event.preventDefault();
      event.returnValue = 'Bạn chưa nộp bài RIASEC. Bạn có muốn rời trang không?';
      return event.returnValue;
    });
    $('retakeRiasec').addEventListener('click', function () {
      state.answers = {}; state.groupIndex = 0; state.result = null; state.draftLoaded = false;
      state.bank = selectQuestions(state.sourceBank);
      try { localStorage.removeItem(keyForUser()); } catch (error) {}
      start();
    });
    restoreSavedResult();
    document.addEventListener('axis:auth-state', restoreSavedResult);
    document.addEventListener('axis:profile-hydrated', restoreSavedResult);
  }
  document.addEventListener('DOMContentLoaded', init);
}());
