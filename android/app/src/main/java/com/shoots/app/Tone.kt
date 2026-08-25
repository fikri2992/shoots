package com.shoots.app

/**
 * The viewfinder's share of backend/app/imaging/tone.py — same constants,
 * same arithmetic, so what the zebras warn about is exactly what the panel
 * will later hold against the frame. Pure: no Android imports.
 */
object Tone {
    /** Luma above this is a blown pixel. Mirrors tone.py CLIP_HIGH. */
    const val CLIP_HIGH = 250

    /** The frame-level Fault threshold: blown share above this percent. */
    const val BLOWN_SHARE_PCT = 2.0f

    /** How much of a block must be blown before the zebra covers it. */
    const val BLOCK_BLOWN_FRACTION = 0.3f

    /** Analysis grid width in blocks; rows follow the frame's aspect. */
    const val BLOCK_COLS = 48

    /** Sample every Nth pixel in each axis — plenty at analysis resolution. */
    private const val STEP = 2

    class BlownMap(
        val cols: Int,
        val rows: Int,
        /** Row-major, true where the block is mostly blown. */
        val blocks: BooleanArray,
        /** Percent of sampled pixels above CLIP_HIGH, whole frame. */
        val sharePct: Float,
    )

    /**
     * Read a Y (luma) plane and report where the highlights are gone.
     * [rowStride] is the plane's stride, which may exceed [width].
     */
    fun blownMap(luma: ByteArray, width: Int, height: Int, rowStride: Int): BlownMap {
        val cols = BLOCK_COLS
        val blockSize = maxOf(1, width / cols)
        val rows = maxOf(1, height / blockSize)
        val blownCount = IntArray(cols * rows)
        val totalCount = IntArray(cols * rows)
        var blownAll = 0
        var totalAll = 0

        var y = 0
        while (y < rows * blockSize && y < height) {
            val by = y / blockSize
            val rowStart = y * rowStride
            var x = 0
            while (x < cols * blockSize && x < width) {
                val bx = x / blockSize
                val v = luma[rowStart + x].toInt() and 0xFF
                val i = by * cols + bx
                totalCount[i]++
                totalAll++
                if (v > CLIP_HIGH) {
                    blownCount[i]++
                    blownAll++
                }
                x += STEP
            }
            y += STEP
        }

        val blocks = BooleanArray(cols * rows) { i ->
            totalCount[i] > 0 && blownCount[i].toFloat() / totalCount[i] >= BLOCK_BLOWN_FRACTION
        }
        val share = if (totalAll == 0) 0f else blownAll.toFloat() / totalAll * 100f
        return BlownMap(cols, rows, blocks, share)
    }

    /**
     * Rotate a block grid clockwise by the sensor-to-display angle so the
     * overlay lands on what the preview actually shows.
     */
    fun rotated(map: BlownMap, degrees: Int): BlownMap = when ((degrees % 360 + 360) % 360) {
        90 -> BlownMap(
            map.rows, map.cols,
            BooleanArray(map.blocks.size) { i ->
                val r = i / map.rows
                val c = i % map.rows
                map.blocks[(map.rows - 1 - c) * map.cols + r]
            },
            map.sharePct,
        )
        180 -> BlownMap(
            map.cols, map.rows,
            BooleanArray(map.blocks.size) { i -> map.blocks[map.blocks.size - 1 - i] },
            map.sharePct,
        )
        270 -> BlownMap(
            map.rows, map.cols,
            BooleanArray(map.blocks.size) { i ->
                val r = i / map.rows
                val c = i % map.rows
                map.blocks[c * map.cols + (map.cols - 1 - r)]
            },
            map.sharePct,
        )
        else -> map
    }
}
