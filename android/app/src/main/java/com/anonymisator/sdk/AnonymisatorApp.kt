package com.anonymisator.sdk

import android.app.Application
import com.anonymisator.sdk.api.RetrofitClient

/**
 * Application class for AnonymisatorSDK.
 * Initializes the SDK with default configuration on app startup.
 */
class AnonymisatorApp : Application() {
    
    override fun onCreate() {
        super.onCreate()
        
        // Initialize SDK with default configuration
        // In production, these URLs should be loaded from a configuration file or build config
        RetrofitClient.init(
            RetrofitClient.Config(
                backendBaseUrl = BuildConfig.DEFAULT_API_URL,
                mcpBaseUrl = "http://10.0.2.2:3000",
                enableLogging = BuildConfig.DEBUG
            )
        )
    }
}
