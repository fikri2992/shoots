const METRIC_LABELS = {
  mean_luma: 'average brightness',
  p05_luma: 'darkest areas',
  p95_luma: 'brightest areas',
  mean_saturation_pct: 'average saturation',
  p95_saturation_pct: 'strongest saturation',
  clipped_highlights_pct: 'pure white',
  colour_temperature_k: 'colour temperature',
}

export function techniqueHistory(context) {
  if (!context) return ''
  const keepers = context.positive_keeper_shots
    ? ` ${context.positive_keeper_shots} ${context.positive_keeper_shots === 1 ? 'Keeper is' : 'Keepers are'} part of that.`
    : ''
  if (!context.corroborated_shots) {
    return `Shoots has not seen this clearly in another Shot yet.${keepers}`
  }
  if (context.corroborated_shots === 1) {
    return `This is the first clear sighting in your Shoots record.${keepers}`
  }
  if (context.corroborated_shots === 2) {
    return `Shoots has seen this clearly in 2 Shots. It becomes recurring at 3.${keepers}`
  }
  const shoots = context.distinct_shoots
    ? ` from ${context.distinct_shoots} ${context.distinct_shoots === 1 ? 'Shoot' : 'Shoots'}`
    : ''
  return `Shoots has seen this clearly in ${context.corroborated_shots} Shots${shoots}.${keepers}`
}

export function repeatabilitySummary(context) {
  if (!context) return ''
  if (!context.reproduce_sessions) return 'You have not tried to repeat this on purpose yet.'
  if (!context.evaluable_reproduce_sessions) {
    return `You tried this in ${context.reproduce_sessions} ${context.reproduce_sessions === 1 ? 'session' : 'sessions'}, but none could be checked.`
  }
  const checked = context.evaluable_reproduce_sessions
  const matched = context.criteria_met_sessions || 0
  if (!matched) {
    return `${checked} ${checked === 1 ? 'session was' : 'sessions were'} checked. None matched every check yet.`
  }
  return `${matched} of ${checked} checked ${checked === 1 ? 'session' : 'sessions'} matched what you set before shooting.`
}

export function metricLabel(key) {
  return METRIC_LABELS[key] || key.replace(/_/g, ' ')
}

export function shootSummary(receipt) {
  const shots = receipt?.shot_count || 0
  const scenes = receipt?.scene_count || 0
  if (!shots) return 'Your outing is ready to look back on.'
  if (!scenes) return `You made ${shots} ${shots === 1 ? 'Shot' : 'Shots'} in this outing.`
  return `You made ${shots} ${shots === 1 ? 'Shot' : 'Shots'} across ${scenes} ${scenes === 1 ? 'Scene' : 'Scenes'}.`
}

/**
 * Old records are immutable, so their original prose stays in storage. This
 * only replaces a small set of retired report phrases at presentation time.
 */
export function humanizeLegacyText(value) {
  return String(value || '')
    .replace(
      /Read (\d+) Shots, grouped (\d+) Scenes, and settled one Shoot Record\./gi,
      'Shoots read $1 Shots and found $2 Scenes in the outing.',
    )
    .replace(
      /(\d+) Reproduce result Shot(?:s)? (?:is|are) recorded\. One attempt is not durable Change\./gi,
      (_, count) => `${count} result ${count === '1' ? 'Shot' : 'Shots'} came back. It is too early to call this a lasting change.`,
    )
    .replace(
      /(\d+) of (\d+) evaluable result(?:s)? met the declared Criteria\./gi,
      '$1 of $2 checked results matched every check set before shooting.',
    )
    .replace(
      /Recurring does not prove deliberate control\. No settled Reproduce session yet\./gi,
      'This keeps returning in your Shots. You have not tried to repeat it on purpose yet.',
    )
    .replace(/First corroborated sighting in your Shoots record/gi, 'First clear sighting in your Shoots record')
    .replace(/Deliberate repeatability has not been tested\./gi, 'You have not tried to repeat this on purpose yet.')
    .replace(
      /One Analyst observation; not a measured Finding\./gi,
      "Shoots saw this once. It is a visual read, not a camera measurement.",
    )
    .replace(/Direct import accepted/gi, 'Shoots accepted the imported Shot')
    .replace(/Visual Evidence stored/gi, 'Shoots finished the visual read')
    .replace(/Photographer record updated/gi, 'Shoots checked what appeared before')
    .replace(/No Reproduce judgment needed/gi, 'No Experiment check was needed')
    .replace(/No external write requested/gi, 'No Drive copy was requested')
    .replace(/Waited for Shoot closure/gi, 'Shoots waited to see the whole outing')
    .replace(
      /(\d+) readable Shots are accounted for in one settled Shoot Record\./gi,
      'Shoots read $1 Shots in this outing and accounted for the full Shoot.',
    )
    .replace(
      /The Shoot contains three capture-continuous Scenes with ([^.]+)\./gi,
      'They fall into three Scenes with $1.',
    )
    .replace(
      /There are no Keeper marks, so taste remains unknown\./gi,
      'You have not marked a Shot yet, so Shoots does not guess which ones matter to you.',
    )
    .replace(
      /No Keeper marks exist, so this record makes no claim about which Shots you value\./gi,
      'When this Shoot settled, no Keeper mark had been made, so this record does not claim which Shots you valued then.',
    )
    .replace(
      /Across this imported outing, the distant ridge and cloud layer recur while foreground paths and open space change how the view is carried\./gi,
      'The distant ridge and cloud layer keep returning. The road and open foreground change how you arrive there.',
    )
    .replace(
      /That is a repeated choice in this record, not proof that you can reproduce it deliberately\./gi,
      'That choice keeps returning. You have not tried to repeat it on purpose yet.',
    )
}

export function resultSummary(results, matched, unchecked = 0) {
  const bits = [`${results} result ${results === 1 ? 'Shot' : 'Shots'}`]
  bits.push(`${matched || 0} matched every check`)
  if (unchecked) bits.push(`${unchecked} could not be checked`)
  return bits.join(' · ')
}

export function scoutStory(scout) {
  if (!scout) return 'Keep shooting. Shoots will speak when a useful pattern appears.'
  const reason = String(scout.reason || '').trim()
  if (scout.route === 'recommend') {
    const option = scout.recommendation?.options?.find(
      (item) => item.id === scout.recommendation?.primary_option_id,
    ) || scout.recommendation?.options?.[0]
    return option
      ? `Shoots recommends trying ${option.technique_name} next. Nothing starts until you choose it.`
      : 'Shoots prepared one optional Experiment idea. Nothing started.'
  }
  if (scout.route === 'ask') {
    return 'Shoots found one supported Experiment idea. Nothing starts until you choose it.'
  }
  if (scout.route === 'explain' && /supported pattern|did not assign|prescrib/i.test(reason)) {
    return 'Shoots found a pattern worth showing. No exercise is needed.'
  }
  if (scout.route === 'silence' && /evidence|intervention|repeated|varied/i.test(reason)) {
    return 'Nothing is clear enough to interrupt you with yet.'
  }
  if (/no marked Keeper has corroborated Technique Evidence/i.test(reason)) {
    return 'Mark a Shot you care about first. Shoots can then build from what appears clearly in it.'
  }
  if (/fewer than two corroborated Technique directions/i.test(reason)) {
    return 'There was no useful choice to ask you about in this outing.'
  }
  return reason || 'Keep shooting. Shoots will speak when a useful pattern appears.'
}
