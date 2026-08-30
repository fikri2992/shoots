import { collinearLine, plain } from '@/domain/cells'

const PAIR_TECHNIQUES = new Set([
  'backlight',
  'complementary',
  'juxtaposition',
  'panning',
  'reflections',
  'shallow_dof',
  'warm_cool',
])
const PLANE_TECHNIQUES = new Set(['deep_dof', 'layering', 'telephoto_compression'])
const INSTANCE_TECHNIQUES = new Set([
  'astro',
  'bokeh_balls',
  'break_the_pattern',
  'dappled_light',
  'patterns',
  'rule_of_odds',
])
const LINE_TECHNIQUES = new Set([
  'diagonals',
  'horizon_placement',
  'leading_lines',
  'light_painting',
  'light_trails',
])
const FRAME_TECHNIQUES = new Set(['frame_within_frame'])
const POINT_TECHNIQUES = new Set([
  'break_the_pattern',
  'eye_contact_portrait',
  'single_accent',
])

export function artifactIsRenderable(artifact) {
  return Boolean(
    artifact?.status === 'rendered' &&
      (artifact.blob_path ||
        (artifact.kind === 'exif_receipt' && Object.keys(artifact.metrics || {}).length)),
  )
}

export function markIsRenderable(mark, composition = null) {
  if (!mark) return false
  if (artifactIsRenderable(mark.visual_artifact)) return true
  const cells = mark.cells || []
  const regions = mark.regions || []
  const expectedRelation = relationKind(mark.technique_id)
  if (expectedRelation && mark.kind !== expectedRelation) return false
  if (expectedRelation || mark.technique_id === 'leading_lines') return false
  switch (mark.kind) {
    case 'finding':
    case 'whole_frame':
      return true
    case 'move':
      return cells.length > 0 && (mark.to_cells || []).length > 0
    case 'line':
      return (
        (mark.paths || []).some((path) => (path.points || []).length >= 2) ||
        Boolean(collinearLine(cells))
      )
    case 'pair':
      return usableRegions(regions).length >= 2
    case 'planes':
      return planesAreRenderable(mark)
    case 'instances':
      return usableRegions(regions).length >= 2
    case 'crop':
    case 'region':
    case 'frame':
      return cells.length > 0
    case 'point':
      return (
        cells.length > 0 ||
        (typeof composition?.subject_x === 'number' && typeof composition?.subject_y === 'number')
      )
    default:
      return false
  }
}

function techniqueMark(evidence) {
  let kind = 'none'
  if (PAIR_TECHNIQUES.has(evidence.technique_id)) kind = 'pair'
  else if (PLANE_TECHNIQUES.has(evidence.technique_id)) kind = 'planes'
  else if (INSTANCE_TECHNIQUES.has(evidence.technique_id)) kind = 'instances'
  else if (LINE_TECHNIQUES.has(evidence.technique_id)) kind = 'line'
  else if (FRAME_TECHNIQUES.has(evidence.technique_id)) kind = 'frame'
  else if (POINT_TECHNIQUES.has(evidence.technique_id)) kind = 'point'
  else if ((evidence.cells || []).length) kind = 'region'
  return {
    kind,
    cells: evidence.cells || [],
    to_cells: [],
    paths: evidence.paths || [],
    regions: evidence.regions || [],
    visual_artifact: evidence.visual_artifact || null,
    technique_id: evidence.technique_id || '',
  }
}

function relationKind(techniqueId) {
  if (PAIR_TECHNIQUES.has(techniqueId)) return 'pair'
  if (PLANE_TECHNIQUES.has(techniqueId)) return 'planes'
  if (INSTANCE_TECHNIQUES.has(techniqueId)) return 'instances'
  return ''
}

function usableRegions(regions) {
  return (regions || []).filter((region) => (region.cells || []).length > 0)
}

function planesAreRenderable(mark) {
  const regions = usableRegions(mark.regions)
  const orders = new Set(regions.map((region) => region.order))
  if (orders.size !== regions.length) return false
  if (mark.technique_id !== 'layering') return regions.length >= 2
  const roles = new Set(regions.map((region) => region.role))
  return (
    regions.length >= 3 &&
    roles.has('foreground') &&
    roles.has('midground') &&
    roles.has('background')
  )
}

function compositionMark(composition) {
  if ((composition?.subject_cells || []).length) {
    return { kind: 'region', cells: composition.subject_cells }
  }
  if (typeof composition?.subject_x === 'number' && typeof composition?.subject_y === 'number') {
    return { kind: 'point', cells: [] }
  }
  return null
}

function storyStep(label, title, body, mark, layer = 'evidence') {
  return { label, title, body: body || '', mark, layer }
}

export function buildVisualStory(view) {
  const analysis = view?.analysis
  const shot = view?.shot
  if (!analysis || !shot) return []
  const teaching = view.teaching || {}
  const composition = analysis.composition || {}
  const grid = shot.grid
  const story = []
  const keepMark = teaching.keep_mark
    ? {
        ...teaching.keep_mark,
        technique_id: teaching.keep_mark.technique_id || teaching.keep_technique_id || '',
      }
    : null
  if (teaching.keep_title && markIsRenderable(keepMark, composition)) {
    story.push(
      storyStep(
        'WHAT HOLDS THIS SHOT',
        teaching.keep_title,
        plain(teaching.keep_proof || '', grid),
        keepMark,
      ),
    )
  } else {
    const mark = compositionMark(composition)
    if (markIsRenderable(mark, composition)) {
      story.push(
        storyStep(
          "START HERE · SHOOTS' VISUAL READ",
          'Start with what catches your eye first.',
          plain(
            analysis.observations?.[0] || 'Shoots found the main subject and where it sits in the Shot.',
            grid,
          ),
          mark,
        ),
      )
    }
  }

  const corroborated = (analysis.techniques || [])
    .filter((evidence) => (evidence.agreement || 0) >= 2)
    .filter((evidence) => evidence.technique_id !== teaching.keep_technique_id)
  corroborated.forEach((evidence) => {
    const mark = techniqueMark(evidence)
    if (!markIsRenderable(mark, composition)) return
    story.push(
      storyStep(
        "ANOTHER CHOICE · SHOOTS' VISUAL READ",
        evidence.name || evidence.technique_id.replace(/_/g, ' '),
        plain(evidence.note || '', grid),
        mark,
      ),
    )
  })

  const noticeMark = teaching.notice_mark
  if (teaching.notice_title && markIsRenderable(noticeMark, composition)) {
    story.push(
      storyStep(
        teaching.notice_authority === 'measured'
          ? 'WHAT THE CAMERA FOUND'
          : "WHAT STOOD OUT · SHOOTS' VISUAL READ",
        teaching.notice_title,
        plain(teaching.notice_proof || '', grid),
        noticeMark,
        teaching.notice_authority === 'measured' ? 'finding' : 'evidence',
      ),
    )
  }

  const tryMark = teaching.try_mark
  if (teaching.try_text && markIsRenderable(tryMark, composition)) {
    story.push(
      storyStep(
        'TRY THIS',
        teaching.try_text,
        plain(teaching.try_reason || '', grid),
        tryMark,
        'action',
      ),
    )
  }

  const checkMark = teaching.check_mark
  if (teaching.visible_check && markIsRenderable(checkMark, composition)) {
    story.push(
      storyStep(
        'CHECK NEXT TIME',
        teaching.visible_check,
        'Use the marked area as a quick check before you move on.',
        checkMark,
        checkMark.kind === 'move' || checkMark.kind === 'crop' ? 'action' : 'evidence',
      ),
    )
  }

  if (!story.length) {
    story.push(
      storyStep(
        'THIS SHOT',
        'Shoots did not find one visual claim it could point to here.',
        '',
        null,
        'clean',
      ),
    )
  }
  return story
}
