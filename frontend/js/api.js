export async function api(method, path, body, timeoutMs = 0) {
  const controller = timeoutMs > 0 ? new AbortController() : null;
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
    signal: controller ? controller.signal : undefined,
  };
  if (body) opts.body = JSON.stringify(body);
  let timer = null;
  try {
    const fetchPromise = fetch(path, opts);
    const timeoutPromise = timeoutMs > 0
      ? new Promise((_, reject) => {
          timer = setTimeout(() => {
            if (controller) controller.abort();
            reject(new Error('요청 시간이 초과되었습니다. 네트워크 상태를 확인한 뒤 다시 시도하세요.'));
          }, timeoutMs);
        })
      : null;
    const res = timeoutMs > 0
      ? await Promise.race([fetchPromise, timeoutPromise])
      : await fetchPromise;
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: '알 수 없는 오류' }));
      throw new Error(err.detail || res.statusText);
    }
    return res.json();
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new Error('요청 시간이 초과되었습니다. 네트워크 상태를 확인한 뒤 다시 시도하세요.');
    }
    throw err;
  } finally {
    if (timer) clearTimeout(timer);
  }
}
