(function () {
  'use strict';
  var state = { month: new Date(new Date().getFullYear(), new Date().getMonth(), 1), tasks: [], selected: new Date() };
  function api(path, options) { return window.AxisAuth.apiRequest(path, options); }
  function dateKey(value) {
    var date = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    return [
      date.getFullYear(),
      String(date.getMonth() + 1).padStart(2, '0'),
      String(date.getDate()).padStart(2, '0')
    ].join('-');
  }
  function setMessage(text, error) { var node = document.getElementById('calendarMessage'); node.textContent = text || ''; node.className = error ? 'calendar-error' : 'calendar-success'; }
  function tasksFor(day) { return state.tasks.filter(function (task) { return task.scheduled_date === day; }); }
  function renderTasks() {
    var day = dateKey(state.selected), tasks = tasksFor(day), list = document.getElementById('taskList');
    document.getElementById('selectedDateLabel').textContent = state.selected.toLocaleDateString('vi-VN', { day: 'numeric', month: 'long', year: 'numeric' });
    list.innerHTML = tasks.length ? tasks.map(function (task) {
      var tag = task.is_ai_generated ? '<span class="task-tag ai">AI Task</span>' : '<span class="task-tag">Thủ công</span>';
      var done = task.status === 'COMPLETED' ? ' checked' : '';
      return '<article class="task-row"><div><strong>' + escapeHtml(task.task_name) + '</strong><p>' + escapeHtml(task.description) + '</p><small>' + task.estimated_time_minutes + ' phút ' + tag + '</small></div><label class="task-status"><input type="checkbox" data-task-id="' + task.task_id + '"' + done + '> Xong</label></article>';
    }).join('') : '<p class="muted">Chưa có task trong ngày này.</p>';
    list.querySelectorAll('[data-task-id]').forEach(function (input) { input.addEventListener('change', function () { updateStatus(input.dataset.taskId, input.checked); }); });
  }
  function renderCalendar() {
    var grid = document.getElementById('calendarGrid'), year = state.month.getFullYear(), month = state.month.getMonth();
    document.getElementById('calendarMonth').textContent = state.month.toLocaleDateString('vi-VN', { month: 'long', year: 'numeric' });
    var first = new Date(year, month, 1), offset = (first.getDay() + 6) % 7, days = new Date(year, month + 1, 0).getDate(), today = dateKey(new Date());
    grid.innerHTML = '';
    for (var i = 0; i < offset; i += 1) grid.appendChild(document.createElement('span'));
    for (var day = 1; day <= days; day += 1) {
      var date = new Date(year, month, day), key = dateKey(date), tasks = tasksFor(key), pending = tasks.filter(function (task) { return task.status !== 'COMPLETED'; });
      var cell = document.createElement('button'); cell.type = 'button'; cell.className = 'calendar-day' + (key === today ? ' today' : '') + (key === dateKey(state.selected) ? ' selected' : '');
      cell.innerHTML = '<strong>' + day + '</strong>' + (pending.length ? '<span class="task-count">' + pending.length + '</span>' : '') + (key < today && pending.length ? '<small>Chưa hoàn thiện</small>' : '');
      cell.addEventListener('click', function (event) { state.selected = new Date(year, month, Number(event.currentTarget.querySelector('strong').textContent)); renderCalendar(); renderTasks(); });
      grid.appendChild(cell);
    }
  }
  function load() {
    return api('/tasks').then(function (data) {
      state.tasks = Array.isArray(data.tasks) ? data.tasks : [];
      renderCalendar();
      renderTasks();
      var movedCount = data.calendar_metadata && data.calendar_metadata.auto_rescheduled_count;
      if (movedCount) setMessage('Đã tự dời ' + movedCount + ' task quá hạn.');
    });
  }
  function updateStatus(id, checked) { return api('/tasks/' + id + '/status', { method: 'PATCH', body: JSON.stringify({ status: checked ? 'COMPLETED' : 'PENDING' }) }).then(load).catch(function (error) { setMessage(error.message, true); }); }
  function escapeHtml(value) { return String(value || '').replace(/[&<>"']/g, function (char) { return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' })[char]; }); }
  function init() {
    var form = document.getElementById('taskForm');
    document.getElementById('previousMonth').onclick = function () { state.month.setMonth(state.month.getMonth() - 1); renderCalendar(); };
    document.getElementById('nextMonth').onclick = function () { state.month.setMonth(state.month.getMonth() + 1); renderCalendar(); };
    document.getElementById('refreshCalendar').onclick = function () { load().catch(function (error) { setMessage(error.message, true); }); };
    document.getElementById('generatePlan').onclick = function () { api('/tasks/generate', { method: 'POST', body: '{}' }).then(function () { setMessage('Đã tạo kế hoạch 3 ngày.'); return load(); }).catch(function (error) { setMessage(error.message, true); }); };
    form.scheduled_date.value = dateKey(new Date());
    form.onsubmit = function (event) { event.preventDefault(); var data = Object.fromEntries(new FormData(form)); data.estimated_time_minutes = Number(data.estimated_time_minutes); api('/tasks', { method: 'POST', body: JSON.stringify(data) }).then(function () { form.reset(); form.scheduled_date.value = dateKey(new Date()); setMessage('Đã thêm task thủ công.'); return load(); }).catch(function (error) { setMessage(error.message, true); }); };
    if (!window.AxisAuth || !window.AxisAuth.isSignedIn()) { setMessage('Vui lòng đăng nhập để sử dụng lịch.', true); return; }
    load().catch(function (error) { setMessage(error.message, true); });
  }
  window.AxisCalendar = { init: init };
}());
