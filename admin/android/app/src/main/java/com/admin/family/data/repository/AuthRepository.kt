package com.admin.family.data.repository

import com.admin.family.data.api.ApiClient
import com.admin.family.data.api.dto.LoginRequest
import com.admin.family.data.auth.TokenStore

class AuthRepository(
    private val api: ApiClient,
    private val tokenStore: TokenStore,
) {
    suspend fun login(email: String, password: String): Result<Unit> = try {
        val tokens = api.login(LoginRequest(email = email, password = password))
        tokenStore.accessToken = tokens.accessToken
        tokenStore.refreshToken = tokens.refreshToken
        tokenStore.userEmail = email
        Result.success(Unit)
    } catch (t: Throwable) {
        Result.failure(t)
    }

    fun logout() {
        tokenStore.clear()
    }

    fun isLoggedIn(): Boolean = tokenStore.isLoggedIn()
    fun userEmail(): String? = tokenStore.userEmail
}
