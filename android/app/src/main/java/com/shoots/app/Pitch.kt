package com.shoots.app

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import kotlin.math.atan2
import kotlin.math.roundToInt

/**
 * How far from level the camera is aimed, in degrees: 0 is straight at the
 * horizon, negative is aimed down, positive up. Read off gravity, so it needs
 * no calibration and costs nothing.
 *
 * This is the one dimension of the Tendency Profile that no photograph can
 * carry (`domain/tendency.py`): a file that arrived through Drive has no idea
 * what height it was taken from, which is why the profile lists height as a
 * declared blind spot. The camera is what closes it — and eye level is the
 * default nobody notices they never leave.
 */
class Pitch(context: Context) : SensorEventListener {

    /** Degrees from level, or null until the first reading arrives. */
    var degrees: Float? = null
        private set

    /** Slow enough to be readable, fast enough to follow a crouch. */
    private val smoothing = 0.15f
    private val sensors = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private val gravity = sensors.getDefaultSensor(Sensor.TYPE_GRAVITY)
        ?: sensors.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)

    fun start() {
        gravity?.let { sensors.registerListener(this, it, SensorManager.SENSOR_DELAY_UI) }
    }

    fun stop() {
        sensors.unregisterListener(this)
    }

    override fun onSensorChanged(event: SensorEvent) {
        // Portrait, camera at the horizon, is gravity straight down the y axis.
        // Screen up on a table is gravity along z, and the lens is aimed at the
        // floor: that reads -90.
        val raw = Math.toDegrees(atan2(-event.values[2], event.values[1]).toDouble()).toFloat()
        degrees = degrees?.let { it + (raw - it) * smoothing } ?: raw
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) = Unit

    /** The bucket `domain/tendency.py` will file this shot under. */
    fun label(): String = when (val d = degrees) {
        null -> ""
        else -> when {
            d <= -20f -> "shooting down"
            d >= 20f -> "shooting up"
            else -> "eye level"
        }
    }

    fun rounded(): Int? = degrees?.roundToInt()
}
