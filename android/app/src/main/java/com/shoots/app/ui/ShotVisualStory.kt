package com.shoots.app.ui

import com.shoots.app.data.AnalysisDto
import com.shoots.app.data.CompositionDto
import com.shoots.app.data.GridSpecDto
import com.shoots.app.data.ShotTeachingReceiptDto
import com.shoots.app.data.TechniqueEvidenceDto
import com.shoots.app.data.VisualEvidenceArtifactDto
import com.shoots.app.data.VisualMarkDto

data class ShotStoryStep(
    val label: String,
    val title: String,
    val body: String = "",
    val layer: ReviewLayer,
    val findingIndex: Int = 0,
    val mark: VisualMarkDto = VisualMarkDto(),
)

fun buildShotVisualStory(
    analysis: AnalysisDto,
    teaching: ShotTeachingReceiptDto?,
    grid: GridSpecDto?,
): List<ShotStoryStep> = buildList {
    val composition = analysis.composition
    val keepMark = teaching?.keepMark
        ?.let { mark ->
            if (mark.techniqueId.isBlank() && teaching.keepTechniqueId.isNotBlank()) {
                mark.copy(techniqueId = teaching.keepTechniqueId)
            } else {
                mark
            }
        }
        ?.takeIf { hasDrawableMark(it, composition) }
        ?: VisualMarkDto()
    if (teaching?.keepTitle?.isNotBlank() == true && hasDrawableMark(keepMark, composition)) {
        add(
            ShotStoryStep(
                label = "WHAT HOLDS THIS SHOT",
                title = teaching.keepTitle,
                body = plainCellReferences(teaching.keepProof, grid),
                layer = layerFor(keepMark),
                mark = keepMark,
            )
        )
    } else if (hasCompositionEvidence(composition)) {
        val observation = analysis.observations.firstOrNull().orEmpty()
        add(
            ShotStoryStep(
                label = "START HERE · SHOOTS' VISUAL READ",
                title = "Start with what catches your eye first.",
                body = plainCellReferences(observation, grid).ifBlank {
                    "Shoots found the main subject and where it sits in the Shot."
                },
                layer = ReviewLayer.EVIDENCE,
                mark = compositionMark(composition),
            )
        )
    }

    analysis.techniques
        .asSequence()
        .filter(::isCorroborated)
        .filter { it.techniqueId != teaching?.keepTechniqueId }
        .map { it to techniqueMark(it) }
        .filter { (_, mark) -> hasDrawableMark(mark, composition) }
        .forEach { (evidence, mark) ->
            add(
                ShotStoryStep(
                    label = "ANOTHER CHOICE · SHOOTS' VISUAL READ",
                    title = evidence.name.ifBlank { humanLabel(evidence.techniqueId) },
                    body = plainCellReferences(evidence.note, grid),
                    layer = ReviewLayer.EVIDENCE,
                    mark = mark,
                )
            )
        }

    val noticeTitle = teaching?.noticeTitle.orEmpty()
    if (noticeTitle.isNotBlank()) {
        val findingId = teaching?.noticeFindingId.orEmpty()
        val findingIndex = analysis.findings.indexOfFirst { it.findingId == findingId }
            .takeIf { it >= 0 }
            ?: 0
        val measured = teaching?.noticeAuthority == "measured"
        val noticeMark = teaching?.noticeMark
            ?.takeIf { hasDrawableMark(it, composition) }
            ?: VisualMarkDto()
        if (hasDrawableMark(noticeMark, composition)) {
            add(
                ShotStoryStep(
                    label = if (measured) "WHAT THE CAMERA FOUND" else "WHAT STOOD OUT · SHOOTS' VISUAL READ",
                    title = noticeTitle,
                    body = plainCellReferences(teaching?.noticeProof.orEmpty(), grid),
                    layer = layerFor(noticeMark),
                    findingIndex = findingIndex,
                    mark = noticeMark,
                )
            )
        }
    }

    val tryText = teaching?.tryText.orEmpty()
    if (tryText.isNotBlank()) {
        val tryMark = teaching?.tryMark
            ?.takeIf { hasDrawableMark(it, composition) }
            ?: VisualMarkDto()
        if (hasDrawableMark(tryMark, composition)) {
            add(
                ShotStoryStep(
                    label = "TRY THIS",
                    title = tryText,
                    body = plainCellReferences(teaching?.tryReason.orEmpty(), grid),
                    layer = layerFor(tryMark),
                    mark = tryMark,
                )
            )
        }
    }

    teaching?.visibleCheck?.takeIf(String::isNotBlank)?.let { check ->
        val checkMark = teaching.checkMark
            .takeIf { hasDrawableMark(it, composition) }
            ?: VisualMarkDto()
        if (hasDrawableMark(checkMark, composition)) {
            add(
                ShotStoryStep(
                    label = "CHECK NEXT TIME",
                    title = check,
                    body = "Use the marked area as a quick check before you move on.",
                    layer = layerFor(checkMark),
                    mark = checkMark,
                )
            )
        }
    }

    if (isEmpty()) {
        add(
            ShotStoryStep(
                label = "THIS SHOT",
                title = "Shoots did not find one visual claim it could point to here.",
                layer = ReviewLayer.CLEAN,
            )
        )
    }
}

fun hasCompositionEvidence(composition: CompositionDto): Boolean =
    composition.subjectCells.isNotEmpty() ||
        (composition.subjectX != null && composition.subjectY != null)

fun hasCompositionAction(composition: CompositionDto): Boolean =
    composition.suggestedCropCells.isNotEmpty() || composition.moves.any {
        it.kind == "move" && it.fromCells.isNotEmpty() && it.toCells.isNotEmpty()
    }

fun hasDrawableMark(mark: VisualMarkDto, composition: CompositionDto? = null): Boolean {
    if (visualArtifactOwnsLayer(mark.visualArtifact)) return true
    val expectedRelation = relationKind(mark.techniqueId)
    if (expectedRelation != null && mark.kind != expectedRelation) return false
    if (expectedRelation != null || mark.techniqueId == "leading_lines") return false
    return when (mark.kind) {
    "finding", "whole_frame" -> true
    "move" -> mark.cells.isNotEmpty() && mark.toCells.isNotEmpty()
    "line" -> mark.paths.any { it.points.size >= 2 } || collinearCellPath(mark.cells) != null
    "pair" -> usableRegions(mark).size >= 2
    "instances" -> usableRegions(mark).size >= 2
    "planes" -> planesAreDrawable(mark)
    "crop", "region", "frame" -> mark.cells.isNotEmpty()
    "point" -> mark.cells.isNotEmpty() ||
        (composition?.subjectX != null && composition.subjectY != null)
    else -> false
    }
}

internal fun visualArtifactOwnsLayer(artifact: VisualEvidenceArtifactDto?): Boolean =
    artifact?.status == "rendered" &&
        (
            artifact.blobPath.isNotBlank() ||
                (artifact.kind == "exif_receipt" && artifact.metrics.isNotEmpty())
        )

private fun layerFor(mark: VisualMarkDto): ReviewLayer = when (mark.kind) {
    "finding" -> ReviewLayer.FINDING
    "move", "crop" -> ReviewLayer.ACTION
    "none" -> ReviewLayer.CLEAN
    else -> ReviewLayer.EVIDENCE
}

private fun compositionMark(composition: CompositionDto): VisualMarkDto = when {
    composition.subjectCells.isNotEmpty() -> VisualMarkDto(kind = "region", cells = composition.subjectCells)
    composition.subjectX != null && composition.subjectY != null -> VisualMarkDto(kind = "point")
    else -> VisualMarkDto()
}

private fun techniqueMark(evidence: TechniqueEvidenceDto): VisualMarkDto {
    val kind = relationKind(evidence.techniqueId) ?: when (evidence.techniqueId) {
        "diagonals", "horizon_placement", "leading_lines", "light_trails", "light_painting" -> "line"
        "frame_within_frame" -> "frame"
        "break_the_pattern", "eye_contact_portrait", "single_accent" -> "point"
        else -> if (evidence.cells.isNotEmpty()) "region" else "none"
    }
    return VisualMarkDto(
        kind = kind,
        cells = evidence.cells,
        paths = evidence.paths,
        regions = evidence.regions,
        visualArtifact = evidence.visualArtifact,
        techniqueId = evidence.techniqueId,
    )
}

private fun relationKind(techniqueId: String): String? = when (techniqueId) {
    in PAIR_TECHNIQUES -> "pair"
    in PLANE_TECHNIQUES -> "planes"
    in INSTANCE_TECHNIQUES -> "instances"
    else -> null
}

private fun usableRegions(mark: VisualMarkDto) = mark.regions.filter { it.cells.isNotEmpty() }

private fun planesAreDrawable(mark: VisualMarkDto): Boolean {
    val regions = usableRegions(mark)
    if (regions.map { it.order }.toSet().size != regions.size) return false
    if (mark.techniqueId != "layering") return regions.size >= 2
    val roles = regions.map { it.role }.toSet()
    return regions.size >= 3 &&
        "foreground" in roles &&
        "midground" in roles &&
        "background" in roles
}

private val PAIR_TECHNIQUES = setOf(
    "backlight",
    "complementary",
    "juxtaposition",
    "panning",
    "reflections",
    "shallow_dof",
    "warm_cool",
)

private val PLANE_TECHNIQUES = setOf("deep_dof", "layering", "telephoto_compression")

private val INSTANCE_TECHNIQUES = setOf(
    "astro",
    "bokeh_balls",
    "break_the_pattern",
    "dappled_light",
    "patterns",
    "rule_of_odds",
)
