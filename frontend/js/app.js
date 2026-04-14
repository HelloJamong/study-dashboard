import { api } from './api.js';
import { renderMarkdown } from './markdown.js';
import { state } from './state.js';
import { $, $$, esc, fmtTime } from './utils.js';

// ═══════════════════════════════════════════════════════════════
// 페이지 라우팅
// ═══════════════════════════════════════════════════════════════
function navigate(page) {
  state.currentPage = page;

  // 페이지 전환
  $$('.page', $('#app-shell')).forEach(p => p.classList.add('hidden'));
  const target = $(`#page-${page}`);
  if (target) { target.classList.remove('hidden'); target.classList.add('fade-in'); }

  // 사이드바 활성 상태
  const activePage = ['course-detail', 'summary-detail'].includes(page) ? 'courses' : page;
  $$('.nav-item').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.page === activePage);
  });

  // 페이지별 초기화
  if (page === 'courses') {
    loadTerms();
    if (state.selectedTerm === null && state.courses.length === 0) loadCourses();
    if (state.selectedTerm !== null) loadSummaryTerm(state.selectedTerm);
  }
  if (page === 'settings') loadSettings();
  if (page === 'dashboard') loadStats();
}

// ═══════════════════════════════════════════════════════════════
// 인증
// ═══════════════════════════════════════════════════════════════
async function checkAuth() {
  try {
    const res = await api('GET', '/api/auth/status');
    if (res.authenticated) {
      showApp(res.user_id);
    } else {
      showLogin();
    }
  } catch {
    showLogin();
  }
}

function showLogin() {
  $('#page-login').classList.remove('hidden');
  $('#app-shell').classList.add('hidden');
  $('#input-user-id').value = '';
  $('#input-password').value = '';
  $('#login-error').classList.add('hidden');
  stopPolling();
  stopAutoPolling();
  stopAllDownloadTaskPolling();
}

function applySettingsVisibility(form = $('#settings-form')) {
  if (!form) return;
  const downloadEnabled = form.elements.DOWNLOAD_ENABLED?.checked ?? state.settings.DOWNLOAD_ENABLED === 'true';
  const autoDownload = downloadEnabled && (form.elements.AUTO_DOWNLOAD_AFTER_PLAY?.checked ?? state.settings.AUTO_DOWNLOAD_AFTER_PLAY === 'true');
  const downloadOptions = $('#download-options');
  const sttSection = $('#stt-settings-section');
  const aiSection = $('#ai-settings-section');

  if (downloadOptions) {
    downloadOptions.classList.toggle('opacity-50', !downloadEnabled);
    $$('input, select', downloadOptions).forEach(el => { el.disabled = !downloadEnabled; });
  }
  if (form.elements.AUTO_DOWNLOAD_AFTER_PLAY) {
    form.elements.AUTO_DOWNLOAD_AFTER_PLAY.disabled = !downloadEnabled;
    if (!downloadEnabled) form.elements.AUTO_DOWNLOAD_AFTER_PLAY.checked = false;
  }
  [sttSection, aiSection].forEach(section => {
    if (section) section.classList.toggle('hidden', !autoDownload);
  });
  if (!autoDownload) {
    if (form.elements.STT_ENABLED) form.elements.STT_ENABLED.checked = false;
    if (form.elements.AI_ENABLED) form.elements.AI_ENABLED.checked = false;
  }
}

async function loadAppSettings() {
  const settings = await api('GET', '/api/settings');
  state.settings = { ...state.settings, ...settings };
  state.settingsLoaded = true;
  return state.settings;
}

function showApp(userId) {
  state.userId = userId;
  $('#page-login').classList.add('hidden');
  $('#app-shell').classList.remove('hidden');
  $('#sidebar-user-id').textContent = userId;
  loadAppSettings().catch(() => {});
  navigate('dashboard');
  startPolling();
  startAutoPolling();
}

// 로그인 폼
$('#login-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const userId = $('#input-user-id').value.trim();
  const password = $('#input-password').value;
  if (!userId || !password) {
    $('#login-error').textContent = '학번과 비밀번호를 모두 입력하세요.';
    $('#login-error').classList.remove('hidden');
    return;
  }

  const btn = $('#btn-login');
  btn.disabled = true;
  btn.textContent = '로그인 중...';
  $('#login-error').classList.add('hidden');

  try {
    const res = await api('POST', '/api/auth/login', { user_id: userId, password }, 60000);
    showApp(res.user_id);
  } catch (err) {
    $('#login-error').textContent = err.message;
    $('#login-error').classList.remove('hidden');
    alert(err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = '로그인';
  }
});

// 로그아웃
$('#btn-logout').addEventListener('click', async () => {
  await api('POST', '/api/auth/logout').catch(() => {});
  state.courses = [];
  showLogin();
});

// ═══════════════════════════════════════════════════════════════
// 재생 폴링
// ═══════════════════════════════════════════════════════════════
function startPolling() {
  stopPolling();
  updatePlayerUI(); // 즉시 1회
  state.pollingTimer = setInterval(updatePlayerUI, 2000);
}

function stopPolling() {
  if (state.pollingTimer) { clearInterval(state.pollingTimer); state.pollingTimer = null; }
}

async function updatePlayerUI() {
  try {
    const s = await api('GET', '/api/player/status');
    const active = $('#player-active');
    const idle = $('#player-idle');
    const message = $('#player-message');
    const messageTitle = $('#player-message-title');
    const messageBody = $('#player-message-body');
    const messageLog = $('#player-message-log');
    const status = s.status || (s.is_playing ? 'playing' : 'idle');
    const previousStatus = state.lastPlayerStatus;
    state.lastPlayerStatus = status;

    if (s.is_playing) {
      active.classList.remove('hidden');
      idle.classList.add('hidden');
      message.classList.add('hidden');
      $('#player-course-name').textContent = s.course_name || '';
      $('#player-lecture-title').textContent = s.lecture_title || '';
      $('#player-week').textContent = s.week_label || '';
      $('#player-pct').childNodes[0].textContent = Math.round(s.progress_pct);
      $('#player-time').textContent = `${fmtTime(s.current)} / ${fmtTime(s.duration)}`;
      $('#player-bar').style.width = `${s.progress_pct}%`;
    } else {
      active.classList.add('hidden');
      idle.classList.remove('hidden');
      $('#player-bar').style.width = '0%';

      message.classList.add('hidden');
      messageTitle.textContent = '';
      messageBody.textContent = '';
      messageLog.classList.add('hidden');
      messageLog.textContent = '';

      if (s.error) {
        message.className = 'mt-5 px-4 py-3 rounded-xl border text-sm bg-red-500/10 border-red-500/30 text-red-300';
        messageTitle.textContent = '재생 실패';
        messageBody.textContent = s.error;
        if (s.log_path) {
          messageLog.textContent = `로그 저장: ${s.log_path}`;
          messageLog.classList.remove('hidden');
        }
      } else if (status === 'completed' && s.lecture_title) {
        message.className = 'mt-5 px-4 py-3 rounded-xl border text-sm bg-emerald-500/10 border-emerald-500/30 text-emerald-300';
        messageTitle.textContent = '재생 완료';
        messageBody.textContent = `${s.lecture_title} 강의 재생이 완료되었습니다.`;
        if (s.refresh_recommended) {
          messageLog.textContent = '강의 목록이 자동으로 업데이트되지 않았습니다. 강의 목록 탭의 새로고침 버튼을 눌러주세요.';
          messageLog.classList.remove('hidden');
        }
      } else if (status === 'stopped' && s.lecture_title) {
        message.className = 'mt-5 px-4 py-3 rounded-xl border text-sm bg-amber-500/10 border-amber-500/30 text-amber-300';
        messageTitle.textContent = '재생 중지됨';
        messageBody.textContent = `${s.lecture_title} 강의 재생이 중지되었습니다.`;
      }

      if (!messageTitle.textContent && !messageBody.textContent) {
        message.classList.add('hidden');
      } else {
        message.classList.remove('hidden');
      }
    }

    if (previousStatus === 'playing' && status === 'completed') {
      loadStats();
      state.courses = [];
      if (state.currentPage === 'courses') loadCourses();
      if (
        state.settings.DOWNLOAD_ENABLED === 'true' &&
        state.settings.AUTO_DOWNLOAD_AFTER_PLAY === 'true' &&
        s.course_id &&
        s.lecture_url &&
        state.autoDownloadStartedFor !== s.lecture_url
      ) {
        state.autoDownloadStartedFor = s.lecture_url;
        startAutoDownloadAfterPlayback(s, messageLog);
      }
    }
  } catch {}
}

// 재생 중지
$('#btn-stop').addEventListener('click', async () => {
  await api('POST', '/api/player/stop').catch(() => {});
  updatePlayerUI();
});

// ═══════════════════════════════════════════════════════════════
// 통계
// ═══════════════════════════════════════════════════════════════
async function loadStats() {
  try {
    const s = await api('GET', '/api/courses/stats');
    // 백엔드 details가 비어있으면(total=0) 아직 강의 목록이 로드되지 않은 것
    if (s.total_videos === 0 && state.courses.length === 0) {
      const courses = await api('GET', '/api/courses');
      state.courses = courses;
      const s2 = await api('GET', '/api/courses/stats');
      $('#stat-completed').textContent = s2.completed_videos;
      $('#stat-total').textContent = s2.total_videos;
      $('#stat-pending').textContent = s2.total_videos - s2.completed_videos;
      return;
    }
    $('#stat-completed').textContent = s.completed_videos;
    $('#stat-total').textContent = s.total_videos;
    $('#stat-pending').textContent = s.total_videos - s.completed_videos;
  } catch {}
}

// ═══════════════════════════════════════════════════════════════
// 학기 선택
// ═══════════════════════════════════════════════════════════════
async function loadTerms() {
  try {
    const { current_term, past_terms } = await api('GET', '/api/courses/terms');
    state.currentTerm = current_term;

    if (past_terms.length === 0) {
      $('#term-selector').classList.add('hidden');
      return;
    }

    const tabs = $('#term-tabs');
    tabs.innerHTML = '';
    const allTerms = [
      { label: current_term || '현재 학기', value: null },
      ...past_terms.map(t => ({ label: t, value: t })),
    ];
    allTerms.forEach(({ label, value }) => {
      const btn = document.createElement('button');
      const active = value === state.selectedTerm;
      btn.className = `term-tab px-4 py-2 rounded-xl text-sm font-medium transition-all border ${
        active
          ? 'bg-indigo-500 text-white border-indigo-500'
          : 'bg-slate-800 text-slate-400 border-slate-700 hover:border-indigo-500/50'
      }`;
      btn.textContent = label;
      btn.dataset.term = value ?? '';
      btn.addEventListener('click', () => switchTerm(value));
      tabs.appendChild(btn);
    });
    $('#term-selector').classList.remove('hidden');
  } catch {}
}

function _updateTermTabs() {
  $$('.term-tab').forEach(btn => {
    const active = (btn.dataset.term || null) === state.selectedTerm;
    btn.className = `term-tab px-4 py-2 rounded-xl text-sm font-medium transition-all border ${
      active
        ? 'bg-indigo-500 text-white border-indigo-500'
        : 'bg-slate-800 text-slate-400 border-slate-700 hover:border-indigo-500/50'
    }`;
  });
}

function switchTerm(term) {
  state.selectedTerm = term;
  _updateTermTabs();
  if (term === null) {
    state.courses = [];
    loadCourses();
  } else {
    loadSummaryTerm(term);
  }
}

function loadSummaryTerm(term) {
  const list = $('#courses-list');
  list.innerHTML = `
    <div class="flex flex-col items-center justify-center py-16 text-center">
      <div class="w-14 h-14 bg-slate-800 rounded-2xl flex items-center justify-center mb-4">
        <i class="fa-solid fa-folder-open text-slate-500 text-xl"></i>
      </div>
      <p class="font-semibold text-slate-300">${esc(term)}</p>
      <p class="text-sm text-slate-500 mt-1">요약 기능 구현 후 이 학기의 강의 요약을 여기서 볼 수 있습니다.</p>
    </div>
  `;
}

// ═══════════════════════════════════════════════════════════════
// 강의 목록
// ═══════════════════════════════════════════════════════════════
async function loadCourses() {
  const list = $('#courses-list');
  const loading = $('#courses-loading');
  list.innerHTML = '';
  loading.classList.remove('hidden');
  loading.classList.add('flex');

  try {
    state.courses = await api('GET', '/api/courses');
    renderCourseCards(state.courses);
  } catch (err) {
    list.innerHTML = `<p class="text-red-400 text-sm">${esc(err.message)}</p>`;
  } finally {
    loading.classList.add('hidden');
    loading.classList.remove('flex');
  }
}

function renderCourseCards(courses) {
  const list = $('#courses-list');
  list.innerHTML = '';

  if (courses.length === 0) {
    list.innerHTML = '<p class="text-slate-400 text-sm text-center py-12">수강 중인 과목이 없습니다.</p>';
    return;
  }

  courses.forEach(course => {
    const pending = course.pending_videos;
    const total = course.total_videos;
    const pct = total > 0 ? Math.round((total - pending) / total * 100) : 0;

    const card = document.createElement('div');
    card.className = 'bg-[#1E293B] rounded-2xl border border-slate-700 p-5 cursor-pointer hover:border-indigo-500/50 transition-all';
    card.setAttribute('role', 'button');
    card.setAttribute('tabindex', '0');
    card.setAttribute('aria-label', `${course.name} 주차별 강의 보기`);
    card.innerHTML = `
      <div class="flex items-start justify-between gap-4">
        <div class="flex-1 min-w-0">
          <h3 class="font-semibold text-white truncate">${esc(course.name)}</h3>
          <p class="text-xs text-slate-500 mt-0.5">${esc(course.term)}</p>
        </div>
        <div class="shrink-0 text-right">
          <span class="text-lg font-black ${pending > 0 ? 'text-amber-400' : 'text-emerald-400'}">${pending}</span>
          <span class="text-slate-500 text-xs"> 미수강</span>
        </div>
      </div>
      <div class="mt-4">
        <div class="flex justify-between text-xs text-slate-500 mb-1.5">
          <span>진행률</span><span>${total - pending} / ${total}</span>
        </div>
        <div class="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
          <div class="h-full ${pct === 100 ? 'bg-emerald-500' : 'bg-indigo-500'} rounded-full transition-all" style="width:${pct}%"></div>
        </div>
      </div>
    `;
    const openDetail = () => loadCourseDetail(course.id, course.name);
    card.addEventListener('click', openDetail);
    card.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        openDetail();
      }
    });
    list.appendChild(card);
  });
}

async function loadCourseDetail(courseId, courseName) {
  const weeks = $('#detail-weeks');
  const settings = await loadAppSettings().catch(() => state.settings);
  state.currentCourseId = courseId;
  state.currentCourseName = courseName;
  navigate('course-detail');
  weeks.innerHTML = '<div class="p-6 text-slate-400 text-sm"><i class="fa-solid fa-spinner fa-spin mr-2"></i>불러오는 중...</div>';
  $('#detail-course-name').textContent = courseName;
  $('#detail-professors').textContent = '';

  try {
    const data = await api('GET', `/api/courses/${courseId}`);
    if (state.currentCourseId !== courseId) return;
    $('#detail-professors').textContent = data.professors || '';
    weeks.innerHTML = '';

    if (!data.weeks || data.weeks.length === 0) {
      weeks.innerHTML = '<div class="p-6 text-slate-400 text-sm">강의 정보가 없습니다.</div>';
      return;
    }

    let renderedSections = 0;
    data.weeks.forEach(week => {
      const videos = week.lectures.filter(l => l.is_video);
      if (videos.length === 0) return;
      renderedSections += 1;

      const section = document.createElement('div');
      section.className = 'px-6 py-4';
      section.innerHTML = `
        <div class="flex items-center justify-between mb-3">
          <h4 class="text-sm font-bold text-slate-300">${esc(week.title)}</h4>
          ${week.pending_count > 0 ? `<span class="text-xs px-2 py-0.5 bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded-full">${week.pending_count} 미수강</span>` : ''}
        </div>
        <div class="flex flex-col gap-2" data-week-rows></div>
      `;
      const rowContainer = section.querySelector('[data-week-rows]');
      videos.forEach(lec => {
        const comp = lec.completion === 'completed' ? 'completed' : 'incomplete';
        const row = document.createElement('div');
        row.className = 'lecture-row flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all cursor-pointer';
        row.dataset.url = lec.full_url;
        row.dataset.title = lec.title;
        row.dataset.week = lec.week_label;
        row.dataset.course = courseId;
        row.innerHTML = `
          <div class="w-7 h-7 rounded-lg ${comp === 'completed' ? 'bg-emerald-500/10' : 'bg-slate-800'} flex items-center justify-center shrink-0">
            <i class="fa-solid ${comp === 'completed' ? 'fa-circle-check text-emerald-400' : 'fa-play text-slate-500'} text-xs"></i>
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-sm text-slate-200 truncate"></p>
            ${lec.duration ? `<p class="text-xs text-slate-500"></p>` : ''}
          </div>
          <span class="completion-badge ${comp} shrink-0 text-xs px-2 py-0.5 border rounded-full font-medium">
            ${comp === 'completed' ? '완료' : '미수강'}
          </span>
          <div class="shrink-0 flex items-center gap-2" data-actions></div>
        `;
        row.querySelector('.flex-1 p:first-child').textContent = lec.title;
        if (lec.duration) row.querySelector('.flex-1 p:last-child').textContent = lec.duration;
        const actions = row.querySelector('[data-actions]');
        if (lec.needs_watch) {
          const playBtn = document.createElement('button');
          playBtn.className = 'btn-play-lec px-3 py-1 bg-indigo-500 hover:bg-indigo-400 text-white text-xs font-bold rounded-lg transition-all';
          playBtn.textContent = '재생';
          actions.appendChild(playBtn);
        }
        if (settings.DOWNLOAD_ENABLED === 'true') {
          const downloadBtn = document.createElement('button');
          downloadBtn.className = 'btn-download-lec px-3 py-1 bg-sky-500 hover:bg-sky-400 text-white text-xs font-bold rounded-lg transition-all';
          downloadBtn.textContent = '영상 다운로드';
          actions.appendChild(downloadBtn);
          const downloadStatus = document.createElement('span');
          downloadStatus.className = 'download-status hidden text-xs text-slate-400';
          actions.appendChild(downloadStatus);
        }
        if (comp === 'completed' && lec.summary && lec.summary.available && lec.summary.id) {
          row.dataset.summaryId = lec.summary.id;
          const summaryBtn = document.createElement('button');
          summaryBtn.className = 'btn-summary-lec px-3 py-1 bg-emerald-500 hover:bg-emerald-400 text-white text-xs font-bold rounded-lg transition-all';
          summaryBtn.textContent = '요약 내용 보기';
          actions.appendChild(summaryBtn);
        }
        rowContainer.appendChild(row);
      });
      weeks.appendChild(section);
    });

    if (renderedSections === 0) {
      weeks.innerHTML = '<div class="p-6 text-slate-400 text-sm">표시할 영상 강의가 없습니다.</div>';
      return;
    }

    // 재생 버튼 이벤트
    $$('.btn-play-lec', weeks).forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const row = btn.closest('.lecture-row');
        await playLecture(row.dataset.course, row.dataset.url, row.dataset.title, row.dataset.week);
      });
    });
    $$('.btn-download-lec', weeks).forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const row = btn.closest('.lecture-row');
        await startDownload(row, btn);
      });
    });
    $$('.btn-summary-lec', weeks).forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const row = btn.closest('.lecture-row');
        await openSummary(row.dataset.summaryId, row.dataset.title, row.dataset.week);
      });
    });

  } catch (err) {
    if (state.currentCourseId === courseId) {
      weeks.innerHTML = `<div class="p-6 text-red-400 text-sm">${esc(err.message)}</div>`;
    }
  }
}

function setDownloadStatus(row, message, tone = 'slate') {
  const status = row.querySelector('.download-status');
  if (!status) return;
  const toneClass = {
    slate: 'text-slate-400',
    sky: 'text-sky-400',
    emerald: 'text-emerald-400',
    amber: 'text-amber-400',
    red: 'text-red-400',
  }[tone] || 'text-slate-400';
  status.textContent = message;
  status.className = `download-status text-xs ${toneClass}`;
}

function stopDownloadTaskPolling(taskId) {
  if (state.downloadTaskTimers[taskId]) {
    clearInterval(state.downloadTaskTimers[taskId]);
    delete state.downloadTaskTimers[taskId];
  }
}

function stopAllDownloadTaskPolling() {
  Object.keys(state.downloadTaskTimers).forEach(stopDownloadTaskPolling);
}

function updateDownloadButton(button, text, disabled) {
  button.textContent = text;
  button.disabled = disabled;
  button.classList.toggle('opacity-60', disabled);
  button.classList.toggle('cursor-not-allowed', disabled);
}

async function pollDownloadTask(taskId, row, button) {
  try {
    const task = await api('GET', `/api/tasks/${taskId}`);
    const pct = Number.isFinite(task.progress_pct) ? ` ${Math.round(task.progress_pct)}%` : '';
    if (task.status === 'completed') {
      stopDownloadTaskPolling(taskId);
      const files = task.result?.files || [];
      const fileText = files.length ? `완료: ${files.map(f => f.type).join(', ')}` : '다운로드 완료';
      setDownloadStatus(row, fileText, 'emerald');
      updateDownloadButton(button, '다시 다운로드', false);
      return;
    }
    if (task.status === 'failed') {
      stopDownloadTaskPolling(taskId);
      setDownloadStatus(row, task.error || '다운로드 실패', 'red');
      updateDownloadButton(button, '재시도', false);
      return;
    }
    if (task.status === 'cancelled') {
      stopDownloadTaskPolling(taskId);
      setDownloadStatus(row, '다운로드가 취소되었습니다.', 'amber');
      updateDownloadButton(button, '다운로드', false);
      return;
    }
    setDownloadStatus(row, `${task.message || '다운로드 중...'}${pct}`, 'sky');
  } catch (err) {
    stopDownloadTaskPolling(taskId);
    setDownloadStatus(row, err.message, 'red');
    updateDownloadButton(button, '재시도', false);
  }
}

async function startDownload(row, button) {
  try {
    updateDownloadButton(button, '시작 중...', true);
    setDownloadStatus(row, '다운로드 작업을 준비하는 중입니다.', 'sky');
    const taskId = await startDownloadPayload({
      course_id: row.dataset.course,
      lecture_url: row.dataset.url,
      lecture_title: row.dataset.title,
      week_label: row.dataset.week,
    });
    row.dataset.downloadTaskId = taskId;
    updateDownloadButton(button, '다운로드 중', true);
    await pollDownloadTask(taskId, row, button);
    stopDownloadTaskPolling(taskId);
    state.downloadTaskTimers[taskId] = setInterval(() => {
      pollDownloadTask(taskId, row, button);
    }, 1500);
  } catch (err) {
    setDownloadStatus(row, err.message, 'red');
    updateDownloadButton(button, '재시도', false);
  }
}

async function startDownloadPayload(payload) {
  const res = await api('POST', '/api/tasks/download', payload);
  return res.task_id;
}

function startAutoDownloadAfterPlayback(playerStatus, messageLog) {
  messageLog.textContent = '재생 완료 후 자동 다운로드를 시작합니다.';
  messageLog.classList.remove('hidden');

  startDownloadPayload({
    course_id: playerStatus.course_id,
    lecture_url: playerStatus.lecture_url,
    lecture_title: playerStatus.lecture_title,
    week_label: playerStatus.week_label || '',
  }).then(taskId => {
    const update = async () => {
      try {
        const task = await api('GET', `/api/tasks/${taskId}`);
        const pct = Number.isFinite(task.progress_pct) ? ` ${Math.round(task.progress_pct)}%` : '';
        if (task.status === 'completed') {
          stopDownloadTaskPolling(taskId);
          const files = task.result?.files || [];
          const fileText = files.length ? files.map(f => f.type).join(', ') : '파일';
          messageLog.textContent = `자동 다운로드 완료: ${fileText}`;
          return;
        }
        if (task.status === 'failed') {
          stopDownloadTaskPolling(taskId);
          messageLog.textContent = `자동 다운로드 실패: ${task.error || '알 수 없는 오류'}`;
          return;
        }
        if (task.status === 'cancelled') {
          stopDownloadTaskPolling(taskId);
          messageLog.textContent = '자동 다운로드가 취소되었습니다.';
          return;
        }
        messageLog.textContent = `자동 다운로드 중: ${task.message || task.stage}${pct}`;
      } catch (err) {
        stopDownloadTaskPolling(taskId);
        messageLog.textContent = `자동 다운로드 상태 확인 실패: ${err.message}`;
      }
    };
    update();
    stopDownloadTaskPolling(taskId);
    state.downloadTaskTimers[taskId] = setInterval(update, 1500);
  }).catch(err => {
    messageLog.textContent = `자동 다운로드 시작 실패: ${err.message}`;
    messageLog.classList.remove('hidden');
  });
}

async function playLecture(courseId, url, title, weekLabel) {
  try {
    await api('POST', '/api/player/play', {
      course_id: courseId,
      lecture_url: url,
      lecture_title: title,
      week_label: weekLabel,
    });
    navigate('dashboard');
    updatePlayerUI();
  } catch (err) {
    alert(`재생 시작 실패: ${err.message}`);
  }
}

async function openSummary(summaryId, lectureTitle, weekLabel) {
  if (!summaryId) return;
  state.currentSummaryId = summaryId;
  navigate('summary-detail');
  $('#summary-title').textContent = lectureTitle || '강의 요약';
  $('#summary-meta').textContent = [state.currentCourseName, weekLabel].filter(Boolean).join(' · ');
  $('#summary-content').innerHTML = '<p class="text-slate-400"><i class="fa-solid fa-spinner fa-spin mr-2"></i>요약을 불러오는 중...</p>';

  try {
    const summary = await api('GET', `/api/summaries/${encodeURIComponent(summaryId)}`);
    if (state.currentSummaryId !== summaryId) return;
    $('#summary-title').textContent = summary.title || lectureTitle || '강의 요약';
    renderMarkdown($('#summary-content'), summary.content || '');
  } catch (err) {
    if (state.currentSummaryId === summaryId) {
      $('#summary-content').innerHTML = `<p class="text-red-400 text-sm">${esc(err.message)}</p>`;
    }
  }
}

// 강의 상세에서 목록으로 돌아가기
$('#btn-back-courses').addEventListener('click', () => {
  navigate('courses');
});

// 요약 상세에서 주차별 강의로 돌아가기
$('#btn-back-course-detail').addEventListener('click', () => {
  navigate(state.currentCourseId ? 'course-detail' : 'courses');
});

// 새로고침
$('#btn-refresh').addEventListener('click', async () => {
  const btn = $('#btn-refresh');
  btn.disabled = true;
  try {
    await api('POST', '/api/courses/refresh');
    state.courses = [];
    await loadCourses();
    await loadStats();
  } catch (err) {
    alert(err.message);
  } finally {
    btn.disabled = false;
  }
});

// ═══════════════════════════════════════════════════════════════
// 설정
// ═══════════════════════════════════════════════════════════════
async function loadSettings() {
  try {
    const s = await loadAppSettings();
    const form = $('#settings-form');

    Object.entries(s).forEach(([key, val]) => {
      const el = form.elements[key];
      if (!el) return;
      if (el.type === 'checkbox') {
        el.checked = val === 'true';
      } else {
        el.value = val || '';
      }
    });
    applySettingsVisibility(form);
  } catch {}
}

$('#settings-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = e.target;
  const payload = {};

  new FormData(form); // trigger validation

  $$('input, select', form).forEach(el => {
    if (!el.name) return;
    if (el.type === 'checkbox') {
      payload[el.name] = el.checked ? 'true' : 'false';
    } else if (el.value.trim()) {
      payload[el.name] = el.value.trim();
    }
  });
  if (payload.DOWNLOAD_ENABLED !== 'true') {
    payload.AUTO_DOWNLOAD_AFTER_PLAY = 'false';
    payload.STT_ENABLED = 'false';
    payload.AI_ENABLED = 'false';
  } else if (payload.AUTO_DOWNLOAD_AFTER_PLAY !== 'true') {
    payload.STT_ENABLED = 'false';
    payload.AI_ENABLED = 'false';
  }

  try {
    await api('PUT', '/api/settings', payload);
    await loadAppSettings();
    applySettingsVisibility(form);
    const msg = $('#settings-success');
    msg.classList.remove('hidden');
    setTimeout(() => msg.classList.add('hidden'), 3000);
  } catch (err) {
    alert(`저장 실패: ${err.message}`);
  }
});

['DOWNLOAD_ENABLED', 'AUTO_DOWNLOAD_AFTER_PLAY'].forEach(name => {
  const el = $('#settings-form').elements[name];
  if (el) el.addEventListener('change', () => applySettingsVisibility());
});

// ═══════════════════════════════════════════════════════════════
// 자동 모드
// ═══════════════════════════════════════════════════════════════
function startAutoPolling() {
  stopAutoPolling();
  updateAutoUI();
  state.autoPollingTimer = setInterval(updateAutoUI, 3000);
}

function stopAutoPolling() {
  if (state.autoPollingTimer) { clearInterval(state.autoPollingTimer); state.autoPollingTimer = null; }
}

function updateScheduleLabel(hours) {
  const sorted = [...hours].sort((a, b) => a - b);
  $('#auto-schedule-label').textContent = sorted.map(h => `${String(h).padStart(2,'0')}시`).join('·');
}

async function updateAutoUI() {
  try {
    const s = await api('GET', '/api/auto/status');
    state.autoEnabled = s.enabled;
    state.autoScheduleHours = s.schedule_hours || [9, 13, 18, 23];

    const toggle = $('#toggle-auto');
    if (toggle.checked !== s.enabled) toggle.checked = s.enabled;

    updateScheduleLabel(state.autoScheduleHours);

    const statusRow = $('#auto-status-row');
    if (s.enabled) {
      statusRow.classList.remove('hidden');
      $('#auto-processed').textContent = s.processed_count || 0;
      if (s.current_lecture) {
        $('#auto-current').classList.remove('hidden');
        $('#auto-current-text').textContent = `${s.current_course} · ${s.current_lecture}`;
      } else {
        $('#auto-current').classList.add('hidden');
      }
      if (s.next_run_at) {
        $('#auto-next-row').classList.remove('hidden');
        $('#auto-next').textContent = s.next_run_at;
      } else {
        $('#auto-next-row').classList.add('hidden');
      }
      if (s.error) {
        $('#auto-error').textContent = s.error;
        $('#auto-error').classList.remove('hidden');
      } else {
        $('#auto-error').classList.add('hidden');
      }
    } else {
      statusRow.classList.add('hidden');
    }
  } catch {}
}

$('#toggle-auto').addEventListener('change', async (e) => {
  const enabled = e.target.checked;
  try {
    if (enabled) {
      await api('POST', '/api/auto/start', { schedule_hours: state.autoScheduleHours });
    } else {
      await api('POST', '/api/auto/stop');
    }
    state.autoEnabled = enabled;
    updateAutoUI();
  } catch (err) {
    e.target.checked = !enabled;
    alert(err.message);
  }
});

// ── 스케줄 모달 ───────────────────────────────────────────────
const _SCHEDULE_PRESETS = [
  [12],
  [9, 21],
  [9, 15, 21],
  [9, 13, 18, 23],
  [8, 11, 14, 18, 22],
  [7, 10, 13, 16, 19, 22],
];

let _scheduleSelected = new Set([9, 13, 18, 23]);

function _isPresetActive(hours) {
  if (hours.length !== _scheduleSelected.size) return false;
  return hours.every(h => _scheduleSelected.has(h));
}

function renderScheduleModal() {
  // 빠른 선택 프리셋
  const presetsEl = $('#schedule-presets');
  presetsEl.innerHTML = '';
  _SCHEDULE_PRESETS.forEach((hours, i) => {
    const btn = document.createElement('button');
    const active = _isPresetActive(hours);
    btn.className = `py-1.5 text-xs font-bold rounded-lg border transition-all ${
      active ? 'bg-indigo-500 border-indigo-500 text-white'
             : 'bg-slate-800 border-slate-700 text-slate-300 hover:border-indigo-500/50'
    }`;
    btn.textContent = `${i + 1}회`;
    if (i === 3) btn.textContent += ' ★';
    btn.addEventListener('click', () => {
      _scheduleSelected = new Set(hours);
      renderScheduleModal();
    });
    presetsEl.appendChild(btn);
  });

  // 시간 그리드 (00~23)
  const gridEl = $('#schedule-hours-grid');
  gridEl.innerHTML = '';
  for (let h = 0; h < 24; h++) {
    const btn = document.createElement('button');
    const selected = _scheduleSelected.has(h);
    btn.className = `py-1.5 text-xs font-bold rounded-lg border transition-all ${
      selected ? 'bg-indigo-500 border-indigo-500 text-white'
               : 'bg-slate-800 border-slate-700 text-slate-400 hover:border-indigo-500/50'
    }`;
    btn.textContent = String(h).padStart(2, '0');
    btn.addEventListener('click', () => {
      if (_scheduleSelected.has(h)) {
        if (_scheduleSelected.size > 1) _scheduleSelected.delete(h);
      } else {
        if (_scheduleSelected.size < 6) _scheduleSelected.add(h);
      }
      renderScheduleModal();
    });
    gridEl.appendChild(btn);
  }
}

$('#btn-auto-schedule').addEventListener('click', () => {
  _scheduleSelected = new Set(state.autoScheduleHours);
  renderScheduleModal();
  $('#modal-schedule').classList.remove('hidden');
});

$('#btn-schedule-close').addEventListener('click', () => {
  $('#modal-schedule').classList.add('hidden');
});

$('#modal-schedule').addEventListener('click', (e) => {
  if (e.target === $('#modal-schedule')) $('#modal-schedule').classList.add('hidden');
});

$('#btn-schedule-apply').addEventListener('click', async () => {
  const hours = [..._scheduleSelected].sort((a, b) => a - b);
  state.autoScheduleHours = hours;
  updateScheduleLabel(hours);
  $('#modal-schedule').classList.add('hidden');

  // 자동 모드 실행 중이면 새 스케줄로 재시작
  if (state.autoEnabled) {
    try {
      await api('POST', '/api/auto/stop');
      await api('POST', '/api/auto/start', { schedule_hours: hours });
      updateAutoUI();
    } catch (err) {
      alert(`스케줄 업데이트 실패: ${err.message}`);
    }
  }
});

// ═══════════════════════════════════════════════════════════════
// 내비게이션 이벤트
// ═══════════════════════════════════════════════════════════════
$$('.nav-item').forEach(btn => {
  btn.addEventListener('click', () => navigate(btn.dataset.page));
});

// ═══════════════════════════════════════════════════════════════
// 초기화
// ═══════════════════════════════════════════════════════════════
checkAuth();
