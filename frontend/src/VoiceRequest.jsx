/**
 * VoiceRequest — Executive Voice & Task Input Component
 * Encodes audio as 16-bit PCM WAV (16 kHz mono) and posts to /transcribe.
 */

import { useEffect, useRef, useState } from "react";

const API_BASE = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"
).replace(/\/$/, "");

function writeString(view, offset, string) {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
}

function encodeWAV(samples, sampleRate) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  writeString(view, 0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(view, 8, "WAVE");

  writeString(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);

  writeString(view, 36, "data");
  view.setUint32(40, samples.length * 2, true);

  let offset = 44;
  for (let i = 0; i < samples.length; i++, offset += 2) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }

  return new Blob([view], { type: "audio/wav" });
}

export default function VoiceRequest({
  token,
  userId,
  onResult,
  context = {},
}) {
  const [transcript, setTranscript] = useState(
    "Summarize my meeting notes and prepare a follow-up email"
  );
  const [recording, setRecording] = useState(false);
  const [loading, setLoading] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("Ready for input");

  const audioContextRef = useRef(null);
  const streamRef = useRef(null);
  const processorRef = useRef(null);
  const samplesRef = useRef([]);

  useEffect(() => {
    return () => cleanupAudio();
  }, []);

  function cleanupAudio() {
    if (processorRef.current) {
      try {
        processorRef.current.disconnect();
      } catch {}
      processorRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (audioContextRef.current && audioContextRef.current.state !== "closed") {
      try {
        audioContextRef.current.close();
      } catch {}
      audioContextRef.current = null;
    }
  }

  async function startRecording() {
    setError("");
    setStatus("Accessing microphone…");
    samplesRef.current = [];

    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
    } catch (err) {
      const msg =
        err.name === "NotAllowedError" || err.name === "PermissionDeniedError"
          ? "Microphone access blocked. Click the lock/tune icon in the browser address bar to allow Microphone."
          : `Microphone error: ${err.message}`;
      setError(msg);
      setStatus("Microphone blocked");
      return;
    }

    streamRef.current = stream;

    try {
      const AudioContextClass =
        window.AudioContext || window.webkitAudioContext;
      const audioCtx = new AudioContextClass();
      audioContextRef.current = audioCtx;

      const source = audioCtx.createMediaStreamSource(stream);
      const processor = audioCtx.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        samplesRef.current.push(new Float32Array(inputData));
      };

      source.connect(processor);
      processor.connect(audioCtx.destination);

      setRecording(true);
      setStatus("🔴 Recording live audio… Click 'Stop & Transcribe' when finished");
    } catch (err) {
      cleanupAudio();
      setError(`Audio init failed: ${err.message}`);
      setStatus("Initialization error");
    }
  }

  async function stopRecording() {
    if (!recording) return;

    setStatus("Encoding audio…");
    setRecording(false);

    const sampleRate = audioContextRef.current?.sampleRate || 44100;
    cleanupAudio();

    const totalSamples = samplesRef.current.reduce((acc, c) => acc + c.length, 0);
    if (totalSamples === 0) {
      setStatus("No audio captured. Try speaking again.");
      return;
    }

    const merged = new Float32Array(totalSamples);
    let offset = 0;
    for (const chunk of samplesRef.current) {
      merged.set(chunk, offset);
      offset += chunk.length;
    }

    let targetSamples = merged;
    let targetRate = sampleRate;
    if (sampleRate !== 16000) {
      const ratio = sampleRate / 16000;
      const newLength = Math.round(merged.length / ratio);
      targetSamples = new Float32Array(newLength);
      for (let i = 0; i < newLength; i++) {
        const srcIndex = Math.min(Math.round(i * ratio), merged.length - 1);
        targetSamples[i] = merged[srcIndex];
      }
      targetRate = 16000;
    }

    const wavBlob = encodeWAV(targetSamples, targetRate);
    await sendAudioToServer(wavBlob);
  }

  async function sendAudioToServer(wavBlob) {
    const formData = new FormData();
    formData.append("file", wavBlob, "recording.wav");

    setTranscribing(true);
    setStatus("Transcribing audio on server…");

    try {
      const resp = await fetch(`${API_BASE}/transcribe`, {
        method: "POST",
        body: formData,
      });

      if (!resp.ok) {
        const detail = await resp.json().catch(() => ({}));
        throw new Error(detail?.detail || `Server error ${resp.status}`);
      }

      const { text } = await resp.json();
      if (text && text.trim()) {
        setTranscript(text.trim());
        setStatus("Transcription complete ✓");
      } else {
        setStatus("No clear speech detected. Please speak closer to the mic.");
      }
    } catch (err) {
      setError(`Transcription failed: ${err.message}`);
      setStatus("Transcription error");
    } finally {
      setTranscribing(false);
    }
  }

  async function submitRequest() {
    if (!transcript.trim()) {
      setError("Please provide a task request first.");
      return;
    }
    if (!token) {
      setError("Authentication token missing. Please select a user profile above.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE}/run-request`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          user_id: userId,
          request: transcript.trim(),
          context: context || {},
        }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        const detail =
          typeof data.detail === "string"
            ? data.detail
            : JSON.stringify(data.detail || data);
        throw new Error(detail || `Request failed (${response.status})`);
      }

      onResult?.(data);
    } catch (err) {
      setError(`${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  const busy = loading || transcribing || recording;

  return (
    <div className="voice-input-module">
      {/* Live Audio Status Bar */}
      <div className={`audio-status-banner ${recording ? "is-recording" : ""}`}>
        <div className="status-indicator-dot"></div>
        <span className="status-banner-text">{status}</span>
        {recording && <span className="recording-timer">LIVE REC</span>}
      </div>

      {/* Voice Control Buttons */}
      <div className="voice-button-row">
        {!recording ? (
          <button
            type="button"
            className="btn-mic-start"
            onClick={startRecording}
            disabled={busy}
          >
            🎤 Speak Command
          </button>
        ) : (
          <button
            type="button"
            className="btn-mic-stop"
            onClick={stopRecording}
            disabled={transcribing}
          >
            ⏹ Stop &amp; Transcribe
          </button>
        )}

        <button
          type="button"
          className="btn-preset-action"
          onClick={() =>
            setTranscript("Summarize my meeting notes and prepare a follow-up email")
          }
          disabled={busy}
          title="Fill standard executive prompt"
        >
          ⚡ Standard Workflow
        </button>

        <button
          type="button"
          className="btn-clear-text"
          onClick={() => {
            setTranscript("");
            setError("");
            setStatus("Ready for input");
          }}
          disabled={busy}
        >
          Clear
        </button>
      </div>

      {/* Prompt Input Area */}
      <div className="prompt-area-wrapper">
        <label htmlFor="speech-transcript" className="prompt-label">
          Instruction / Prompt Command:
        </label>
        <textarea
          id="speech-transcript"
          className="prompt-textarea"
          rows={3}
          value={transcript}
          onChange={(e) => setTranscript(e.target.value)}
          placeholder="e.g. Summarize my meeting notes and prepare a follow-up email"
        />
      </div>

      {/* Primary Submit Button */}
      <button
        type="button"
        className="btn-run-workflow"
        onClick={submitRequest}
        disabled={busy || !transcript.trim()}
      >
        {loading ? (
          <span className="btn-spinner-content">
            <span className="spinner-ring"></span> Executing Multi-Agent Pipeline…
          </span>
        ) : (
          <span>🚀 Run Automation Workflow</span>
        )}
      </button>

      {error && (
        <div className="dashboard-alert alert-error" style={{ marginTop: 12 }}>
          <span>Error:</span> {error}
        </div>
      )}
    </div>
  );
}
