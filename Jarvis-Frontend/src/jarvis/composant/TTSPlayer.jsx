import { useRef, useEffect, useState } from "react";

export default function TTSPlayer() {
  const [status, setStatus] = useState("idle");
  const wsRef     = useRef(null);
  const audioRef  = useRef(null);

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws/tts/");
    ws.binaryType = "arraybuffer";
    wsRef.current = ws;

    ws.onmessage = (event) => {
      if (typeof event.data === "string") {
        const msg = JSON.parse(event.data);
        if (msg.type === "done") setStatus("idle");
        return;
      }

      // Un seul WAV complet → joue directement
      const blob  = new Blob([event.data], { type: "audio/wav" });
      const url   = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audioRef.current = audio;
      setStatus("playing");
      audio.onended = () => { URL.revokeObjectURL(url); setStatus("idle"); };
      audio.play();
    };

    ws.onclose = () => console.log("[TTS] fermé");
    ws.onerror = (e) => console.error("[TTS] erreur", e);

    return () => ws.close();
  }, []);

  const askJarvis = async () => {
    setStatus("loading");
    await fetch("http://localhost:8000/Jarvis/lire/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
  };

  const stop = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setStatus("idle");
  };

  return (
    <div style={{ padding: 12 }}>
      <span style={{ fontSize: 12, color: "#22d3ee" }}>
        🔊 {status === "playing" ? "▶️ lecture..." : status === "loading" ? "⏳ chargement..." : "en attente..."}
      </span>
      <br /><br />
      <button
        onClick={askJarvis}
        disabled={status === "loading" || status === "playing"}
        style={{ padding: "8px 20px", marginRight: 10 }}
      >
        🎙️ Jarvis parle
      </button>
      {(status === "playing" || status === "loading") && (
        <button onClick={stop}
          style={{ padding: "8px 16px", background: "#e74c3c", color: "white", border: "none", borderRadius: 4 }}>
          ⏹ Stop
        </button>
      )}
    </div>
  );
}