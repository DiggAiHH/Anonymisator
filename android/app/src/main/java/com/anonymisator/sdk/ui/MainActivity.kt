package com.anonymisator.sdk.ui

import android.graphics.Color
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.anonymisator.sdk.AnonymisatorClient
import com.anonymisator.sdk.R
import com.anonymisator.sdk.api.RetrofitClient
import com.anonymisator.sdk.databinding.ActivityMainBinding
import com.anonymisator.sdk.exception.AnonymisatorException
import kotlinx.coroutines.launch

/**
 * Main activity demonstrating the AnonymisatorSDK functionality.
 * Provides a UI for testing PHI anonymization with the backend service.
 */
class MainActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityMainBinding
    private lateinit var client: AnonymisatorClient
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        client = AnonymisatorClient()
        
        setupListeners()
        checkServiceHealth()
    }
    
    private fun setupListeners() {
        binding.submitButton.setOnClickListener {
            processDocument()
        }
        
        binding.clearButton.setOnClickListener {
            clearFields()
        }
        
        binding.refreshButton.setOnClickListener {
            updateApiUrl()
            checkServiceHealth()
        }
        
        // Update API URL when focus is lost
        binding.apiUrlInput.setOnFocusChangeListener { _, hasFocus ->
            if (!hasFocus) {
                updateApiUrl()
            }
        }
    }
    
    private fun updateApiUrl() {
        val url = binding.apiUrlInput.text?.toString()?.trim()
        if (!url.isNullOrEmpty()) {
            AnonymisatorClient.setBackendUrl(url)
            // Recreate client with new URL
            client = AnonymisatorClient()
        }
    }
    
    private fun checkServiceHealth() {
        setConnectionStatus(StatusType.CHECKING, "Checking connection...")
        
        lifecycleScope.launch {
            try {
                val health = client.checkHealth()
                if (health.isHealthy) {
                    setConnectionStatus(StatusType.CONNECTED, "Connected to SecureDoc Flow")
                } else {
                    setConnectionStatus(StatusType.ERROR, "Service unhealthy: ${health.status}")
                }
            } catch (e: AnonymisatorException) {
                setConnectionStatus(StatusType.ERROR, "Connection failed: ${getErrorMessage(e)}")
            } catch (e: Exception) {
                setConnectionStatus(StatusType.ERROR, "Connection failed: ${e.message}")
            }
        }
    }
    
    private fun processDocument() {
        val practiceId = binding.practiceIdInput.text?.toString()?.trim() ?: ""
        val task = binding.taskInput.text?.toString()?.trim() ?: ""
        val text = binding.textInput.text?.toString() ?: ""
        
        // Validate inputs
        if (practiceId.isEmpty() || task.isEmpty() || text.isEmpty()) {
            showError(getString(R.string.error_empty_fields))
            return
        }
        
        // Update API URL if changed
        updateApiUrl()
        
        // Show loading state
        setLoading(true)
        binding.resultText.text = getString(R.string.processing)
        
        lifecycleScope.launch {
            try {
                val response = client.generateSecureDoc(
                    practiceId = practiceId,
                    task = task,
                    text = text
                )
                
                setLoading(false)
                
                if (response.isSuccess) {
                    binding.resultText.text = response.outputText
                    binding.resultText.setTextColor(getColor(R.color.text_primary))
                } else {
                    binding.resultText.text = "Status: ${response.status}\n${response.outputText}"
                    binding.resultText.setTextColor(getColor(R.color.warning))
                }
                
            } catch (e: AnonymisatorException) {
                setLoading(false)
                showResult(getErrorMessage(e), isError = true)
            } catch (e: Exception) {
                setLoading(false)
                showResult("Unexpected error: ${e.message}", isError = true)
            }
        }
    }
    
    private fun clearFields() {
        binding.textInput.text?.clear()
        binding.resultText.text = ""
        binding.resultText.setTextColor(getColor(R.color.text_primary))
    }
    
    private fun setLoading(loading: Boolean) {
        binding.progressBar.visibility = if (loading) View.VISIBLE else View.GONE
        binding.submitButton.isEnabled = !loading
        binding.clearButton.isEnabled = !loading
    }
    
    private fun showError(message: String) {
        Toast.makeText(this, message, Toast.LENGTH_LONG).show()
    }
    
    private fun showResult(message: String, isError: Boolean = false) {
        binding.resultText.text = message
        binding.resultText.setTextColor(
            getColor(if (isError) R.color.error else R.color.text_primary)
        )
    }
    
    private fun getErrorMessage(exception: AnonymisatorException): String {
        return when (exception) {
            is AnonymisatorException.ValidationException -> 
                "Validation error: ${exception.message}"
            is AnonymisatorException.NetworkException -> 
                getString(R.string.error_network, exception.message)
            is AnonymisatorException.ApiException -> 
                getString(R.string.error_api, "HTTP ${exception.httpCode}: ${exception.apiMessage}")
            is AnonymisatorException.ParseException -> 
                "Parse error: ${exception.message}"
            is AnonymisatorException.InitializationException -> 
                "SDK error: ${exception.message}"
        }
    }
    
    private enum class StatusType {
        CONNECTED, ERROR, CHECKING
    }
    
    private fun setConnectionStatus(type: StatusType, message: String) {
        binding.statusText.text = message
        
        val color = when (type) {
            StatusType.CONNECTED -> getColor(R.color.success)
            StatusType.ERROR -> getColor(R.color.error)
            StatusType.CHECKING -> getColor(R.color.warning)
        }
        
        // Update status indicator color
        val drawable = binding.statusIndicator.background as? GradientDrawable
        drawable?.setColor(color)
    }
}
