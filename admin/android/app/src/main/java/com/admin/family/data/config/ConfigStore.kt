package com.admin.family.data.config

import android.content.Context
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import java.util.UUID

/**
 * A named configuration bundle. Users can create as many as they want
 * (e.g. "Home", "Work", "Trip") and switch between them with one tap.
 *
 * Fields:
 *   - id            — stable UUID
 *   - name          — user-visible label
 *   - backendUrl    — full URL to the FamilySafety backend
 *   - backendUrl    — HTTP endpoint of the embedded or remote backend
 *   - tunnelProvider— "cloudflare" | "ngrok" | null
 *   - tunnelUrl     — public URL produced by the tunnel (optional)
 *   - createdAt     — ms epoch
 *   - updatedAt     — ms epoch
 */
@Serializable
data class NamedConfig(
    val id: String,
    val name: String,
    val backendUrl: String,
    val controlToken: String? = null,
    val tunnelProvider: String? = null,
    val tunnelUrl: String? = null,
    val createdAt: Long = System.currentTimeMillis(),
    val updatedAt: Long = System.currentTimeMillis(),
) {
    fun withUpdatedNow(): NamedConfig = copy(updatedAt = System.currentTimeMillis())
}

/**
 * Persistent store for named configurations.
 *
 * Backed by SharedPreferences with a single JSON array. Safe for the
 * scale we need (tens of configs at most). Not for concurrent access
 * from multiple processes — but we only have one process.
 */
class ConfigStore(context: Context) {

    private val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    private val json = Json {
        ignoreUnknownKeys = true
        encodeDefaults = true
    }

    // ─────────────────────────────────────────────────────────────
    //  Read
    // ─────────────────────────────────────────────────────────────

    fun list(): List<NamedConfig> {
        val raw = prefs.getString(KEY_LIST, null) ?: return emptyList()
        return try {
            json.decodeFromString<List<NamedConfig>>(raw)
                .sortedByDescending { it.updatedAt }
        } catch (_: Exception) {
            emptyList()
        }
    }

    fun get(id: String): NamedConfig? = list().firstOrNull { it.id == id }

    fun count(): Int = list().size

    fun isEmpty(): Boolean = count() == 0

    fun activeId(): String? = prefs.getString(KEY_ACTIVE, null)

    fun active(): NamedConfig? {
        val id = activeId() ?: return null
        return get(id)
    }

    // ─────────────────────────────────────────────────────────────
    //  Write
    // ─────────────────────────────────────────────────────────────

    /** Insert or update. Also sets as active if it's the first config. */
    fun save(config: NamedConfig) {
        val current = list().toMutableList()
        val idx = current.indexOfFirst { it.id == config.id }
        val stamped = config.withUpdatedNow()
        if (idx >= 0) {
            current[idx] = stamped
        } else {
            current.add(stamped)
        }
        persist(current)

        // First config → auto-activate
        if (activeId() == null) {
            setActive(stamped.id)
        }
    }

    fun delete(id: String) {
        val current = list().filter { it.id != id }
        persist(current)
        // If we deleted the active one, pick the newest remaining
        if (activeId() == id) {
            val next = current.firstOrNull()
            if (next != null) {
                setActive(next.id)
            } else {
                prefs.edit().remove(KEY_ACTIVE).apply()
            }
        }
    }

    fun setActive(id: String) {
        val exists = list().any { it.id == id }
        if (exists) {
            prefs.edit().putString(KEY_ACTIVE, id).apply()
        }
    }

    /** Convenience: create a new config with sane defaults. */
    fun create(name: String, backendUrl: String): NamedConfig {
        val cfg = NamedConfig(
            id = UUID.randomUUID().toString(),
            name = name.trim().ifBlank { "Config ${count() + 1}" },
            backendUrl = backendUrl.trim(),
        )
        save(cfg)
        return cfg
    }

    fun clear() {
        prefs.edit().clear().apply()
    }

    // ─────────────────────────────────────────────────────────────
    //  Internal
    // ─────────────────────────────────────────────────────────────

    private fun persist(list: List<NamedConfig>) {
        val raw = try {
            json.encodeToString(list)
        } catch (_: Exception) {
            "[]"
        }
        prefs.edit().putString(KEY_LIST, raw).apply()
    }

    companion object {
        private const val PREFS_NAME = "family_configs"
        private const val KEY_LIST = "config_list_v1"
        private const val KEY_ACTIVE = "active_config_id"
    }
}
