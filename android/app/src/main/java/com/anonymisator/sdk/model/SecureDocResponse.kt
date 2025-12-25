package com.anonymisator.sdk.model

import com.google.gson.annotations.SerializedName

/**
 * Response model from /v1/securedoc/generate endpoint.
 * Contains the re-identified LLM output with PHI restored.
 * 
 * @property outputText The processed text with original PHI values restored
 * @property status Status of the operation ("success" on successful completion)
 */
data class SecureDocResponse(
    @SerializedName("output_text")
    val outputText: String,
    
    @SerializedName("status")
    val status: String
) {
    /**
     * Check if the response indicates successful processing.
     */
    val isSuccess: Boolean
        get() = status.equals("success", ignoreCase = true)
}
