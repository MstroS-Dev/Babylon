package com.babylon.site.util

import okhttp3.MediaType
import okhttp3.RequestBody
import okio.Buffer
import okio.BufferedSink
import okio.ForwardingSink
import okio.Sink
import okio.buffer

/**
 * Wraps a file RequestBody and reports when all of its bytes have actually
 * been handed to the network. A plain Retrofit call gives no signal
 * between "started sending" and "got a response" - for a photo upload
 * that's also being AI-reviewed server-side in the same request, that
 * hides a real, sometimes multi-second gap where the file is fully sent
 * but the server is still thinking. onUploadFinished lets the UI show
 * that as its own "checking your photo" step instead of one long,
 * unexplained wait.
 */
class CountingRequestBody(
    private val delegate: RequestBody,
    private val onUploadFinished: () -> Unit,
) : RequestBody() {

    override fun contentType(): MediaType? = delegate.contentType()
    override fun contentLength(): Long = delegate.contentLength()

    override fun writeTo(sink: BufferedSink) {
        val countingSink = object : ForwardingSink(sink) {
            private var bytesWritten = 0L
            private var finished = false
            override fun write(source: Buffer, byteCount: Long) {
                super.write(source, byteCount)
                bytesWritten += byteCount
                if (!finished && bytesWritten >= contentLength()) {
                    finished = true
                    onUploadFinished()
                }
            }
        }
        val bufferedSink = countingSink.buffer()
        delegate.writeTo(bufferedSink)
        bufferedSink.flush()
    }
}
