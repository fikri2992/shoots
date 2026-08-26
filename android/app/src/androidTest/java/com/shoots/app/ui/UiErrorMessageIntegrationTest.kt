package com.shoots.app.ui

import java.io.IOException
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import retrofit2.HttpException
import retrofit2.Response

class UiErrorMessageIntegrationTest {
    @Test
    fun networkFailureProducesAReadableMessageOnAndroid() {
        assertEquals("Connection reset", friendlyMessage(IOException("Connection reset")))
    }

    @Test
    fun backendDetailProducesAReadableMessageOnAndroid() {
        assertEquals(
            "Device session expired",
            friendlyMessage(IllegalStateException("{\"detail\":\"Device session expired\"}")),
        )
    }

    @Test
    fun expiredDeviceSessionRequestsForegroundAuthentication() {
        val response = Response.error<Unit>(
            401,
            "{\"detail\":\"Device session expired\"}"
                .toResponseBody("application/json".toMediaType()),
        )
        val exception = HttpException(response)

        assertTrue(isAuthenticationFailure(exception))
        assertEquals("Sign in again to continue.", friendlyMessage(exception))
    }
}
