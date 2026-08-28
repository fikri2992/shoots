package com.shoots.app.ui

import androidx.compose.foundation.Canvas
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.shoots.app.Amber
import com.shoots.app.FindingRed
import com.shoots.app.WarmWhite
import com.shoots.app.data.CompositionDto
import com.shoots.app.data.FindingDto
import com.shoots.app.data.GridSpecDto
import com.shoots.app.data.VisualMarkDto
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.exp
import kotlin.math.ln
import kotlin.math.min
import kotlin.math.sin
import kotlin.math.sqrt

private val EvidenceCyan = Color(0xFF36C4DC)
private val EvidenceViolet = Color(0xFFCB7EEB)

@Composable
fun CompositionGuide(
    grid: GridSpecDto,
    composition: CompositionDto,
    modifier: Modifier = Modifier,
    finding: FindingDto? = null,
    layer: ReviewLayer = ReviewLayer.GUIDE,
    guideOverride: String? = null,
    guideRotation: Int = 0,
    storyMark: VisualMarkDto? = null,
) {
    val guide = guideOverride ?: composition.guide.ifBlank { "thirds" }
    Canvas(
        modifier.semantics {
            contentDescription = when (layer) {
                ReviewLayer.CLEAN -> "Clean Shot"
                ReviewLayer.EVIDENCE -> "Located composition Evidence"
                ReviewLayer.FINDING -> finding?.let { "Finding ${findingLabel(it.findingId)}" } ?: "No located Finding"
                ReviewLayer.ACTION -> "Composition action"
                ReviewLayer.GUIDE -> "${guideLabel(guide)} composition guide"
            }
            if (storyMark?.let(::hasDrawableMark) == true) {
                contentDescription = "Visual mark ${storyMark.kind.replace('_', ' ')}"
            }
        },
    ) {
        if (storyMark?.let(::hasDrawableMark) == true) {
            drawStoryMark(grid, composition, finding, storyMark)
        } else {
            when (layer) {
                ReviewLayer.CLEAN -> Unit
                ReviewLayer.EVIDENCE -> drawCompositionEvidence(grid, composition)
                ReviewLayer.FINDING -> finding?.let { drawFinding(grid, composition, it) }
                ReviewLayer.ACTION -> drawAction(grid, composition)
                ReviewLayer.GUIDE -> {
                    drawGuide(guide, guideRotation)
                    drawSubjectPoint(grid, composition)
                }
            }
        }
    }
}

enum class ReviewLayer { CLEAN, EVIDENCE, FINDING, ACTION, GUIDE }

private fun DrawScope.drawStoryMark(
    grid: GridSpecDto,
    composition: CompositionDto,
    finding: FindingDto?,
    mark: VisualMarkDto,
) {
    when (mark.kind) {
        "region" -> drawMarkedRegion(grid, mark.cells)
        "line" -> drawMarkedLine(grid, composition, mark)
        "frame" -> drawMarkedFrame(grid, mark.cells)
        "point" -> drawMarkedPoint(grid, composition, mark.cells)
        "whole_frame" -> drawWholeFrame()
        "finding" -> if (finding != null) {
            drawFinding(grid, composition, finding)
        } else {
            drawMarkedFindingFallback(grid, mark)
        }
        "move" -> drawMarkedMove(grid, mark)
        "crop" -> drawMarkedCrop(grid, mark.cells)
        "pair" -> drawMarkedPair(grid, mark)
        "instances" -> drawMarkedInstances(grid, mark)
        "planes" -> drawMarkedPlanes(grid, mark)
    }
}

private fun DrawScope.drawMarkedRegion(grid: GridSpecDto, cells: List<String>) {
    val region = spanRect(cells, grid) ?: return
    val stroke = 2.dp.toPx()
    drawRect(EvidenceCyan.copy(alpha = 0.18f), region.topLeft, region.size)
    drawRect(EvidenceCyan.copy(alpha = 0.9f), region.topLeft, region.size, style = Stroke(stroke))
}

private fun DrawScope.drawMarkedLine(
    grid: GridSpecDto,
    composition: CompositionDto,
    mark: VisualMarkDto,
) {
    val paths = mark.paths.mapNotNull { visualPath ->
        cellCentres(visualPath.points, grid).takeIf { it.size >= 2 }?.let { it to visualPath }
    }
    if (paths.isEmpty()) {
        drawMarkedRegion(grid, mark.cells)
        return
    }
    val stroke = 3.dp.toPx()
    paths.forEach { (points, visualPath) ->
        val path = Path().apply {
            moveTo(points.first().x, points.first().y)
            points.drop(1).forEach { point -> lineTo(point.x, point.y) }
        }
        drawPath(path, Color.Black.copy(alpha = 0.6f), style = Stroke(stroke * 2.2f))
        drawPath(path, EvidenceCyan, style = Stroke(stroke))
        drawCircle(EvidenceCyan, radius = 4.dp.toPx(), center = points.first())
        drawCircle(EvidenceCyan, radius = 4.dp.toPx(), center = points.last())
        spanRect(visualPath.leadsTo, grid)?.center?.let { target ->
            drawCircle(EvidenceCyan.copy(alpha = 0.2f), radius = 13.dp.toPx(), center = target)
            drawCircle(EvidenceCyan, radius = 8.dp.toPx(), center = target, style = Stroke(2.dp.toPx()))
        }
    }
    if (mark.techniqueId == "leading_lines" && paths.none { it.second.leadsTo.isNotEmpty() }) {
        drawSubjectPoint(grid, composition)
    }
}

private fun DrawScope.drawMarkedFrame(grid: GridSpecDto, cells: List<String>) {
    val region = spanRect(cells, grid) ?: return
    val stroke = 2.dp.toPx()
    drawRect(EvidenceCyan.copy(alpha = 0.08f), region.topLeft, region.size)
    drawRect(EvidenceCyan, region.topLeft, region.size, style = Stroke(stroke * 1.4f))
    val inset = stroke * 3f
    if (region.width > inset * 2 && region.height > inset * 2) {
        drawRect(
            EvidenceCyan.copy(alpha = 0.65f),
            Offset(region.left + inset, region.top + inset),
            androidx.compose.ui.geometry.Size(region.width - inset * 2, region.height - inset * 2),
            style = Stroke(stroke),
        )
    }
}

private fun DrawScope.drawMarkedPoint(
    grid: GridSpecDto,
    composition: CompositionDto,
    cells: List<String>,
) {
    val point = spanRect(cells, grid)?.center ?: subjectPoint(grid, composition) ?: return
    drawCircle(EvidenceCyan.copy(alpha = 0.18f), radius = 18.dp.toPx(), center = point)
    drawCircle(EvidenceCyan, radius = 11.dp.toPx(), center = point, style = Stroke(2.dp.toPx()))
    drawCircle(EvidenceCyan, radius = 4.dp.toPx(), center = point)
}

private fun DrawScope.drawWholeFrame() {
    val stroke = 2.dp.toPx()
    drawRect(EvidenceCyan.copy(alpha = 0.07f))
    drawRect(EvidenceCyan.copy(alpha = 0.88f), style = Stroke(stroke))
}

private fun DrawScope.drawMarkedPair(grid: GridSpecDto, mark: VisualMarkDto) {
    val regions = mark.regions.sortedBy { it.order }.take(2).mapNotNull { region ->
        spanRect(region.cells, grid)?.let { it to region.role }
    }
    if (regions.size < 2) {
        drawMarkedRegion(grid, mark.cells)
        return
    }
    val stroke = 2.dp.toPx()
    val colours = listOf(EvidenceCyan, EvidenceViolet)
    regions.forEachIndexed { index, (rect, _) ->
        val colour = colours[index]
        drawRect(colour.copy(alpha = 0.14f), rect.topLeft, rect.size)
        drawRect(colour, rect.topLeft, rect.size, style = Stroke(stroke))
        drawCircle(colour, 4.dp.toPx(), rect.center)
    }
    drawLine(
        WarmWhite.copy(alpha = 0.72f),
        regions[0].first.center,
        regions[1].first.center,
        stroke,
        pathEffect = PathEffect.dashPathEffect(floatArrayOf(stroke * 3, stroke * 2)),
    )
}

private fun DrawScope.drawMarkedInstances(grid: GridSpecDto, mark: VisualMarkDto) {
    val stroke = 2.dp.toPx()
    mark.regions.sortedBy { it.order }.forEach { region ->
        val rect = spanRect(region.cells, grid) ?: return@forEach
        val colour = if (region.role == "exception") EvidenceViolet else EvidenceCyan
        val radius = maxOf(8.dp.toPx(), min(rect.width, rect.height) * 0.22f)
        drawCircle(colour.copy(alpha = 0.14f), radius * 1.35f, rect.center)
        drawCircle(colour, radius, rect.center, style = Stroke(stroke))
    }
}

private fun DrawScope.drawMarkedPlanes(grid: GridSpecDto, mark: VisualMarkDto) {
    val colours = listOf(EvidenceCyan, EvidenceViolet, WarmWhite.copy(alpha = 0.8f))
    val stroke = 2.dp.toPx()
    mark.regions.sortedBy { it.order }.take(3).forEachIndexed { index, region ->
        val rect = spanRect(region.cells, grid) ?: return@forEachIndexed
        val colour = colours[index % colours.size]
        drawRect(colour.copy(alpha = 0.12f), rect.topLeft, rect.size)
        drawRect(colour, rect.topLeft, rect.size, style = Stroke(stroke))
    }
}

private fun DrawScope.drawMarkedFindingFallback(grid: GridSpecDto, mark: VisualMarkDto) {
    if (mark.cells.isNotEmpty()) {
        val region = spanRect(mark.cells, grid) ?: return
        drawRect(FindingRed.copy(alpha = 0.16f), region.topLeft, region.size)
        drawRect(FindingRed, region.topLeft, region.size, style = Stroke(2.dp.toPx()))
    } else {
        drawRect(FindingRed.copy(alpha = 0.8f), style = Stroke(2.dp.toPx()))
    }
}

private fun DrawScope.drawMarkedMove(grid: GridSpecDto, mark: VisualMarkDto) {
    val from = spanRect(mark.cells, grid) ?: return
    val to = spanRect(mark.toCells, grid) ?: return
    drawMove(from.center, to, 2.dp.toPx())
}

private fun DrawScope.drawMarkedCrop(grid: GridSpecDto, cells: List<String>) {
    val crop = spanRect(cells, grid) ?: return
    val shade = Color.Black.copy(alpha = 0.55f)
    drawRect(shade, size = androidx.compose.ui.geometry.Size(size.width, crop.top))
    drawRect(
        shade,
        topLeft = Offset(0f, crop.bottom),
        size = androidx.compose.ui.geometry.Size(size.width, size.height - crop.bottom),
    )
    drawRect(
        shade,
        topLeft = Offset(0f, crop.top),
        size = androidx.compose.ui.geometry.Size(crop.left, crop.height),
    )
    drawRect(
        shade,
        topLeft = Offset(crop.right, crop.top),
        size = androidx.compose.ui.geometry.Size(size.width - crop.right, crop.height),
    )
    drawRect(WarmWhite, crop.topLeft, crop.size, style = Stroke(2.dp.toPx()))
}

private fun DrawScope.drawGuide(guide: String, rotation: Int) {
    val colour = WarmWhite.copy(alpha = 0.34f)
    val stroke = 1.dp.toPx()
    val pointStroke = Stroke(stroke)
    when (guide) {
        "none", "fill" -> return
        "golden_spiral" -> drawGoldenSpiral(rotation)
        "centre" -> {
            drawLine(colour, Offset(size.width / 2f, 0f), Offset(size.width / 2f, size.height), stroke)
            drawLine(colour, Offset(0f, size.height / 2f), Offset(size.width, size.height / 2f), stroke)
            drawCircle(
                WarmWhite.copy(alpha = 0.45f),
                radius = 4.dp.toPx(),
                center = Offset(size.width / 2f, size.height / 2f),
                style = pointStroke,
            )
        }
        "diagonals" -> {
            drawLine(colour, Offset.Zero, Offset(size.width, size.height), stroke)
            drawLine(colour, Offset(size.width, 0f), Offset(0f, size.height), stroke)
            val short = min(size.width, size.height)
            drawLine(colour, Offset.Zero, Offset(short, short), stroke)
            drawLine(colour, Offset(size.width, 0f), Offset(size.width - short, short), stroke)
            drawLine(colour, Offset(0f, size.height), Offset(short, size.height - short), stroke)
            drawLine(
                colour,
                Offset(size.width, size.height),
                Offset(size.width - short, size.height - short),
                stroke,
            )
        }
        else -> {
            val fractions = if (guide == "phi") listOf(0.382f, 0.618f) else listOf(1f / 3f, 2f / 3f)
            fractions.forEach { fraction ->
                drawLine(
                    colour,
                    Offset(size.width * fraction, 0f),
                    Offset(size.width * fraction, size.height),
                    stroke,
                )
                drawLine(
                    colour,
                    Offset(0f, size.height * fraction),
                    Offset(size.width, size.height * fraction),
                    stroke,
                )
            }
            fractions.forEach { x ->
                fractions.forEach { y ->
                    drawCircle(
                        WarmWhite.copy(alpha = 0.45f),
                        radius = 4.dp.toPx(),
                        center = Offset(size.width * x, size.height * y),
                        style = pointStroke,
                    )
                }
            }
        }
    }
}

private fun DrawScope.drawGoldenSpiral(rotation: Int) {
    val phi = (1.0 + sqrt(5.0)) / 2.0
    val growth = ln(phi) / (Math.PI / 2.0)
    val orientation = ((rotation % 4) + 4) % 4
    val focus = when (orientation) {
        0 -> Offset(size.width * 0.618f, size.height * 0.382f)
        1 -> Offset(size.width * 0.618f, size.height * 0.618f)
        2 -> Offset(size.width * 0.382f, size.height * 0.618f)
        else -> Offset(size.width * 0.382f, size.height * 0.382f)
    }
    val outer = when (orientation) {
        0 -> Offset(0f, size.height)
        1 -> Offset.Zero
        2 -> Offset(size.width, 0f)
        else -> Offset(size.width, size.height)
    }
    val endAngle = atan2(outer.y - focus.y, outer.x - focus.x).toDouble()
    val quarterTurns = 8
    val thetaMax = quarterTurns * Math.PI / 2.0
    val radiusMax = kotlin.math.hypot(
        (outer.x - focus.x).toDouble(),
        (outer.y - focus.y).toDouble(),
    )
    val path = Path()
    val samples = 180
    repeat(samples + 1) { index ->
        val theta = thetaMax * index / samples
        val radius = radiusMax * exp(growth * (theta - thetaMax))
        val angle = endAngle - thetaMax + theta
        val point = Offset(
            x = (focus.x + radius * cos(angle)).toFloat(),
            y = (focus.y + radius * sin(angle)).toFloat(),
        )
        if (index == 0) path.moveTo(point.x, point.y) else path.lineTo(point.x, point.y)
    }
    val stroke = 1.6.dp.toPx()
    drawPath(path, Color.Black.copy(alpha = 0.5f), style = Stroke(stroke * 2.2f))
    drawPath(path, WarmWhite.copy(alpha = 0.82f), style = Stroke(stroke))
    drawCircle(
        WarmWhite.copy(alpha = 0.7f),
        radius = 5.dp.toPx(),
        center = focus,
        style = Stroke(1.dp.toPx()),
    )
}

private fun DrawScope.drawCompositionEvidence(grid: GridSpecDto, composition: CompositionDto) {
    val stroke = 2.dp.toPx()
    spanRect(composition.subjectCells, grid)?.let { region ->
        drawRect(Amber.copy(alpha = 0.10f), region.topLeft, region.size)
        drawRect(Amber.copy(alpha = 0.82f), region.topLeft, region.size, style = Stroke(stroke))
    }
    composition.horizonRow
        ?.takeIf { it in 1..grid.rows }
        ?.let { row ->
            val y = (row - 0.5f) * size.height / grid.rows
            drawLine(Amber.copy(alpha = 0.86f), Offset(0f, y), Offset(size.width, y), stroke)
        }
    drawSubjectPoint(grid, composition)
}

private fun DrawScope.drawSubjectPoint(grid: GridSpecDto, composition: CompositionDto) {
    subjectPoint(grid, composition)?.let {
        drawCircle(Amber, radius = 4.dp.toPx(), center = it)
    }
}

private fun DrawScope.drawAction(grid: GridSpecDto, composition: CompositionDto) {
    val stroke = 2.dp.toPx()
    val crop = spanRect(composition.suggestedCropCells, grid)
    if (crop != null) {
        val shade = Color.Black.copy(alpha = 0.55f)
        drawRect(shade, size = androidx.compose.ui.geometry.Size(size.width, crop.top))
        drawRect(
            shade,
            topLeft = Offset(0f, crop.bottom),
            size = androidx.compose.ui.geometry.Size(size.width, size.height - crop.bottom),
        )
        drawRect(
            shade,
            topLeft = Offset(0f, crop.top),
            size = androidx.compose.ui.geometry.Size(crop.left, crop.height),
        )
        drawRect(
            shade,
            topLeft = Offset(crop.right, crop.top),
            size = androidx.compose.ui.geometry.Size(size.width - crop.right, crop.height),
        )
        drawRect(WarmWhite, crop.topLeft, crop.size, style = Stroke(stroke))
    }
    if (crop == null) {
        val move = composition.moves.firstOrNull {
            it.kind == "move" && it.fromCells.isNotEmpty() && it.toCells.isNotEmpty()
        }
        val from = move?.let { spanRect(it.fromCells, grid) }
        val to = move?.let { spanRect(it.toCells, grid) }
        if (from != null && to != null) drawMove(from.center, to, stroke)
    }
}

private fun DrawScope.drawFinding(
    grid: GridSpecDto,
    composition: CompositionDto,
    finding: FindingDto,
) {
    val stroke = 2.dp.toPx()
    when (finding.findingId) {
        "no_centre_of_interest" -> {
            spanRect(finding.cells.ifEmpty { composition.subjectCells }, grid)?.let { region ->
                drawRect(FindingRed.copy(alpha = 0.12f), region.topLeft, region.size)
                drawRect(FindingRed, region.topLeft, region.size, style = Stroke(stroke))
            }
        }
        "split_horizon" -> composition.horizonRow
            ?.takeIf { it in 1..grid.rows }
            ?.let { row ->
                val y = (row - 0.5f) * size.height / grid.rows
                drawLine(FindingRed, Offset(0f, y), Offset(size.width, y), stroke * 1.4f)
                drawLine(
                    FindingRed.copy(alpha = 0.65f),
                    Offset(0f, size.height / 2f),
                    Offset(size.width, size.height / 2f),
                    stroke,
                    pathEffect = PathEffect.dashPathEffect(floatArrayOf(stroke * 4, stroke * 3)),
                )
            }
        "off_guide_subject" -> drawPlacementFinding(grid, composition, stroke)
        "colour_cast" -> {
            drawRect(FindingRed.copy(alpha = 0.08f))
            drawRect(FindingRed, style = Stroke(stroke * 1.4f))
        }
        "camera_shake" -> drawRect(FindingRed, style = Stroke(stroke * 1.4f))
        "blown_highlights" -> {
            // Exact clipped pixels are painted into the finding_marked blob by
            // the backend. The border keeps the layer legible for legacy Shots.
            drawRect(FindingRed.copy(alpha = 0.8f), style = Stroke(stroke))
        }
        else -> spanRect(finding.cells, grid)?.let { region ->
            drawRect(FindingRed.copy(alpha = 0.12f), region.topLeft, region.size)
            drawRect(FindingRed, region.topLeft, region.size, style = Stroke(stroke))
        }
    }
}

private fun DrawScope.drawPlacementFinding(
    grid: GridSpecDto,
    composition: CompositionDto,
    stroke: Float,
) {
    val point = subjectPoint(grid, composition) ?: return
    val x = point.x / size.width
    val y = point.y / size.height
    val lines = listOf(1f / 3f, 2f / 3f, 0.382f, 0.618f, 0.5f)
    val nearestX = lines.minBy { kotlin.math.abs(it - x) }
    val nearestY = lines.minBy { kotlin.math.abs(it - y) }
    val target = if (kotlin.math.abs(nearestX - x) >= kotlin.math.abs(nearestY - y)) {
        Offset(size.width * nearestX, point.y)
    } else {
        Offset(point.x, size.height * nearestY)
    }
    drawCircle(FindingRed, radius = 5.dp.toPx(), center = point)
    drawLine(FindingRed, point, target, stroke * 1.2f)
    drawCircle(FindingRed.copy(alpha = 0.9f), radius = 9.dp.toPx(), center = target, style = Stroke(stroke))
}

private fun DrawScope.subjectPoint(grid: GridSpecDto, composition: CompositionDto): Offset? =
    if (composition.subjectX != null && composition.subjectY != null) {
        Offset(size.width * composition.subjectX.toFloat(), size.height * composition.subjectY.toFloat())
    } else {
        spanRect(composition.subjectCells, grid)?.center
    }

private fun DrawScope.drawMove(start: Offset, target: Rect, stroke: Float) {
    drawRect(
        Amber.copy(alpha = 0.7f),
        target.topLeft,
        target.size,
        style = Stroke(stroke, pathEffect = PathEffect.dashPathEffect(floatArrayOf(stroke * 3, stroke * 2))),
    )
    drawLine(Amber, start, target.center, stroke * 1.2f)
    drawCircle(Amber, radius = stroke * 1.8f, center = start)
    val angle = atan2(target.center.y - start.y, target.center.x - start.x)
    val head = 12.dp.toPx()
    val path = Path().apply {
        moveTo(target.center.x, target.center.y)
        lineTo(
            target.center.x - head * cos(angle - 0.5f),
            target.center.y - head * sin(angle - 0.5f),
        )
        lineTo(
            target.center.x - head * cos(angle + 0.5f),
            target.center.y - head * sin(angle + 0.5f),
        )
        close()
    }
    drawPath(path, Amber)
}

private fun DrawScope.spanRect(refs: List<String>, grid: GridSpecDto): Rect? {
    val span = span(refs, grid) ?: return null
    return Rect(
        left = span.left * size.width / grid.cols,
        top = span.top * size.height / grid.rows,
        right = span.right * size.width / grid.cols,
        bottom = span.bottom * size.height / grid.rows,
    )
}

private fun DrawScope.cellCentres(refs: List<String>, grid: GridSpecDto): List<Offset> =
    refs.mapNotNull { ref ->
        CELL.matchEntire(ref.trim().uppercase())?.let { match ->
            val col = match.groupValues[1][0] - 'A'
            val row = match.groupValues[2].toIntOrNull()?.minus(1) ?: return@let null
            if (col !in 0 until grid.cols || row !in 0 until grid.rows) {
                null
            } else {
                Offset(
                    x = (col + 0.5f) * size.width / grid.cols,
                    y = (row + 0.5f) * size.height / grid.rows,
                )
            }
        }
    }

private data class CellSpan(val left: Float, val top: Float, val right: Float, val bottom: Float)

private fun span(refs: List<String>, grid: GridSpecDto): CellSpan? {
    val cells = refs.mapNotNull { ref ->
        CELL.matchEntire(ref.trim().uppercase())?.let { match ->
            val col = match.groupValues[1][0] - 'A'
            val row = match.groupValues[2].toIntOrNull()?.minus(1) ?: return@let null
            if (col !in 0 until grid.cols || row !in 0 until grid.rows) null else col to row
        }
    }
    if (cells.isEmpty()) return null
    return CellSpan(
        left = cells.minOf { it.first }.toFloat(),
        top = cells.minOf { it.second }.toFloat(),
        right = cells.maxOf { it.first }.plus(1).toFloat(),
        bottom = cells.maxOf { it.second }.plus(1).toFloat(),
    )
}

fun plainCellReferences(text: String, grid: GridSpecDto?): String {
    if (text.isBlank() || grid == null) return text
    val cellsRewritten = CELL_RUN.replace(text) { match ->
        val refs = CELL.findAll(match.value.uppercase()).map { it.value }.toList()
        place(refs, grid).ifBlank { "the shown area" }
    }
    val columnsRewritten = COLUMN_RUN.replace(cellsRewritten) { match ->
        val prefix = match.groupValues[1].lowercase().takeIf(String::isNotBlank)
        val first = match.groupValues[2][0] - 'A'
        val last = match.groupValues[3].firstOrNull()?.minus('A') ?: first
        val phrase = horizontalPlace(first, last, grid)
        listOfNotNull(prefix, phrase).joinToString(" ")
    }
    return ROW_RUN.replace(columnsRewritten) { match ->
        val prefix = match.groupValues[1].lowercase().takeIf(String::isNotBlank)
        val first = match.groupValues[2].toIntOrNull()?.minus(1) ?: 0
        val last = match.groupValues[3].toIntOrNull()?.minus(1) ?: first
        val phrase = verticalPlace(first, last, grid)
        listOfNotNull(prefix, phrase).joinToString(" ")
    }
}

private fun horizontalPlace(first: Int, last: Int, grid: GridSpecDto): String {
    val left = minOf(first, last).coerceIn(0, grid.cols - 1)
    val right = maxOf(first, last).coerceIn(0, grid.cols - 1) + 1
    if ((right - left).toFloat() / grid.cols > 0.6f) return "the width of the frame"
    val centre = (left + right) / 2f / grid.cols
    return when {
        centre < 1f / 3f -> "the left side of the frame"
        centre > 2f / 3f -> "the right side of the frame"
        else -> "the centre of the frame"
    }
}

private fun verticalPlace(first: Int, last: Int, grid: GridSpecDto): String {
    val top = minOf(first, last).coerceIn(0, grid.rows - 1)
    val bottom = maxOf(first, last).coerceIn(0, grid.rows - 1) + 1
    if ((bottom - top).toFloat() / grid.rows > 0.6f) return "the height of the frame"
    val centre = (top + bottom) / 2f / grid.rows
    return when {
        centre < 1f / 3f -> "the top of the frame"
        centre > 2f / 3f -> "the bottom of the frame"
        else -> "the middle of the frame"
    }
}

private fun place(refs: List<String>, grid: GridSpecDto): String {
    val box = span(refs, grid) ?: return ""
    val width = (box.right - box.left) / grid.cols
    val height = (box.bottom - box.top) / grid.rows
    val wide = width > 0.6f
    val tall = height > 0.6f
    if (wide && tall) return "most of the frame"

    val x = (box.left + box.right) / 2f / grid.cols
    val y = (box.top + box.bottom) / 2f / grid.rows
    val horizontal = when {
        x < 1f / 3f -> "left"
        x > 2f / 3f -> "right"
        else -> "centre"
    }
    val vertical = when {
        y < 1f / 3f -> "top"
        y > 2f / 3f -> "bottom"
        else -> "middle"
    }
    if (wide) return if (vertical == "middle") "across the middle" else "across the $vertical"
    if (tall) return if (horizontal == "centre") "down the centre" else "down the $horizontal"
    if (vertical == "middle" && horizontal == "centre") return "the centre of the frame"
    if (vertical == "middle") return "the $horizontal of the frame"
    if (horizontal == "centre") return "the $vertical of the frame"
    return "the $vertical $horizontal"
}

fun guideLabel(guide: String): String = when (guide) {
    "phi" -> "Phi grid"
    "golden_spiral" -> "Golden spiral"
    "diagonals" -> "Diagonal"
    "centre" -> "Centre"
    "fill" -> "Frame fill"
    "none" -> "No"
    else -> "Thirds"
}

fun findingLabel(findingId: String): String = when (findingId) {
    "camera_shake" -> "Camera shake risk"
    "off_guide_subject" -> "Subject placement"
    "split_horizon" -> "Split horizon"
    "no_centre_of_interest" -> "Centre of interest"
    "blown_highlights" -> "Blown highlights"
    "colour_cast" -> "Colour cast"
    else -> "Measured Finding"
}

private val CELL = Regex("^([A-Z])(\\d{1,2})$")
private val CELL_RUN = Regex(
    "\\b[A-H]\\d{1,2}\\b(?:\\s*(?:[-–—,/:]|to|and|through)\\s*\\b[A-H]\\d{1,2}\\b)*",
    RegexOption.IGNORE_CASE,
)
private val COLUMN_RUN = Regex(
    "\\b(?:(from|in|across|within|through|at)\\s+)?columns?\\s+([A-H])(?:\\s*(?:[-–—:]|to|through)\\s*([A-H]))?\\b",
    RegexOption.IGNORE_CASE,
)
private val ROW_RUN = Regex(
    "\\b(?:(from|in|across|within|through|at)\\s+)?rows?\\s+(\\d{1,2})(?:\\s*(?:[-–—:]|to|through)\\s*(\\d{1,2}))?\\b",
    RegexOption.IGNORE_CASE,
)
