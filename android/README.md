# Anonymisator Android SDK

Android SDK and demo application for the SecureDoc Flow Privacy Proxy.

## Features

- **PHI-Protected Document Processing**: Send medical text to the backend for LLM processing with automatic PHI anonymization
- **Free Slots API**: Query available appointment slots (data-minimized, no patient info)
- **Modern Kotlin Architecture**: Coroutines, Retrofit, Clean Architecture
- **Secure by Default**: Input validation, no PHI logging, SSL support

## Quick Start

### Prerequisites

- Android Studio Hedgehog (2023.1.1) or newer
- JDK 17
- Android SDK 34
- Backend service running (see main README)

### Building the APK

1. Open the `android/` folder in Android Studio

2. Sync Gradle files

3. Build the APK:
   ```bash
   cd android
   ./gradlew assembleDebug
   ```

4. Find the APK at: `android/app/build/outputs/apk/debug/app-debug.apk`

### Installing on Device

**Option 1: Android Studio**
- Connect your device via USB
- Enable "Developer Options" and "USB Debugging" on your device
- Click "Run" in Android Studio

**Option 2: ADB**
```bash
adb install app/build/outputs/apk/debug/app-debug.apk
```

**Option 3: Direct Transfer**
- Copy the APK to your device
- Open it to install (enable "Install from unknown sources" if prompted)

## SDK Usage

### Initialization

```kotlin
// In your Application class or before first use
AnonymisatorClient.init(
    RetrofitClient.Config(
        backendBaseUrl = "https://your-backend.example.com",
        mcpBaseUrl = "https://your-mcp-server.example.com",
        timeoutSeconds = 60,
        enableLogging = BuildConfig.DEBUG
    )
)
```

### Processing Documents with PHI Protection

```kotlin
val client = AnonymisatorClient()

// Use coroutines (recommended)
lifecycleScope.launch {
    try {
        val response = client.generateSecureDoc(
            practiceId = "clinic_123",
            task = "summarize",
            text = "Patient Dr. John Smith, DOB 01/15/1980, presented with headache."
        )
        
        if (response.isSuccess) {
            println("Result: ${response.outputText}")
        }
    } catch (e: AnonymisatorException.ValidationException) {
        // Handle validation errors
    } catch (e: AnonymisatorException.NetworkException) {
        // Handle network errors
    } catch (e: AnonymisatorException.ApiException) {
        // Handle API errors (e.g., 400, 500)
    }
}
```

### Checking Service Health

```kotlin
lifecycleScope.launch {
    val health = client.checkHealth()
    if (health.isHealthy) {
        println("Service is operational")
    }
}
```

### Getting Free Appointment Slots

```kotlin
lifecycleScope.launch {
    val slots = client.getFreeSlots(date = "2025-12-26")
    slots.slots.forEach { slot ->
        println("${slot.time} - ${slot.durationMinutes} minutes")
    }
}
```

## Error Handling

The SDK provides typed exceptions for different error scenarios:

```kotlin
sealed class AnonymisatorException : Exception {
    class ValidationException   // Input validation failed
    class NetworkException      // Network/connectivity issues
    class ApiException          // HTTP error from API (4xx, 5xx)
    class ParseException        // Response parsing failed
    class InitializationException // SDK not initialized
}
```

## Project Structure

```
android/
├── app/
│   ├── src/main/
│   │   ├── java/com/anonymisator/sdk/
│   │   │   ├── AnonymisatorClient.kt    # Main SDK client
│   │   │   ├── AnonymisatorApp.kt       # Application class
│   │   │   ├── api/
│   │   │   │   ├── AnonymisatorApi.kt   # Retrofit interfaces
│   │   │   │   └── RetrofitClient.kt    # HTTP client config
│   │   │   ├── exception/
│   │   │   │   └── AnonymisatorException.kt
│   │   │   ├── model/
│   │   │   │   ├── SecureDocRequest.kt
│   │   │   │   ├── SecureDocResponse.kt
│   │   │   │   ├── FreeSlotsResponse.kt
│   │   │   │   └── HealthResponse.kt
│   │   │   └── ui/
│   │   │       └── MainActivity.kt      # Demo UI
│   │   ├── res/
│   │   │   ├── layout/activity_main.xml
│   │   │   ├── values/
│   │   │   └── xml/network_security_config.xml
│   │   └── AndroidManifest.xml
│   ├── build.gradle.kts
│   └── proguard-rules.pro
├── build.gradle.kts
├── settings.gradle.kts
├── gradle.properties
└── gradle/wrapper/
```

## Configuration

### Build Variants

- **Debug**: Logging enabled, no code minification
- **Release**: ProGuard minification, logging disabled

### Network Security

The app is configured with a network security config that:
- Allows cleartext traffic only for local development (10.0.2.2, localhost)
- Requires HTTPS for all other domains

For production, update `network_security_config.xml` to add your domain:

```xml
<domain-config cleartextTrafficPermitted="false">
    <domain includeSubdomains="true">your-domain.com</domain>
</domain-config>
```

### Emulator Connection

When running the backend locally, use `10.0.2.2` as the host (this maps to `localhost` on your development machine):

```
http://10.0.2.2:8000  → Backend Privacy Proxy
http://10.0.2.2:3000  → MCP Tool Server
```

## Dependencies

- **Retrofit 2.9.0**: HTTP client
- **OkHttp 4.12.0**: HTTP library
- **Gson 2.10.1**: JSON serialization
- **Kotlin Coroutines 1.7.3**: Async programming
- **AndroidX Lifecycle**: Lifecycle-aware components
- **Material Components**: UI components

## Security Considerations

1. **No PHI Logging**: HTTP logging is set to HEADERS level only (no body logging)
2. **Input Validation**: All inputs validated before API calls
3. **SSL/TLS**: Production should use HTTPS only
4. **ProGuard**: Release builds have code minification enabled

## Minimum Requirements

- Android 7.0 (API 24) or higher
- Internet connectivity

## License

See LICENSE file in the repository root.
