package com.anonymisator.sdk.model

import com.google.gson.annotations.SerializedName

/**
 * Health check response from the API.
 * Used to verify connectivity and service status.
 */
data class HealthResponse(
    @SerializedName("status")
    val status: String,
    
    @SerializedName("service")
    val service: String? = null,
    
    @SerializedName("version")
    val version: String? = null
) {
    val isHealthy: Boolean
        get() = status.equals("healthy", ignoreCase = true) || 
                status.equals("operational", ignoreCase = true)
}
