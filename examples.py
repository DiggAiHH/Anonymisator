#!/usr/bin/env python3
"""
Comprehensive example demonstrating SecureDoc Flow usage.
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"
MCP_URL = "http://localhost:3000"


def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def example_securedoc_basic():
    """Example 1: Basic SecureDoc usage with PHI."""
    print_section("Example 1: Basic SecureDoc Document Generation")
    
    medical_text = """
    Patient Dr. Jane Smith, DOB 05/20/1975, presented on 2024-01-15 with symptoms.
    Contact: jane.smith@example.com
    Phone: (555) 987-6543
    MRN: ABC123456
    
    Chief Complaint: Persistent headaches for 2 weeks.
    
    History: Patient reports onset of headaches on 01/01/2024, gradually worsening.
    No previous similar episodes.
    """
    
    request_data = {
        "practice_id": "clinic_456",
        "task": "summarize",
        "text": medical_text
    }
    
    print("\nSending request to /v1/securedoc/generate...")
    print(f"Text length: {len(medical_text)} characters")
    print(f"Practice ID: {request_data['practice_id']}")
    print(f"Task: {request_data['task']}")
    
    response = requests.post(
        f"{BASE_URL}/v1/securedoc/generate",
        json=request_data
    )
    
    if response.status_code == 200:
        result = response.json()
        print("\n✓ Success!")
        print("\nGenerated Output:")
        print("-" * 80)
        print(result["output_text"])
        print("-" * 80)
    else:
        print(f"\n✗ Error: {response.status_code}")
        print(response.json())


def example_securedoc_extraction():
    """Example 2: Data extraction task."""
    print_section("Example 2: Data Extraction from Clinical Note")
    
    clinical_note = """
    Patient: Mr. Robert Johnson
    DOB: 12/03/1962
    Date of Visit: 2024-03-15
    
    Vitals:
    - BP: 140/90 mmHg
    - HR: 78 bpm
    - Temp: 98.6°F
    
    Medications:
    1. Lisinopril 10mg daily
    2. Metformin 500mg BID
    
    Assessment: Hypertension, well-controlled. Type 2 Diabetes Mellitus.
    
    Plan: Continue current medications. Follow-up in 3 months.
    Contact: rjohnson@email.com or (555) 234-5678
    """
    
    request_data = {
        "practice_id": "clinic_789",
        "task": "extract_key_information",
        "text": clinical_note
    }
    
    print("\nSending extraction request...")
    response = requests.post(
        f"{BASE_URL}/v1/securedoc/generate",
        json=request_data
    )
    
    if response.status_code == 200:
        result = response.json()
        print("\n✓ Success!")
        print("\nExtracted Information:")
        print("-" * 80)
        print(result["output_text"])
    else:
        print(f"\n✗ Error: {response.status_code}")


def example_validation_errors():
    """Example 3: Input validation."""
    print_section("Example 3: Input Validation Examples")
    
    # Test 1: Empty practice_id
    print("\nTest 1: Empty practice_id (should fail)")
    response = requests.post(
        f"{BASE_URL}/v1/securedoc/generate",
        json={"practice_id": "", "task": "test", "text": "Some text"}
    )
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print("✓ Correctly rejected")
    
    # Test 2: Text too long
    print("\nTest 2: Text exceeding size limit (should fail)")
    long_text = "a" * 50001
    response = requests.post(
        f"{BASE_URL}/v1/securedoc/generate",
        json={"practice_id": "test", "task": "test", "text": long_text}
    )
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print("✓ Correctly rejected")
    
    # Test 3: Valid at max size
    print("\nTest 3: Text at max size (50000 chars, should succeed)")
    max_text = "a" * 50000
    response = requests.post(
        f"{BASE_URL}/v1/securedoc/generate",
        json={"practice_id": "test", "task": "test", "text": max_text}
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✓ Correctly accepted")


def example_mcp_server():
    """Example 4: MCP Server usage."""
    print_section("Example 4: MCP Tool Server - Get Free Slots")
    
    print("\nFetching free slots for today...")
    response = requests.get(f"{MCP_URL}/tools/get_free_slots")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n✓ Success! Date: {result['date']}")
        print("\nAvailable Appointment Slots:")
        print("-" * 80)
        for slot in result["slots"]:
            print(f"  {slot['time']} - {slot['duration_minutes']} minutes")
    else:
        print(f"\n✗ Error: {response.status_code}")
    
    print("\n\nFetching free slots for specific date...")
    response = requests.get(
        f"{MCP_URL}/tools/get_free_slots",
        params={"date": "2025-12-26"}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Success! Date: {result['date']}")
        print(f"Number of slots: {len(result['slots'])}")


def example_health_checks():
    """Example 5: Health checks."""
    print_section("Example 5: Service Health Checks")
    
    print("\nChecking Backend Health...")
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        print(f"✓ Backend: {response.json()['status']}")
    
    print("\nChecking MCP Server Health...")
    response = requests.get(f"{MCP_URL}/health")
    if response.status_code == 200:
        data = response.json()
        print(f"✓ MCP Server: {data['status']} - {data['service']}")


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("SECUREDOC FLOW - COMPREHENSIVE EXAMPLES")
    print("=" * 80)
    print("\nEnsure both services are running:")
    print("  Backend: http://localhost:8000")
    print("  MCP Server: http://localhost:3000")
    print()
    
    try:
        # Check services are running
        requests.get(f"{BASE_URL}/health", timeout=2)
        requests.get(f"{MCP_URL}/health", timeout=2)
    except requests.exceptions.RequestException as e:
        print("✗ Error: Services are not running!")
        print("\nPlease start the services:")
        print("  Terminal 1: uvicorn backend.main:app --host 0.0.0.0 --port 8000")
        print("  Terminal 2: npm start")
        return
    
    # Run examples
    example_health_checks()
    example_securedoc_basic()
    example_securedoc_extraction()
    example_validation_errors()
    example_mcp_server()
    
    print("\n" + "=" * 80)
    print("ALL EXAMPLES COMPLETED")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()
