package com.admin.family.data.prefs

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

/**
 * Pure-JVM tests for the URL normalizer — no Android context required.
 * This runs on GitHub Actions Linux without Robolectric.
 */
class AppPreferencesNormalizeTest {

    @Test
    fun `accepts http urls`() {
        assertEquals(
            "http://example.com/",
            AppPreferences.normalize("http://example.com"),
        )
    }

    @Test
    fun `accepts https urls`() {
        assertEquals(
            "https://example.com/",
            AppPreferences.normalize("https://example.com"),
        )
    }

    @Test
    fun `adds trailing slash when missing`() {
        assertEquals(
            "http://10.0.2.2:8000/",
            AppPreferences.normalize("http://10.0.2.2:8000"),
        )
    }

    @Test
    fun `keeps existing trailing slash`() {
        assertEquals(
            "http://10.0.2.2:8000/",
            AppPreferences.normalize("http://10.0.2.2:8000/"),
        )
    }

    @Test
    fun `trims surrounding whitespace`() {
        assertEquals(
            "https://api.example.com/",
            AppPreferences.normalize("  https://api.example.com  "),
        )
    }

    @Test
    fun `rejects empty input`() {
        assertThrows(IllegalArgumentException::class.java) {
            AppPreferences.normalize("")
        }
    }

    @Test
    fun `rejects whitespace only`() {
        assertThrows(IllegalArgumentException::class.java) {
            AppPreferences.normalize("   ")
        }
    }

    @Test
    fun `rejects missing scheme`() {
        assertThrows(IllegalArgumentException::class.java) {
            AppPreferences.normalize("example.com")
        }
    }

    @Test
    fun `rejects ftp scheme`() {
        assertThrows(IllegalArgumentException::class.java) {
            AppPreferences.normalize("ftp://example.com")
        }
    }

    @Test
    fun `rejects javascript scheme`() {
        assertThrows(IllegalArgumentException::class.java) {
            AppPreferences.normalize("javascript:alert(1)")
        }
    }

    @Test
    fun `uppercase scheme is normalized lowercase for validation`() {
        // The require check lowercases only for validation; original case kept
        assertEquals(
            "HTTP://example.com/",
            AppPreferences.normalize("HTTP://example.com"),
        )
    }

    @Test
    fun `preserves path`() {
        assertEquals(
            "https://api.example.com/v1/",
            AppPreferences.normalize("https://api.example.com/v1"),
        )
    }

    @Test
    fun `default base url points to emulator loopback`() {
        assertEquals("http://10.0.2.2:8000/", AppPreferences.DEFAULT_BASE_URL)
    }
}
