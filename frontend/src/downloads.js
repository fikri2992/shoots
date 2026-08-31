export function storyPageFilename(draftId, index) {
  const id = String(draftId || 'story').replace(/[^a-zA-Z0-9_-]/g, '_')
  return `Shoots-${id}-${String(index + 1).padStart(2, '0')}.jpg`
}

/** Request separate downloads. The browser, not the app, decides whether to save them. */
export async function downloadImages(images) {
  for (const [index, { blob, filename }] of images.entries()) {
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.hidden = true
    document.body.appendChild(link)
    try {
      link.click()
    } finally {
      link.remove()
      // Keep the bytes available while the browser hands the request to its downloader.
      setTimeout(() => URL.revokeObjectURL(url), 30000)
    }
    if (index < images.length - 1) {
      await new Promise((resolve) => setTimeout(resolve, 200))
    }
  }
  return images.length
}
