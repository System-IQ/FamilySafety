package com.admin.family.ui.settings

import com.admin.family.data.api.ApiClient
import com.admin.family.data.repository.SettingsRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

/**
 * SettingsViewModel unit tests — pure JVM, no Android.
 *
 * We use a fake SettingsRepository and a fake ApiClient whose base URL
 * points to an unreachable host, so testConnection() must fail fast.
 *
 * This validates:
 * - URL validation logic
 * - State transitions (Idle -> Testing -> Failure)
 * - lastFailureAtMillis updating
 * - reset behavior
 */
@OptIn(ExperimentalCoroutinesApi::class)
class SettingsViewModelTest {

    private val dispatcher = StandardTestDispatcher()
    private lateinit var fakeRepo: FakeSettingsRepo
    private lateinit var apiClient: ApiClient

    @Before
    fun setUp() {
        Dispatchers.setMain(dispatcher)
        fakeRepo = FakeSettingsRepo(initialUrl = "http://10.0.2.2:8000/")
        // ApiClient reused here — but base URL is unreachable, so it
        // fails fast within test timeout.
        apiClient = ApiClient("http://127.0.0.1:1/") // port 1 = refused
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun `initial state reflects repository`() {
        val vm = SettingsViewModel(fakeRepo, apiClient, clock = { 1000L })
        val s = vm.state.value
        assertEquals("http://10.0.2.2:8000/", s.apiBaseUrlInput)
        assertEquals("http://10.0.2.2:8000/", s.savedApiBaseUrl)
        assertTrue(s.testResult is ConnectionTestResult.Idle)
    }

    @Test
    fun `valid input clears error`() {
        val vm = SettingsViewModel(fakeRepo, apiClient, clock = { 1000L })
        vm.onUrlInputChanged("https://api.example.com")
        assertNull(vm.state.value.urlError)
    }

    @Test
    fun `invalid input sets error on validate`() {
        val vm = SettingsViewModel(fakeRepo, apiClient, clock = { 1000L })
        vm.onUrlInputChanged("not a url")
        vm.validateInput()
        assertNotNull(vm.state.value.urlError)
    }

    @Test
    fun `save persists and normalizes`() {
        val vm = SettingsViewModel(fakeRepo, apiClient, clock = { 1000L })
        vm.onUrlInputChanged("https://api.example.com")
        vm.save()
        assertEquals("https://api.example.com/", fakeRepo.apiBaseUrl)
        assertEquals("https://api.example.com/", vm.state.value.savedApiBaseUrl)
        assertEquals("https://api.example.com/", vm.state.value.apiBaseUrlInput)
    }

    @Test
    fun `save with invalid url keeps previous saved url`() {
        val vm = SettingsViewModel(fakeRepo, apiClient, clock = { 1000L })
        vm.onUrlInputChanged("broken")
        vm.save()
        assertEquals("http://10.0.2.2:8000/", fakeRepo.apiBaseUrl)
    }

    @Test
    fun `reset restores default url`() {
        val vm = SettingsViewModel(fakeRepo, apiClient, clock = { 1000L })
        vm.onUrlInputChanged("https://api.example.com")
        vm.save()
        vm.resetToDefaults()
        assertEquals("http://10.0.2.2:8000/", vm.state.value.savedApiBaseUrl)
        assertEquals("http://10.0.2.2:8000/", fakeRepo.apiBaseUrl)
    }

    @Test
    fun `testConnection on unreachable host records failure`() = runTest {
        val vm = SettingsViewModel(fakeRepo, apiClient, clock = { 4242L })
        vm.onUrlInputChanged("http://127.0.0.1:1")
        vm.save()
        vm.testConnection()
        advanceUntilIdle()

        val s = vm.state.value
        assertTrue(
            "expected Failure, got ${s.testResult}",
            s.testResult is ConnectionTestResult.Failure,
        )
        assertEquals(4242L, s.lastFailureAtMillis)
        assertEquals(4242L, fakeRepo.lastTestFailureAtMillis)
        // Idle success never touched
        assertEquals(0L, fakeRepo.lastTestSuccessAtMillis)
    }

    @Test
    fun `testConnection with invalid url does not change state`() = runTest {
        val vm = SettingsViewModel(fakeRepo, apiClient, clock = { 1000L })
        vm.onUrlInputChanged("nope")
        vm.testConnection()
        advanceUntilIdle()
        assertTrue(vm.state.value.testResult is ConnectionTestResult.Idle)
    }
}

// ------------------------------------------------------------------
// Fake SettingsRepository — in-memory, no Android dependency
// ------------------------------------------------------------------

class FakeSettingsRepo(initialUrl: String) : SettingsRepository {
    private var url: String = initialUrl
    override val apiBaseUrl: String get() = url
    override fun saveBaseUrl(url: String) { this.url = url }
    override fun resetToDefaults() { this.url = "http://10.0.2.2:8000/" }

    private var _successAt = 0L
    private var _failureAt = 0L
    override val lastTestSuccessAtMillis: Long get() = _successAt
    override val lastTestFailureAtMillis: Long get() = _failureAt
    override fun recordTestSuccess(atMillis: Long) { _successAt = atMillis }
    override fun recordTestFailure(atMillis: Long) { _failureAt = atMillis }
}
