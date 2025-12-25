package com.anonymisator.sdk.model

import com.google.gson.annotations.SerializedName

/**
 * Represents an available appointment time slot.
 * Returned from the MCP server's get_free_slots endpoint.
 * 
 * @property time The time of the slot in HH:MM format
 * @property durationMinutes Duration of the appointment slot in minutes
 */
data class TimeSlot(
    @SerializedName("time")
    val time: String,
    
    @SerializedName("duration_minutes")
    val durationMinutes: Int
)

/**
 * Response from the /tools/get_free_slots endpoint.
 * Contains available appointment slots for a given date.
 * 
 * @property date The date for which slots are returned (YYYY-MM-DD format)
 * @property slots List of available time slots
 */
data class FreeSlotsResponse(
    @SerializedName("date")
    val date: String,
    
    @SerializedName("slots")
    val slots: List<TimeSlot>
)
