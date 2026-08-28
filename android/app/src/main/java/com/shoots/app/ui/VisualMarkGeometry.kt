package com.shoots.app.ui

private val CELL_REF = Regex("^([A-Z])(\\d{1,2})$")

private data class CellPoint(val col: Int, val row: Int)

/**
 * Return one straight cell path only when every point is demonstrably on the
 * same row, column, or 45-degree diagonal. A broad cell cloud is not a line.
 */
internal fun collinearCellPath(refs: List<String>): List<String>? {
    val cells = refs.mapNotNull { ref ->
        CELL_REF.matchEntire(ref.trim().uppercase())?.let { match ->
            val row = match.groupValues[2].toIntOrNull()?.minus(1) ?: return@let null
            CellPoint(match.groupValues[1][0] - 'A', row)
        }
    }.distinct()
    if (cells.size < 2) return null
    val sameRow = cells.all { it.row == cells.first().row }
    val sameColumn = cells.all { it.col == cells.first().col }
    val sameDownDiagonal = cells.all {
        it.col - it.row == cells.first().col - cells.first().row
    }
    val sameUpDiagonal = cells.all {
        it.col + it.row == cells.first().col + cells.first().row
    }
    if (!sameRow && !sameColumn && !sameDownDiagonal && !sameUpDiagonal) return null
    val ordered = cells.sortedWith(
        if (sameColumn) {
            compareBy<CellPoint> { it.row }
        } else {
            compareBy<CellPoint>({ it.col }, { it.row })
        }
    )
    return ordered.map { "${'A' + it.col}${it.row + 1}" }
}
