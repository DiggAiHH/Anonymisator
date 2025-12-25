package com.anonymisator.sdk.exception

/**
 * Custom exception hierarchy for AnonymisatorSDK.
 * Provides specific error types for better error handling by consumers.
 */
sealed class AnonymisatorException(
    message: String,
    cause: Throwable? = null
) : Exception(message, cause) {
    
    /**
     * Thrown when network connectivity is unavailable or request times out.
     */
    class NetworkException(
        message: String = "Network error occurred",
        cause: Throwable? = null
    ) : AnonymisatorException(message, cause)
    
    /**
     * Thrown when the API returns an error response.
     * @param httpCode The HTTP status code returned
     * @param apiMessage The error message from the API
     */
    class ApiException(
        val httpCode: Int,
        val apiMessage: String,
        cause: Throwable? = null
    ) : AnonymisatorException("API error ($httpCode): $apiMessage", cause)
    
    /**
     * Thrown when input validation fails before making API call.
     */
    class ValidationException(
        message: String
    ) : AnonymisatorException(message)
    
    /**
     * Thrown when response parsing fails.
     */
    class ParseException(
        message: String = "Failed to parse API response",
        cause: Throwable? = null
    ) : AnonymisatorException(message, cause)
    
    /**
     * Thrown when SDK is not properly initialized.
     */
    class InitializationException(
        message: String = "SDK not initialized. Call AnonymisatorClient.init() first."
    ) : AnonymisatorException(message)
}
