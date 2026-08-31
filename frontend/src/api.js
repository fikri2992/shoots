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
    throw new Error(await errorMessage(response))
  }
  return response.status === 204 ? null : response.json()
}

export default {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: 'POST', body: JSON.stringify(body) }),
  patch: (path, body) => request(path, { method: 'PATCH', body: JSON.stringify(body) }),
  put: (path, body) => request(path, { method: 'PUT', body: JSON.stringify(body) }),
  del: (path) => request(path, { method: 'DELETE' }),

  async getBlob(path) {
    const response = await fetch(path, { credentials: 'include' })
    if (!response.ok) throw new Error(await errorMessage(response))
    return response.blob()
  },

  /** A WebSocket on this origin; the session cookie rides along. Binary frames as ArrayBuffer. */
  socket(path) {
    const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const socket = new WebSocket(`${scheme}://${window.location.host}${path}`)
    socket.binaryType = 'arraybuffer'
    return socket
  },

  /** Multipart upload: no JSON content type, the browser sets the boundary. */
  async postForm(path, form) {
    const response = await fetch(path, { method: 'POST', credentials: 'include', body: form })
    if (!response.ok) throw new Error(await errorMessage(response))
    return response.status === 204 ? null : response.json()
  },

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

async function errorMessage(response) {
  const fallback = response.statusText || `Request failed (${response.status})`
  const body = await response.text()
  if (!body) return fallback
  try {
    const parsed = JSON.parse(body)
    if (typeof parsed.detail === 'string') return sentence(parsed.detail)
    if (Array.isArray(parsed.detail)) {
      const messages = parsed.detail.map((item) => item?.msg).filter(Boolean)
      if (messages.length) return sentence(messages.join('. '))
    }
  } catch {
    // Plain-text server errors are already readable.
  }
  return sentence(body.length <= 240 ? body : fallback)
}

function sentence(value) {
  const clean = String(value).trim()
  if (!clean) return 'Something went wrong.'
  if (/^UnknownEntity:\s*user\b/i.test(clean)) {
    return 'This account has no matching record in the current Shoots store.'
  }
  if (/^UnknownEntity:/i.test(clean)) return 'This record is no longer available.'
  if (/^Internal Server Error$/i.test(clean)) return 'Shoots could not finish that request.'
  return `${clean.charAt(0).toUpperCase()}${clean.slice(1)}${/[.!?]$/.test(clean) ? '' : '.'}`
}
