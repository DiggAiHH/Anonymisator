package com.anonymisator.sdk.api

import com.anonymisator.sdk.BuildConfig
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

/**
 * Singleton Retrofit client factory for API communication.
 * Configures OkHttp with appropriate timeouts and interceptors.
 */
object RetrofitClient {
    
    private const val DEFAULT_TIMEOUT_SECONDS = 60L
    private const val DEFAULT_CONNECT_TIMEOUT_SECONDS = 30L
    
    @Volatile
    private var backendRetrofit: Retrofit? = null
    
    @Volatile
    private var mcpRetrofit: Retrofit? = null
    
    /**
     * Configuration for SDK initialization.
     */
    data class Config(
        val backendBaseUrl: String = BuildConfig.DEFAULT_API_URL,
        val mcpBaseUrl: String = "http://10.0.2.2:3000",
        val timeoutSeconds: Long = DEFAULT_TIMEOUT_SECONDS,
        val connectTimeoutSeconds: Long = DEFAULT_CONNECT_TIMEOUT_SECONDS,
        val enableLogging: Boolean = BuildConfig.DEBUG
    )
    
    private var config: Config = Config()
    
    /**
     * Initialize the SDK with custom configuration.
     * Call this before using any API methods.
     */
    fun init(config: Config) {
        this.config = config
        backendRetrofit = null
        mcpRetrofit = null
    }
    
    /**
     * Update the backend base URL at runtime.
     * Useful for switching between environments.
     */
    fun setBackendBaseUrl(url: String) {
        config = config.copy(backendBaseUrl = url)
        backendRetrofit = null
    }
    
    /**
     * Update the MCP server base URL at runtime.
     */
    fun setMcpBaseUrl(url: String) {
        config = config.copy(mcpBaseUrl = url)
        mcpRetrofit = null
    }
    
    /**
     * Create OkHttpClient with configured interceptors and timeouts.
     */
    private fun createOkHttpClient(): OkHttpClient {
        val builder = OkHttpClient.Builder()
            .connectTimeout(config.connectTimeoutSeconds, TimeUnit.SECONDS)
            .readTimeout(config.timeoutSeconds, TimeUnit.SECONDS)
            .writeTimeout(config.timeoutSeconds, TimeUnit.SECONDS)
            .retryOnConnectionFailure(true)
        
        // Add logging interceptor only in debug builds
        if (config.enableLogging) {
            val loggingInterceptor = HttpLoggingInterceptor().apply {
                // Use HEADERS level to avoid logging PHI in request/response bodies
                level = HttpLoggingInterceptor.Level.HEADERS
            }
            builder.addInterceptor(loggingInterceptor)
        }
        
        return builder.build()
    }
    
    /**
     * Get or create Retrofit instance for backend Privacy Proxy API.
     */
    private fun getBackendRetrofit(): Retrofit {
        return backendRetrofit ?: synchronized(this) {
            backendRetrofit ?: Retrofit.Builder()
                .baseUrl(ensureTrailingSlash(config.backendBaseUrl))
                .client(createOkHttpClient())
                .addConverterFactory(GsonConverterFactory.create())
                .build()
                .also { backendRetrofit = it }
        }
    }
    
    /**
     * Get or create Retrofit instance for MCP Tool Server API.
     */
    private fun getMcpRetrofit(): Retrofit {
        return mcpRetrofit ?: synchronized(this) {
            mcpRetrofit ?: Retrofit.Builder()
                .baseUrl(ensureTrailingSlash(config.mcpBaseUrl))
                .client(createOkHttpClient())
                .addConverterFactory(GsonConverterFactory.create())
                .build()
                .also { mcpRetrofit = it }
        }
    }
    
    /**
     * Get the AnonymisatorApi instance for backend calls.
     */
    fun getAnonymisatorApi(): AnonymisatorApi {
        return getBackendRetrofit().create(AnonymisatorApi::class.java)
    }
    
    /**
     * Get the McpToolsApi instance for MCP server calls.
     */
    fun getMcpToolsApi(): McpToolsApi {
        return getMcpRetrofit().create(McpToolsApi::class.java)
    }
    
    /**
     * Ensure URL has trailing slash for Retrofit base URL.
     */
    private fun ensureTrailingSlash(url: String): String {
        return if (url.endsWith("/")) url else "$url/"
    }
    
    /**
     * Get current configuration.
     */
    fun getConfig(): Config = config
}
