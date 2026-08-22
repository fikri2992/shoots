/**
 * The single fetch/SSE wrapper. AGENTS.md: components never call this directly —
 * only Pinia actions do.
 */

async function request(path, options = {}) {
  const response = await fetch(path, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(`${response.status} ${response.statusText}: ${detail}`)
  }
  return response.status === 204 ? null : response.json()
}

export default {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: 'POST', body: JSON.stringify(body) }),
  patch: (path, body) => request(path, { method: 'PATCH', body: JSON.stringify(body) }),
  del: (path) => request(path, { method: 'DELETE' }),

  /**
   * Server-sent events — the live agent activity feed.
   *
   * EventSource reconnects on its own, but not after the server closes the stream
   * cleanly, which is what a proxy idle-timeout looks like. Cloud Run does exactly
   * that, so a run longer than the timeout would silently stop narrating itself.
   * This reopens with backoff and reports connection state so the UI can show it.
   *
   * Returns a close function; calling it stops reconnecting for good.
   */
  stream(path, { onEvent, onError, onOpen, onReconnecting } = {}) {
    let source = null
    let attempt = 0
    let timer = null
    let closed = false

    const connect = () => {
      if (closed) return
      source = new EventSource(path, { withCredentials: true })

      source.onopen = () => {
        attempt = 0
        onOpen?.()
      }

      source.onmessage = (event) => {
        try {
          onEvent?.(JSON.parse(event.data))
        } catch {
          // A malformed frame must not tear down the whole feed.
        }
      }

      source.onerror = (event) => {
        onError?.(event)
        source?.close()
        if (closed) return

        attempt += 1
        const delay = Math.min(1000 * 2 ** (attempt - 1), 30000)
        onReconnecting?.(attempt, delay)
        timer = setTimeout(connect, delay)
      }
    }

    connect()

    return () => {
      closed = true
      clearTimeout(timer)
      source?.close()
    }
  },
}
