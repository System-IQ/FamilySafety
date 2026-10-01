package com.admin.family.tsnet

import android.content.Context
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

@Serializable
data class TsnetProfile(
    val id: String,
    val name: String,
    val hostname: String,
    val authKey: String,
    val enabled: Boolean = true,
)

class TsnetProfileStore(context: Context) {
    private val prefs = context.getSharedPreferences("tsnet_profiles", Context.MODE_PRIVATE)
    private val json = Json { ignoreUnknownKeys = true; encodeDefaults = true; prettyPrint = true }

    fun list(): List<TsnetProfile> {
        val raw = prefs.getString(KEY, null) ?: return emptyList()
        return runCatching {
            json.decodeFromString<List<TsnetProfile>>(raw)
        }.getOrDefault(emptyList())
    }

    fun save(profiles: List<TsnetProfile>) {
        prefs.edit().putString(KEY, json.encodeToString(profiles)).apply()
    }

    fun upsert(profile: TsnetProfile) {
        val current = list().filterNot { it.id == profile.id }
        save(current + profile)
    }

    fun remove(id: String) {
        save(list().filterNot { it.id == id })
    }

    fun get(id: String): TsnetProfile? = list().firstOrNull { it.id == id }

    companion object { private const val KEY = "profiles" }
}
