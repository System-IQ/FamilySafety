package com.admin.family.python

import android.content.Context
import android.util.Log
import com.chaquo.python.PyObject
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File

/**
 * Kotlin bridge to embedded Python (Chaquopy).
 *
 * Lifecycle:
 *   1. init(context)          — starts Python runtime
 *   2. configure(filesDir)    — sets env vars (db path, secrets)
 *   3. startBackend()         — spawns uvicorn in a thread
 *   4. isBackendReady()       — poll until port 8000 accepts
 */
object PythonServer {

    private const val TAG = "PythonServer"
    private const val MODULE = "run_server"

    @Volatile private var initialized = false
    @Volatile private var configured = false
    @Volatile private var module: PyObject? = null

    // ── 1. Init runtime ──
    fun init(context: Context) {
        if (initialized) return
        synchronized(this) {
            if (initialized) return
            if (!Python.isStarted()) {
                Python.start(AndroidPlatform(context))
            }
            initialized = true
            Log.i(TAG, "Python runtime started")
        }
    }

    private fun getModule(): PyObject {
        module?.let { return it }
        synchronized(this) {
            module?.let { return it }
            val m = Python.getInstance().getModule(MODULE)
            module = m
            return m
        }
    }

    // ── 2. Configure paths ──
    fun configure(context: Context) {
        if (configured) return
        val filesDir: File = context.filesDir
        val cacheDir: File = context.cacheDir
        filesDir.mkdirs()
        cacheDir.mkdirs()

        val result = try {
            getModule().callAttr(
                "configure",
                filesDir.absolutePath,
                cacheDir.absolutePath,
            ).toString()
        } catch (t: Throwable) {
            Log.e(TAG, "configure failed", t)
            "error: ${t.message}"
        }
        configured = true
        Log.i(TAG, "configure -> $result")
    }

    // ── 3. Start backend ──
    suspend fun startBackend(): String = withContext(Dispatchers.IO) {
        try {
            getModule().callAttr("start_backend").toString()
        } catch (t: Throwable) {
            Log.e(TAG, "startBackend failed", t)
            "error: ${t.message}"
        }
    }

    // ── 4. Health check ──
    suspend fun isBackendReady(timeoutSec: Double = 15.0): Boolean =
        withContext(Dispatchers.IO) {
            try {
                getModule().callAttr("is_backend_ready", timeoutSec)
                    .toJava(Boolean::class.java)
            } catch (t: Throwable) {
                Log.e(TAG, "isBackendReady failed", t)
                false
            }
        }

    suspend fun status(): String = withContext(Dispatchers.IO) {
        try {
            getModule().callAttr("get_status").toString()
        } catch (t: Throwable) {
            "error: ${t.message}"
        }
    }

    suspend fun stopBackend(): String = withContext(Dispatchers.IO) {
        try {
            getModule().callAttr("stop_backend").toString()
        } catch (t: Throwable) {
            "error: ${t.message}"
        }
    }

    suspend fun hello(): String = withContext(Dispatchers.IO) {
        try {
            getModule().callAttr("hello").toString()
        } catch (t: Throwable) {
            "error: ${t.message}"
        }
    }
}
