package com.anonymisator.sdk.model

import com.google.gson.annotations.SerializedName

/**
 * Request model for /v1/securedoc/generate endpoint.
 * Matches the backend SecureDocRequest schema.
 * 
 * @property practiceId Unique identifier for the medical practice (1-100 chars)
 * @property task The processing task to perform (e.g., "summarize", "analyze")
 * @property text The medical text containing PHI to be anonymized (1-50000 chars)
 */
data class SecureDocRequest(
    @SerializedName("practice_id")
    val practiceId: String,
    
    @SerializedName("task")
    val task: String,
    
    @SerializedName("text")
    val text: String
) {
    companion object {
        const val MAX_TEXT_LENGTH = 50_000
        const val MAX_PRACTICE_ID_LENGTH = 100
        const val MAX_TASK_LENGTH = 100
    }
    
    /**
     * Validates the request before sending to API.
     * @return List of validation error messages, empty if valid
     */
    fun validate(): List<String> {
        val errors = mutableListOf<String>()
        
        if (practiceId.isBlank()) {
            errors.add("Practice ID cannot be empty")
        } else if (practiceId.length > MAX_PRACTICE_ID_LENGTH) {
            errors.add("Practice ID exceeds maximum length of $MAX_PRACTICE_ID_LENGTH")
        }
        
        if (task.isBlank()) {
            errors.add("Task cannot be empty")
        } else if (task.length > MAX_TASK_LENGTH) {
            errors.add("Task exceeds maximum length of $MAX_TASK_LENGTH")
        }
        
        if (text.isBlank()) {
            errors.add("Text cannot be empty")
        } else if (text.length > MAX_TEXT_LENGTH) {
            errors.add("Text exceeds maximum length of $MAX_TEXT_LENGTH")
        }
        
        // Check for control characters (matching backend validation)
        text.forEach { char ->
            if (char.code < 32 && char !in listOf('\n', '\t', '\r')) {
                errors.add("Text contains invalid control characters")
                return errors
            }
        }
        
        return errors
    }
}
