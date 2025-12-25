package com.anonymisator.sdk.api

import com.anonymisator.sdk.model.FreeSlotsResponse
import com.anonymisator.sdk.model.HealthResponse
import com.anonymisator.sdk.model.SecureDocRequest
import com.anonymisator.sdk.model.SecureDocResponse
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query

/**
 * Retrofit API interface for SecureDoc Flow Privacy Proxy.
 * Defines all available API endpoints.
 */
interface AnonymisatorApi {
    
    /**
     * Generate LLM-enhanced document with PHI protection.
     * 
     * The backend will:
     * 1. Anonymize PHI in the input text
     * 2. Send only anonymized text to the LLM
     * 3. Re-identify the LLM response
     * 4. Return the fully de-anonymized result
     * 
     * @param request SecureDocRequest containing practice_id, task, and text
     * @return Response with the processed text
     */
    @POST("/v1/securedoc/generate")
    suspend fun generateSecureDoc(
        @Body request: SecureDocRequest
    ): Response<SecureDocResponse>
    
    /**
     * Backend health check endpoint.
     * Use to verify connectivity to the Privacy Proxy.
     */
    @GET("/health")
    suspend fun healthCheck(): Response<HealthResponse>
    
    /**
     * Root endpoint with service information.
     */
    @GET("/")
    suspend fun getServiceInfo(): Response<HealthResponse>
}

/**
 * API interface for the MCP Tool Server.
 * Provides data-minimized tool endpoints.
 */
interface McpToolsApi {
    
    /**
     * Get available appointment slots for a given date.
     * Returns only free time slots with no patient information.
     * 
     * @param date Optional date in YYYY-MM-DD format. Defaults to today if not provided.
     * @return Response with available time slots
     */
    @GET("/tools/get_free_slots")
    suspend fun getFreeSlots(
        @Query("date") date: String? = null
    ): Response<FreeSlotsResponse>
    
    /**
     * MCP server health check endpoint.
     */
    @GET("/health")
    suspend fun healthCheck(): Response<HealthResponse>
}
