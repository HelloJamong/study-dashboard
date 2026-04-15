import { api } from './api.js';
import { state } from './state.js';
import { $, $$, esc } from './utils.js';

// ═══════════════════════════════════════════════════════════════
// 로그 조회
// ═══════════════════════════════════════════════════════════════
const LOG_TYPE_LABELS = {
  '': '전체 로그',
  auth: '로그인/로그아웃',
  settings: '설정 변경',
  player: '영상 재생',
  download: '다운로드',
  stt: 'STT',
  summary: 'AI 요약',
};

const LOG_EVENT_LABELS = {
  auth: '인증',
  settings: '설정',
  player: '재생',
  download: '다운로드',
  stt: 'STT',
  summary: 'AI 요약',
};

const LOG_ACTION_LABELS = {
  login: '로그인',
  logout: '로그아웃',
  update: '설정 변경',
  play_start: '재생 시작',
  play_complete: '재생 완료',
  play_failed: '재생 실패',
  play_stop: '재생 중지',
  play_stop_request: '중지 요청',
  download_start: '다운로드 시작',
  download_complete: '다운로드 완료',
  download_failed: '다운로드 실패',
  download_unsupported: '다운로드 미지원',
  download_cancel: '다운로드 취소',
  transcribe_complete: 'STT 완료',
  transcribe_failed: 'STT 실패',
  summary_complete: '요약 완료',
  summary_failed: '요약 실패',
};

export function updateLogMenuState(open = state.currentPage === 'logs') {
  const submenu = $('#log-submenu');
  const caret = $('#log-menu-caret');
  if (submenu) submenu.classList.toggle('hidden', !open);
  if (caret) caret.classList.toggle('rotate-180', open);
  $$('.log-filter').forEach(btn => {
    btn.classList.toggle('active', (btn.dataset.logType || '') === state.selectedLogType);
  });
}

function statusBadgeClass(status) {
  if (['success', 'completed'].includes(status)) return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
  if (['failed', 'error'].includes(status)) return 'bg-red-500/10 text-red-400 border-red-500/20';
  if (['started', 'running', 'requested'].includes(status)) return 'bg-sky-500/10 text-sky-400 border-sky-500/20';
  if (['cancelled', 'cancelling'].includes(status)) return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
  return 'bg-slate-700/50 text-slate-300 border-slate-600';
}

function setText(el, text) {
  el.textContent = text ?? '';
  return el;
}

function eventTargetText(event) {
  return [
    event.course_name,
    event.week_label,
    event.lecture_title,
    event.target_type && event.target_id ? `${event.target_type}:${event.target_id}` : '',
  ].filter(Boolean).join(' · ') || '—';
}

function eventMessageText(event) {
  return event.error_message || event.message || event.error_code || '—';
}

function renderLogRows(events) {
  const list = $('#logs-list');
  const empty = $('#logs-empty');
  const count = $('#logs-count');
  list.innerHTML = '';
  count.textContent = `${events.length}개`;
  empty.classList.toggle('hidden', events.length !== 0);

  events.forEach(event => {
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-slate-800/40 align-top';

    const time = document.createElement('td');
    time.className = 'px-4 py-3 text-xs text-slate-400 whitespace-nowrap';
    setText(time, event.created_at);

    const type = document.createElement('td');
    type.className = 'px-4 py-3 whitespace-nowrap';
    const typeWrap = document.createElement('div');
    typeWrap.className = 'flex flex-col gap-0.5';
    const eventLabel = document.createElement('span');
    eventLabel.className = 'text-sm font-semibold text-slate-200';
    setText(eventLabel, LOG_EVENT_LABELS[event.event_type] || event.event_type);
    const actionLabel = document.createElement('span');
    actionLabel.className = 'text-xs text-slate-500';
    setText(actionLabel, LOG_ACTION_LABELS[event.action] || event.action);
    typeWrap.append(eventLabel, actionLabel);
    type.appendChild(typeWrap);

    const status = document.createElement('td');
    status.className = 'px-4 py-3 whitespace-nowrap';
    const badge = document.createElement('span');
    badge.className = `inline-flex px-2 py-0.5 rounded-full border text-xs font-medium ${statusBadgeClass(event.status)}`;
    setText(badge, event.status);
    status.appendChild(badge);

    const target = document.createElement('td');
    target.className = 'px-4 py-3 text-xs text-slate-300 min-w-[220px]';
    setText(target, eventTargetText(event));

    const message = document.createElement('td');
    message.className = 'px-4 py-3 text-xs text-slate-300';
    const msg = document.createElement('p');
    msg.className = event.error_message ? 'text-red-300' : 'text-slate-300';
    setText(msg, eventMessageText(event));
    message.appendChild(msg);
    if (event.log_path) {
      const logPath = document.createElement('p');
      logPath.className = 'mt-1 text-[11px] text-slate-500 break-all';
      setText(logPath, `로그 파일: ${event.log_path}`);
      message.appendChild(logPath);
    }

    const actor = document.createElement('td');
    actor.className = 'px-4 py-3 text-xs text-slate-400 whitespace-nowrap';
    setText(actor, event.actor_user_id || '—');

    tr.append(time, type, status, target, message, actor);
    list.appendChild(tr);
  });
}

export async function loadLogs() {
  const loading = $('#logs-loading');
  const list = $('#logs-list');
  const empty = $('#logs-empty');
  const label = LOG_TYPE_LABELS[state.selectedLogType] || '로그';
  $('#logs-title').textContent = label;
  $('#logs-subtitle').textContent = state.selectedLogType
    ? `${label} 이벤트만 조회합니다.`
    : '전체 로그를 조회합니다.';
  updateLogMenuState(true);
  loading.classList.remove('hidden');
  loading.classList.add('flex');
  empty.classList.add('hidden');
  list.innerHTML = '';

  try {
    const params = new URLSearchParams({ limit: '100' });
    if (state.selectedLogType) params.set('event_type', state.selectedLogType);
    const payload = await api('GET', `/api/logs?${params.toString()}`);
    renderLogRows(payload.events || []);
  } catch (err) {
    list.innerHTML = `<tr><td colspan="6" class="px-4 py-8 text-sm text-red-400">${esc(err.message)}</td></tr>`;
    $('#logs-count').textContent = '';
  } finally {
    loading.classList.add('hidden');
    loading.classList.remove('flex');
  }
}
