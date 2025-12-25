package com.anonymisator.sdk

import com.anonymisator.sdk.api.RetrofitClient
import com.anonymisator.sdk.exception.AnonymisatorException
import com.anonymisator.sdk.model.FreeSlotsResponse
import com.anonymisator.sdk.model.HealthResponse
import com.anonymisator.sdk.model.SecureDocRequest
import com.anonymisator.sdk.model.SecureDocResponse
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import retrofit2.Response
import java.io.IOException

/**
 * Main client for interacting with the Anonymisator SecureDoc Flow Privacy Proxy.
 * 
 * This SDK provides a simple interface to:
 * - Process medical documents with PHI protection
 * - Query available appointment slots
 * - Check service health status
 * 
 * Usage:
 * ```kotlin
 * // Initialize SDK
 * AnonymisatorClient.init(AnonymisatorClient.Config(
 *     backendBaseUrl = "https://your-backend.com"
 * ))
 * 
 * // Use the client
 * val client = AnonymisatorClient()
 * val response = client.generateSecureDoc(
 *     practiceId = "clinic_123",
 *     task = "summarize",
 *     text = "Patient Dr. John Smith, DOB 01/15/1980..."
 * )
 * ```
 */
class AnonymisatorClient {
    
    private val api = RetrofitClient.getAnonymisatorApi()
    private val mcpApi = RetrofitClient.getMcpToolsApi()
    
    companion object {
        /**
         * Initialize the SDK with custom configuration.
         * Must be called before using any SDK methods.
         * 
         * @param config SDK configuration including base URLs and timeouts
         */
        fun init(config: RetrofitClient.Config) {
            RetrofitClient.init(config)
        }
        
        /**
         * Quick initialization with just the backend URL.
         * 
         * @param backendUrl Base URL of the SecureDoc Flow backend
         */
        fun init(backendUrl: String) {
            RetrofitClient.init(RetrofitClient.Config(backendBaseUrl = backendUrl))
        }
        
        /**
         * Update backend URL at runtime.
         */
        fun setBackendUrl(url: String) {
            RetrofitClient.setBackendBaseUrl(url)
        }
    }
    
    /**
     * Generate an LLM-enhanced document with PHI protection.
     * 
     * The backend will:
     * 1. Detect and anonymize PHI (names, dates, IDs, etc.) in the input
     * 2. Send only the anonymized text to the LLM
     * 3. Re-identify the response with original PHI values
     * 4. Return the complete de-anonymized response
     * 
     * @param practiceId Unique identifier for your medical practice
     * @param task The processing task (e.g., "summarize", "analyze", "translate")
     * @param text Medical text containing PHI to be processed
     * @return SecureDocResponse with the processed, de-anonymized text
     * @throws AnonymisatorException.ValidationException if input validation fails
     * @throws AnonymisatorException.NetworkException if network error occurs
     * @throws AnonymisatorException.ApiException if API returns an error
     */
    suspend fun generateSecureDoc(
        practiceId: String,
        task: String,
        text: String
    ): SecureDocResponse = withContext(Dispatchers.IO) {
        // Create and validate request
        val request = SecureDocRequest(
            practiceId = practiceId,
            task = task,
            text = text
        )
        
        val validationErrors = request.validate()
        if (validationErrors.isNotEmpty()) {
            throw AnonymisatorException.ValidationException(
                validationErrors.joinToString("; ")
            )
        }
        
        // Make API call
        executeRequest { api.generateSecureDoc(request) }
    }
    
    /**
     * Check the health status of the backend service.
     * 
     * @return HealthResponse with service status
     * @throws AnonymisatorException.NetworkException if network error occurs
     */
    suspend fun checkHealth(): HealthResponse = withContext(Dispatchers.IO) {
        executeRequest { api.healthCheck() }
    }
    
    /**
     * Get service information from the root endpoint.
     * 
     * @return HealthResponse with service info
     * @throws AnonymisatorException.NetworkException if network error occurs
     */
    suspend fun getServiceInfo(): HealthResponse = withContext(Dispatchers.IO) {
        executeRequest { api.getServiceInfo() }
    }
    
    /**
     * Get available appointment slots from the MCP server.
     * 
     * Returns only free time slots with no patient information (data-minimized).
     * 
     * @param date Optional date in YYYY-MM-DD format. Defaults to today.
     * @return FreeSlotsResponse with available time slots
     * @throws AnonymisatorException.ValidationException if date format is invalid
     * @throws AnonymisatorException.NetworkException if network error occurs
     */
    suspend fun getFreeSlots(date: String? = null): FreeSlotsResponse = withContext(Dispatchers.IO) {
        // Validate date format if provided
        if (date != null && !date.matches(Regex("^\\d{4}-\\d{2}-\\d{2}$"))) {
            throw AnonymisatorException.ValidationException(
                "Invalid date format. Use YYYY-MM-DD"
            )
        }
        
        executeRequest { mcpApi.getFreeSlots(date) }
    }
    
    /**
     * Check the health status of the MCP server.
     * 
     * @return HealthResponse with service status
     * @throws AnonymisatorException.NetworkException if network error occurs
     */
    suspend fun checkMcpHealth(): HealthResponse = withContext(Dispatchers.IO) {
        executeRequest { mcpApi.healthCheck() }
    }
    
    /**
     * Execute a Retrofit request with proper error handling.
     * Converts network and HTTP errors to appropriate exceptions.
     */
    private suspend fun <T> executeRequest(
        apiCall: suspend () -> Response<T>
    ): T {
        try {
            val response = apiCall()
            
            if (response.isSuccessful) {
                return response.body() 
                    ?: throw AnonymisatorException.ParseException("Empty response body")
            }
            
            // Handle error response
            val errorBody = response.errorBody()?.string() ?: "Unknown error"
            throw AnonymisatorException.ApiException(
                httpCode = response.code(),
                apiMessage = errorBody
            )
            
        } catch (e: IOException) {
            throw AnonymisatorException.NetworkException(
                message = "Network error: ${e.message}",
                cause = e
            )
        } catch (e: AnonymisatorException) {
            throw e
        } catch (e: Exception) {
            throw AnonymisatorException.NetworkException(
                message = "Unexpected error: ${e.message}",
                cause = e
            )
        }
    }
}
