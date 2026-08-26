package com.shoots.app.notifications

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Intent
import android.net.Uri
import androidx.core.app.NotificationCompat
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import com.google.firebase.installations.FirebaseInstallations
import com.shoots.app.MainActivity
import com.shoots.app.R
import com.shoots.app.work.PhoneSourceScheduler

class ShootsMessagingService : FirebaseMessagingService() {
    @Suppress("OVERRIDE_DEPRECATION")
    override fun onNewToken(token: String) {
        FirebaseInstallations.getInstance().id.addOnSuccessListener { fid ->
            PhoneSourceScheduler.registerNotificationTarget(this, fid)
        }
    }

    override fun onMessageReceived(message: RemoteMessage) {
        val route = message.data["route"].orEmpty().ifBlank { "now" }
        val title = message.notification?.title ?: "Shoots"
        val body = message.notification?.body ?: "Shoots has an update."
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(
            NotificationChannel(CHANNEL, "Capture Session updates", NotificationManager.IMPORTANCE_DEFAULT)
        )
        val intent = Intent(this, MainActivity::class.java).apply {
            data = Uri.parse("shoots://open/$route")
            flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP
        }
        val pending = PendingIntent.getActivity(
            this,
            route.hashCode(),
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        manager.notify(
            message.messageId?.hashCode() ?: route.hashCode(),
            NotificationCompat.Builder(this, CHANNEL)
                .setSmallIcon(R.drawable.shoots_icon)
                .setContentTitle(title)
                .setContentText(body)
                .setAutoCancel(true)
                .setContentIntent(pending)
                .build(),
        )
    }

    private companion object {
        const val CHANNEL = "capture-session"
    }
}
