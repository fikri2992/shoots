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
        ?.takeIf(::hasDrawableMark)
        ?: legacyKeepMark(teaching)
    if (teaching?.keepTitle?.isNotBlank() == true && hasDrawableMark(keepMark)) {
        add(
            ShotStoryStep(
                label = "WHAT HOLDS THIS SHOT",
                title = teaching.keepTitle,
                body = teaching.keepProof,
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
        .filter { (_, mark) -> hasDrawableMark(mark) }
        .forEach { (evidence, mark) ->
            add(
                ShotStoryStep(
                    label = "ANOTHER CHOICE · SHOOTS' VISUAL READ",
                    title = evidence.name.ifBlank { humanLabel(evidence.techniqueId) },
                    body = evidence.note,
                    layer = ReviewLayer.EVIDENCE,
                    mark = mark,
                )
            )
        }

    val noticeTitle = teaching?.noticeTitle.orEmpty().ifBlank {
        analysis.findings.firstOrNull()?.what.orEmpty()
    }
    if (noticeTitle.isNotBlank()) {
        val findingId = teaching?.noticeFindingId.orEmpty()
        val findingIndex = analysis.findings.indexOfFirst { it.findingId == findingId }
            .takeIf { it >= 0 }
            ?: 0
        val measured = teaching?.noticeAuthority == "measured" || analysis.findings.isNotEmpty()
        val noticeMark = teaching?.noticeMark
            ?.takeIf(::hasDrawableMark)
            ?: legacyNoticeMark(teaching, analysis, findingIndex, measured)
        if (hasDrawableMark(noticeMark)) {
            add(
                ShotStoryStep(
                    label = if (measured) "WHAT THE CAMERA FOUND" else "WHAT STOOD OUT · SHOOTS' VISUAL READ",
                    title = noticeTitle,
                    body = teaching?.noticeProof.orEmpty().ifBlank {
                        analysis.findings.getOrNull(findingIndex)?.why.orEmpty()
                    },
                    layer = layerFor(noticeMark),
                    findingIndex = findingIndex,
                    mark = noticeMark,
                )
            )
        }
    }

    val tryText = teaching?.tryText.orEmpty().ifBlank {
        compositionInstruction(composition, grid).substringBeforeLast(". ").trimEnd('.')
    }
    if (tryText.isNotBlank()) {
        val tryMark = teaching?.tryMark
            ?.takeIf(::hasDrawableMark)
            ?: legacyTryMark(teaching, composition)
        if (hasDrawableMark(tryMark)) {
            add(
                ShotStoryStep(
                    label = "TRY THIS",
                    title = tryText,
                    body = teaching?.tryReason.orEmpty(),
                    layer = layerFor(tryMark),
                    mark = tryMark,
                )
            )
        }
    }

    teaching?.visibleCheck?.takeIf(String::isNotBlank)?.let { check ->
        val checkMark = teaching.checkMark
            .takeIf(::hasDrawableMark)
            ?: teaching.tryMark.takeIf(::hasDrawableMark)
            ?: teaching.noticeMark.takeIf(::hasDrawableMark)
            ?: keepMark
        if (hasDrawableMark(checkMark)) {
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
        composition.subjectX != null ||
        composition.subjectY != null ||
        composition.horizonRow != null

fun hasCompositionAction(composition: CompositionDto): Boolean =
    composition.suggestedCropCells.isNotEmpty() || composition.moves.any {
        it.kind == "move" && it.fromCells.isNotEmpty() && it.toCells.isNotEmpty()
    }

fun hasDrawableMark(mark: VisualMarkDto): Boolean {
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
    "point" -> true
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
    composition.horizonRow != null -> VisualMarkDto(kind = "line")
    else -> VisualMarkDto()
}

private fun legacyKeepMark(teaching: ShotTeachingReceiptDto?): VisualMarkDto {
    if (teaching == null || teaching.keepCells.isEmpty()) return VisualMarkDto()
    val kind = relationKind(teaching.keepTechniqueId) ?: when (teaching.keepTechniqueId) {
        "diagonals", "horizon_placement", "leading_lines", "light_trails" -> "line"
        "frame_within_frame" -> "frame"
        "break_the_pattern", "eye_contact_portrait", "single_accent" -> "point"
        else -> "region"
    }
    return VisualMarkDto(
        kind = kind,
        cells = teaching.keepCells,
        techniqueId = teaching.keepTechniqueId,
    )
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

private fun legacyNoticeMark(
    teaching: ShotTeachingReceiptDto?,
    analysis: AnalysisDto,
    findingIndex: Int,
    measured: Boolean,
): VisualMarkDto {
    if (measured) {
        val finding = analysis.findings.getOrNull(findingIndex)
        return VisualMarkDto(
            kind = "finding",
            cells = finding?.cells.orEmpty(),
            findingId = finding?.findingId.orEmpty(),
        )
    }
    return teaching?.noticeCells
        ?.takeIf { it.isNotEmpty() }
        ?.let { VisualMarkDto(kind = "region", cells = it) }
        ?: VisualMarkDto()
}

private fun legacyTryMark(
    teaching: ShotTeachingReceiptDto?,
    composition: CompositionDto,
): VisualMarkDto {
    if (teaching != null) {
        if (teaching.tryKind == "move" && teaching.tryFromCells.isNotEmpty() && teaching.tryToCells.isNotEmpty()) {
            return VisualMarkDto(kind = "move", cells = teaching.tryFromCells, toCells = teaching.tryToCells)
        }
        if (teaching.tryKind == "crop" && teaching.tryToCells.isNotEmpty()) {
            return VisualMarkDto(kind = "crop", cells = teaching.tryToCells)
        }
    }
    if (composition.suggestedCropCells.isNotEmpty()) {
        return VisualMarkDto(kind = "crop", cells = composition.suggestedCropCells)
    }
    val move = composition.moves.firstOrNull {
        it.kind == "move" && it.fromCells.isNotEmpty() && it.toCells.isNotEmpty()
    }
    return move?.let { VisualMarkDto(kind = "move", cells = it.fromCells, toCells = it.toCells) }
        ?: VisualMarkDto()
}
