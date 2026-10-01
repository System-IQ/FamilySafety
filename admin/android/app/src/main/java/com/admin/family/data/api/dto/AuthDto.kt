package com.admin.family.data.api.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/**
 * Authentication DTOs for the guardian/admin flow.
 * (Separate from the AccessCode flow used by child devices.)
 */

@Serializable
data class LoginRequest(
    @SerialName("email") val email: String,
    @SerialName("password") val password: String,
)

@Serializable
data class TokenResponse(
    @SerialName("access_token") val accessToken: String,
    @SerialName("token_type") val tokenType: String = "Bearer",
    @SerialName("user") val user: UserPublic? = null,
)

@Serializable
data class UserPublic(
    @SerialName("id") val id: String,
    @SerialName("email") val email: String,
    @SerialName("display_name") val displayName: String? = null,
    @SerialName("role") val role: String = "guardian",
    @SerialName("created_at") val createdAt: String? = null,
)
