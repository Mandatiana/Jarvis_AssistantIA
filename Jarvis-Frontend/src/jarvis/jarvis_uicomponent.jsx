import React, { useState, useRef, useEffect, useCallback } from "react";
import { Mic, MicOff, Camera, MessageSquare, Send, X, Download, Trash2, ChevronDown, ChevronUp } from "lucide-react";
import ChatTabs from "./composant/ChatTabs";
import Orb3D from "./composant/Orb3D";
import AudioRecorder from 'audio-recorder-polyfill';

// ⚡ IMPORTANT: Installer le polyfill AVANT son utilisation
if (!window.MediaRecorder) {
  window.MediaRecorder = AudioRecorder;
}

// ⚡ Initialiser le polyfill avec les dépendances Web Audio
AudioRecorder.NotSupportedError = Error;
AudioRecorder.encoder = '/encoderWorker.js'; // ← À télécharger depuis npm package

export default function JarvisUI() {
  const [listening,  setListening]  = useState(true);
  const [chatOpen,   setChatOpen]   = useState(false);
  const [recording,  setRecording]  = useState(false);
  const [transcript, setTranscript] = useState("");
  const [voiceLogs,  setVoiceLogs]  = useState([]);
  const [recStatus,  setRecStatus]  = useState("idle");
  const [messages,   setMessages]   = useState([
    { sender: "ai",  text: "Bonjour, je suis JARVIS. Comment puis-je vous aider aujourd'hui ?" },
    { sender: "moi", text: "Bonjour …" },
  ]);
  const [input, setInput] = useState("");
  const [time,  setTime]  = useState(new Date());

  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);
  const mediaRecRef    = useRef(null);
  const audioChunksRef = useRef([]);
  const streamRef      = useRef(null);
  const finalTextRef   = useRef("");
  const socketRef = useRef(null);
  const sendQueueRef = useRef([]);
  const reconnectTimerRef = useRef(null);
  const recordingStartTimeRef = useRef(null);

  // ⚡ Utiliser WebM pour meilleure compatibilité (polyfill convertira en WAV)
  const AUDIO_MIME_TYPE = "audio/webm";
  const AUDIO_EXTENSION = "wav"; // On le serve comme WAV au backend

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => { return () => stopEverything(); }, []);

  const fmtTime  = d => d.toLocaleTimeString("fr-FR", { hour:"2-digit", minute:"2-digit", second:"2-digit" });
  const fmtDate  = d => d.toLocaleDateString("fr-FR", { weekday:"long", day:"numeric", month:"long" });
  const nowLabel = () => new Date().toLocaleTimeString("fr-FR", { hour:"2-digit", minute:"2-digit", second:"2-digit" });

  const stopEverything = () => {
    if (recognitionRef.current) { 
      try { recognitionRef.current.abort(); } 
      catch(_){} 
      recognitionRef.current = null; 
    }
    if (mediaRecRef.current?.state !== "inactive") { 
      try { mediaRecRef.current.stop(); } 
      catch(_){} 
    }
    if (streamRef.current) { 
      streamRef.current.getTracks().forEach(t => t.stop()); 
      streamRef.current = null; 
    }
  };

  // ⚡ WebSocket optimisé avec reconnexion progressive
  useEffect(() => {
    const url = "ws://localhost:8000/ws/chat/";
    let reconnectCount = 0;
    const maxReconnectDelay = 5000;
    
    function connect() {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        console.log("✅ WebSocket établie");
        reconnectCount = 0;
        
        // Flush queue
        while (sendQueueRef.current.length && ws.readyState === WebSocket.OPEN) {
          const p = sendQueueRef.current.shift();
          try {
            if (p instanceof ArrayBuffer) ws.send(p);
            else ws.send(JSON.stringify(p));
          } catch(_) { 
            sendQueueRef.current.unshift(p); 
            break; 
          }
        }
      };

      ws.onmessage = (event) => {
        try {
          const msg = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;
          
          if (msg.type === 'final_transcript') {
            setTranscript(msg.text || "");
            setInput(msg.text || "");
            setRecStatus("idle");
            addMsg("ai", `📝 Transcription reçue (${msg.audio_file})`);
            console.log("✅ Transcript final:", msg.text?.substring(0, 100));
          } 
          else if (msg.type === 'interim_transcript') {
            setTranscript(msg.text || "");
          } 
          else if (msg.type === 'transcript_timeout') {
            setRecStatus("idle");
            addMsg("ai", "⏱ Timeout: transcription non terminée");
          } 
          else if (msg.type === 'error') {
            addMsg("ai", `❌ Erreur: ${msg.message}`);
          }
        } catch (e) {
          console.error("Parse error:", e);
        }
      };

      ws.onerror = (e) => {
        console.error("❌ WebSocket error", e);
        try { ws.close(); } catch(_) {}
      };

      ws.onclose = () => {
        console.log("⚠️ WebSocket fermée, reconnexion...");
        const delay = Math.min(1000 * Math.pow(1.5, reconnectCount), maxReconnectDelay);
        reconnectCount++;
        
        if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = setTimeout(() => {
          if (!socketRef.current || socketRef.current.readyState === WebSocket.CLOSED) {
            connect();
          }
        }, delay);
      };

      socketRef.current = ws;
      return ws;
    }

    if (!socketRef.current) connect();

    return () => {
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      if (socketRef.current) {
        try { socketRef.current.close(); } catch(_) {}
        socketRef.current = null;
      }
    };
  }, []);

  const startRecording = useCallback(async () => {
    if (recording) return;
    
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });
      streamRef.current = stream;
    } catch(err) {
      setRecStatus("idle");
      addMsg("ai", `⚠️ Erreur microphone: ${err.message}`);
      console.error("Microphone access error:", err);
      return;
    }

    setRecording(true);
    setRecStatus("recording");
    setTranscript("");
    finalTextRef.current = "";
    audioChunksRef.current = [];
    recordingStartTimeRef.current = Date.now();

    try {
      console.log(`🎤 Démarrage enregistrement WebM (polyfill WAV)`);

      // ⚡ Utiliser WebM — le polyfill convertira en WAV si nécessaire
      const mr = new MediaRecorder(stream, { mimeType: AUDIO_MIME_TYPE });
      mediaRecRef.current = mr;

      // 📦 Accumule chunks localement
      mr.ondataavailable = (e) => {
        if (e.data?.size > 0) {
          audioChunksRef.current.push(e.data);
          console.log(`📦 Chunk audio reçu (${e.data.size} bytes, type: ${e.data.type})`);
        }
      };

      mr.onstop = async () => {
        setRecStatus("processing");
        console.log(`⏹️ Enregistrement arrêté, ${audioChunksRef.current.length} chunks`);
        
        const blob = new Blob(audioChunksRef.current, { type: AUDIO_MIME_TYPE });
        const url = URL.createObjectURL(blob);
        const duration = (Date.now() - recordingStartTimeRef.current) / 1000;

        try {
          // ⚡ Conversion directe en ArrayBuffer
          const ab = await blob.arrayBuffer();
          const filename = `recording_${Date.now()}.${AUDIO_EXTENSION}`;
          const header = JSON.stringify({ 
            type: 'full_recording', 
            filename,
            mimeType: blob.type 
          });
          const headerBytes = new TextEncoder().encode(header);
          
          // Construire le packet une seule fois
          const packet = new Uint8Array(4 + headerBytes.length + ab.byteLength);
          const dv = new DataView(packet.buffer);
          dv.setUint32(0, headerBytes.length, true);
          packet.set(headerBytes, 4);
          packet.set(new Uint8Array(ab), 4 + headerBytes.length);

          const payload = packet.buffer;
          
          // Envoyer immédiatement
          if (socketRef.current?.readyState === WebSocket.OPEN) {
            socketRef.current.send(payload);
            console.log(`📤 Enregistrement envoyé (${(payload.byteLength / 1024).toFixed(1)} KB, ${duration.toFixed(1)}s)`);
          } else {
            sendQueueRef.current.push(payload);
            console.log(`📋 Enregistrement en queue (${(payload.byteLength / 1024).toFixed(1)} KB)`);
          }
        } catch (err) {
          console.error("❌ Erreur envoi:", err);
          setRecStatus("idle");
          addMsg("ai", `❌ Erreur envoi: ${err.message}`);
        }

        // 📝 Logger localement immédiatement
        const capturedText = finalTextRef.current.trim() || "(aucune transcription)";
        setVoiceLogs(prev => [{
          id: Date.now(),
          label: nowLabel(),
          url,
          ext: AUDIO_EXTENSION,
          text: capturedText,
          expanded: true,
          duration: duration.toFixed(1)
        }, ...prev]);

        stream.getTracks().forEach(t => t.stop());
        streamRef.current = null;
      };

      mr.onerror = (e) => {
        console.error("❌ MediaRecorder error:", e.error);
        setRecStatus("idle");
        addMsg("ai", `❌ Erreur enregistrement: ${e.error}`);
        
        // Fallback: arrêter le stream
        stream.getTracks().forEach(t => t.stop());
        streamRef.current = null;
      };

      // ⚡ Commencer l'enregistrement avec timeslice
      mr.start(1000);

    } catch (err) {
      console.error("❌ Erreur initialisation MediaRecorder:", err);
      setRecStatus("idle");
      addMsg("ai", `❌ Erreur: ${err.message}`);
      stream.getTracks().forEach(t => t.stop());
      streamRef.current = null;
      setRecording(false);
      return;
    }

    // 🎤 Speech Recognition activée en parallèle (non bloquant)
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SR) {
      const recog = new SR();
      recog.lang = "fr-FR";
      recog.continuous = true;
      recog.interimResults = true;

      recog.onresult = e => {
        let interim = "";
        for (let i = e.resultIndex; i < e.results.length; i++) {
          const t = e.results[i][0].transcript;
          if (e.results[i].isFinal) {
            finalTextRef.current += t + " ";
          } else {
            interim = t;
          }
        }
        setTranscript((finalTextRef.current + interim).trim());
        setInput(finalTextRef.current.trim());
      };

      recog.onerror = (e) => {
        console.warn("🔇 Speech Recognition error:", e.error);
      };

      recog.onend = () => {
        if (mediaRecRef.current?.state === "recording") {
          try { recog.start(); } catch(_) {}
        }
      };

      try { 
        recog.start(); 
        console.log("🎤 Speech Recognition démarrée");
      } catch(err) {
        console.warn("⚠️ Speech Recognition erreur:", err);
      }
      recognitionRef.current = recog;
    }
  }, [recording]);

  const stopRecording = useCallback(() => {
    if (!recording) return;
    
    console.log("⏹️ Arrêt enregistrement demandé");
    setRecording(false);
    
    if (recognitionRef.current) { 
      try { recognitionRef.current.abort(); } 
      catch(_){} 
      recognitionRef.current = null; 
    }
    
    if (mediaRecRef.current && mediaRecRef.current.state !== "inactive") {
      try {
        mediaRecRef.current.stop();
      } catch(err) {
        console.error("❌ Erreur stop MediaRecorder:", err);
        setRecStatus("idle");
      }
    } else {
      console.warn("⚠️ MediaRecorder pas actif ou null");
      setRecStatus("idle");
    }
  }, [recording]);

  const toggleMic = useCallback(() => {
    if (!recording) startRecording();
    else stopRecording();
  }, [recording, startRecording, stopRecording]);

  const toggleChat = () => setChatOpen(v => !v);
  const addMsg = (sender, text) => setMessages(prev => [...prev, { sender, text }]);

  const handleSend = () => {
    const txt = input.trim();
    if (!txt) return;
    addMsg("moi", txt);
    setInput("");
    setTranscript("");
    finalTextRef.current = "";
  };

  const deleteLog  = id => setVoiceLogs(prev => {
    const log = prev.find(x => x.id === id);
    if (log) URL.revokeObjectURL(log.url);
    return prev.filter(x => x.id !== id);
  });
  
  const toggleExpand = id => setVoiceLogs(prev => 
    prev.map(l => l.id === id ? {...l, expanded: !l.expanded} : l)
  );
  
  const downloadLog = log => {
    const a = document.createElement("a");
    a.href = log.url;
    a.download = `jarvis_${log.label.replace(/:/g, "-")}.${log.ext}`;
    a.click();
  };

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;900&family=Rajdhani:wght@300;400;500&display=swap');
        *,*::before,*::after{margin:0;padding:0;box-sizing:border-box}

        .j-root{width:100vw;height:100vh;overflow:hidden;background:#000;font-family:'Rajdhani',sans-serif;position:relative;display:flex}

        .j-grid{position:absolute;inset:0;pointer-events:none;background-image:linear-gradient(rgba(6,182,212,.04) 1px,transparent 1px),linear-gradient(90deg,rgba(6,182,212,.04) 1px,transparent 1px);background-size:60px 60px;animation:gridMove 20s linear infinite}
        @keyframes gridMove{to{transform:translate(60px,60px)}}
        .j-glow{position:absolute;inset:0;pointer-events:none;background:radial-gradient(ellipse 80% 60% at 30% 50%,rgba(6,182,212,.07) 0%,transparent 70%)}
        .j-scan{position:absolute;inset:0;pointer-events:none;background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(6,182,212,.007) 2px,rgba(6,182,212,.007) 4px)}

        .j-left{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;position:relative;z-index:1;padding:20px}
        .j-corner{position:absolute;width:18px;height:18px;border-color:rgba(6,182,212,.35);border-style:solid}
        .j-corner.tl{top:12px;left:12px;border-width:1px 0 0 1px}
        .j-corner.tr{top:12px;right:12px;border-width:1px 1px 0 0}
        .j-corner.bl{bottom:12px;left:12px;border-width:0 0 1px 1px}
        .j-corner.br{bottom:12px;right:12px;border-width:0 1px 1px 0}

        .j-status{position:absolute;top:18px;left:20px;right:20px;display:flex;justify-content:space-between;align-items:center}
        .j-online{display:flex;align-items:center;gap:7px;font-family:'Orbitron',monospace;font-size:9px;color:#22d3ee;letter-spacing:.15em}
        .j-dot{width:7px;height:7px;border-radius:50%;background:#22d3ee;box-shadow:0 0 8px #22d3ee;animation:dotP 1.5s ease-in-out infinite}
        @keyframes dotP{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.35;transform:scale(.65)}}
        .j-clock{font-family:'Orbitron',monospace;font-size:clamp(9px,1.1vw,13px);color:rgba(6,182,212,.55);letter-spacing:.08em;text-align:right}
        .j-clock small{font-size:.82em;opacity:.65;display:block;margin-top:2px}

        .j-core-wrap{position:relative;display:flex;align-items:center;justify-content:center;width:clamp(240px,38vw,400px);height:clamp(240px,38vw,400px)}
        .j-orbit{position:absolute;border-radius:50%;border:1px solid}
        .j-orbit::after{content:'';position:absolute;width:6px;height:6px;border-radius:50%;background:#22d3ee;box-shadow:0 0 10px #22d3ee;top:-3px;left:50%;transform:translateX(-50%)}
        .j-o1{width:100%;height:100%;border-color:rgba(6,182,212,.11);animation:cw 30s linear infinite}
        .j-o2{width:74%;height:74%;border-color:rgba(6,182,212,.2);animation:ccw 20s linear infinite}
        .j-o3{width:53%;height:53%;border-color:rgba(6,182,212,.33);animation:cw 12s linear infinite}
        @keyframes cw{to{transform:rotate(360deg)}}
        @keyframes ccw{to{transform:rotate(-360deg)}}
        .j-core{width:36%;height:36%;border-radius:50%;background:radial-gradient(circle at 35% 35%,rgba(6,182,212,.38),rgba(6,182,212,.07) 60%,transparent);border:1px solid rgba(6,182,212,.5);display:flex;align-items:center;justify-content:center;box-shadow:0 0 60px rgba(6,182,212,.22),0 0 120px rgba(6,182,212,.09),inset 0 0 28px rgba(6,182,212,.09);position:relative;z-index:2}
        .j-core-sym{font-family:'Orbitron',monospace;font-size:clamp(18px,2.8vw,30px);color:#22d3ee;text-shadow:0 0 18px #22d3ee,0 0 36px rgba(6,182,212,.5);animation:symP 2s ease-in-out infinite}
        @keyframes symP{0%,100%{opacity:1;text-shadow:0 0 18px #22d3ee,0 0 36px rgba(6,182,212,.5)}50%{opacity:.55;text-shadow:0 0 8px #22d3ee}}
        .j-listen-ring{position:absolute;inset:-12%;border-radius:50%;border:2px solid rgba(6,182,212,.6);animation:lRing 1s ease-out infinite}
        @keyframes lRing{0%{transform:scale(1);opacity:.8}100%{transform:scale(1.45);opacity:0}}
        .j-rec-ring{position:absolute;inset:-18%;border-radius:50%;border:2px solid rgba(239,68,68,.7);animation:rRing .8s ease-out infinite}
        @keyframes rRing{0%{transform:scale(1);opacity:.9}100%{transform:scale(1.5);opacity:0}}

        .j-title{margin-top:clamp(18px,3.5vh,36px);font-family:'Orbitron',monospace;font-weight:900;font-size:clamp(20px,3.2vw,42px);letter-spacing:clamp(.3em,1.4vw,.65em);color:#22d3ee;text-shadow:0 0 28px rgba(6,182,212,.5);text-align:center}
        .j-subtitle{font-size:clamp(9px,1.1vw,12px);letter-spacing:.28em;color:rgba(6,182,212,.4);text-transform:uppercase;margin-top:5px;text-align:center}

        .j-live-transcript{margin-top:10px;max-width:65%;text-align:center;font-size:clamp(11px,1vw,13px);color:rgba(6,182,212,.75);line-height:1.5;font-style:italic}

        .j-badge{display:inline-flex;align-items:center;gap:6px;font-family:'Orbitron',monospace;font-size:9px;letter-spacing:.12em;padding:4px 10px;border-radius:20px;margin-top:8px}
        .j-badge.rec{color:#ef4444;border:1px solid rgba(239,68,68,.4);background:rgba(239,68,68,.08)}
        .j-badge.rec .j-bd{background:#ef4444;box-shadow:0 0 6px #ef4444;animation:dotP .7s ease-in-out infinite}
        .j-badge.proc{color:#f59e0b;border:1px solid rgba(245,158,11,.4);background:rgba(245,158,11,.08)}
        .j-badge.proc .j-bd{background:#f59e0b}
        .j-bd{width:6px;height:6px;border-radius:50%}

        .j-controls{position:absolute;bottom:clamp(14px,2.8vh,28px);left:50%;transform:translateX(-50%);display:flex;gap:clamp(8px,1.8vw,18px);align-items:center}
        .j-btn{border-radius:13px;background:rgba(6,182,212,.06);border:1px solid rgba(6,182,212,.2);display:flex;align-items:center;justify-content:center;cursor:pointer;transition:all .2s;color:#22d3ee;width:clamp(42px,4.8vw,54px);height:clamp(42px,4.8vw,54px)}
        .j-btn:hover{background:rgba(6,182,212,.16);border-color:rgba(6,182,212,.45);box-shadow:0 0 18px rgba(6,182,212,.18)}
        .j-btn.on{background:rgba(6,182,212,.22);border-color:#22d3ee;box-shadow:0 0 28px rgba(6,182,212,.38)}
        .j-btn.rec{background:rgba(239,68,68,.18);border-color:#ef4444;box-shadow:0 0 28px rgba(239,68,68,.3);color:#ef4444}

        .j-chat{width:clamp(300px,32vw,440px);height:100vh;display:flex;flex-direction:column;border-left:1px solid rgba(6,182,212,.14);background:rgba(0,8,16,.9);backdrop-filter:blur(18px);position:relative;z-index:2;overflow:hidden;transition:width .35s cubic-bezier(.4,0,.2,1),opacity .3s,border-left-color .3s}
        .j-chat.closed{width:0;opacity:0;pointer-events:none;border-left-color:transparent}
        .j-chat-header{padding:clamp(13px,1.8vh,20px) clamp(14px,1.6vw,22px);border-bottom:1px solid rgba(6,182,212,.11);display:flex;align-items:center;justify-content:space-between;flex-shrink:0;white-space:nowrap}
        .j-chat-title{font-family:'Orbitron',monospace;font-size:clamp(11px,1vw,14px);color:#22d3ee;letter-spacing:.14em}
        .j-chat-close{background:none;border:none;cursor:pointer;color:rgba(6,182,212,.4);transition:color .2s;display:flex}
        .j-chat-close:hover{color:#22d3ee}

        .j-tabs{display:flex;border-bottom:1px solid rgba(6,182,212,.11);flex-shrink:0}
        .j-tab{flex:1;padding:9px;text-align:center;cursor:pointer;font-family:'Orbitron',monospace;font-size:9px;letter-spacing:.12em;color:rgba(6,182,212,.4);border:none;background:none;transition:all .2s;border-bottom:2px solid transparent}
        .j-tab.active{color:#22d3ee;border-bottom-color:#22d3ee;background:rgba(6,182,212,.05)}

        .j-msgs{flex:1;overflow-y:auto;padding:clamp(10px,1.8vh,18px) clamp(12px,1.3vw,18px);display:flex;flex-direction:column;gap:clamp(7px,1.1vh,12px);scrollbar-width:thin;scrollbar-color:rgba(6,182,212,.18) transparent}
        .j-msg{padding:clamp(9px,1.1vh,13px) clamp(11px,1.1vw,15px);border-radius:11px;line-height:1.5;font-size:clamp(12px,1vw,14px);max-width:90%;word-break:break-word}
        .j-msg.ai{align-self:flex-start;background:rgba(6,182,212,.06);border:1px solid rgba(6,182,212,.14);color:#cbd5e1}
        .j-msg.moi{align-self:flex-end;background:rgba(37,99,235,.22);border:1px solid rgba(59,130,246,.22);color:#e2e8f0}

        .j-logs{flex:1;overflow-y:auto;padding:10px 10px 20px;display:flex;flex-direction:column;gap:8px;scrollbar-width:thin;scrollbar-color:rgba(6,182,212,.18) transparent}
        .j-log{background:rgba(6,182,212,.04);border:1px solid rgba(6,182,212,.13);border-radius:10px;overflow:hidden;transition:border-color .2s}
        .j-log:hover{border-color:rgba(6,182,212,.28)}

        .j-log-head{display:flex;align-items:center;gap:8px;padding:10px 12px;cursor:pointer;user-select:none}
        .j-log-icon{font-size:13px;flex-shrink:0}
        .j-log-time{font-family:'Orbitron',monospace;font-size:9px;color:rgba(6,182,212,.6);letter-spacing:.1em;flex:1}
        .j-log-actions{display:flex;align-items:center;gap:2px}
        .j-icon-btn{background:none;border:none;cursor:pointer;color:rgba(6,182,212,.4);transition:all .2s;padding:5px;display:flex;border-radius:7px}
        .j-icon-btn:hover{color:#22d3ee;background:rgba(6,182,212,.1)}
        .j-icon-btn.del:hover{color:#ef4444;background:rgba(239,68,68,.1)}

        .j-log-body{padding:0 12px 12px;display:flex;flex-direction:column;gap:8px}

        .j-audio{
          width:100%;
          height:36px;
          border-radius:8px;
          outline:none;
          background:rgba(6,182,212,.06);
          border:1px solid rgba(6,182,212,.15);
          accent-color:#22d3ee;
        }

        .j-log-section-label{font-family:'Orbitron',monospace;font-size:8px;letter-spacing:.12em;color:rgba(6,182,212,.35);text-transform:uppercase}
        .j-log-text{font-size:12px;color:rgba(203,213,225,.75);line-height:1.55;font-style:italic;background:rgba(6,182,212,.04);border:1px solid rgba(6,182,212,.1);border-radius:8px;padding:8px 10px}
        .j-log-text.empty{color:rgba(6,182,212,.25);font-style:normal;font-size:11px}

        .j-logs-empty{text-align:center;color:rgba(6,182,212,.22);font-family:'Orbitron',monospace;font-size:10px;letter-spacing:.12em;margin-top:40px;line-height:2.2}

        .j-input-row{padding:clamp(10px,1.4vh,16px) clamp(12px,1.3vw,16px);border-top:1px solid rgba(6,182,212,.11);display:flex;gap:9px;align-items:center;flex-shrink:0}
        .j-input{flex:1;background:rgba(6,182,212,.05);border:1px solid rgba(6,182,212,.18);border-radius:11px;padding:clamp(7px,.9vh,10px) clamp(11px,1.1vw,14px);color:#e2e8f0;font-family:'Rajdhani',sans-serif;font-size:clamp(13px,1vw,15px);outline:none;transition:border-color .2s,box-shadow .2s}
        .j-input:focus{border-color:rgba(6,182,212,.45);box-shadow:0 0 12px rgba(6,182,212,.09)}
        .j-input::placeholder{color:rgba(6,182,212,.28)}
        .j-send{width:clamp(36px,3.2vw,44px);height:clamp(36px,3.2vw,44px);border-radius:10px;flex-shrink:0;cursor:pointer;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,rgba(6,182,212,.48),rgba(6,182,212,.28));border:1px solid rgba(6,182,212,.38);color:#000;transition:all .2s}
        .j-send:hover{background:linear-gradient(135deg,#22d3ee,rgba(6,182,212,.65));box-shadow:0 0 18px rgba(6,182,212,.28)}
        
        .j-core-wrap{
          width: clamp(340px, 50vw, 650px);
          aspect-ratio: 1 / 1; /* TRÈS IMPORTANT */
        }
        .j-core-wrap{
          transform: translateY(-40px); /* monte l’orb */
        }
        }
        @media(max-width:768px){
          .j-root{flex-direction:column}
          .j-left{flex:1;min-height:0}
          .j-chat{width:100%;height:52vh;border-left:none;border-top:1px solid rgba(6,182,212,.14);transition:height .35s cubic-bezier(.4,0,.2,1),opacity .3s}
          .j-chat.closed{width:100%;height:0;opacity:0;border-top-color:transparent}
        }
      `}</style>

      <div className="j-root">
        <div className="j-grid"/><div className="j-glow"/><div className="j-scan"/>

        <div className="j-left">
          <div className="j-corner tl"/><div className="j-corner tr"/>
          <div className="j-corner bl"/><div className="j-corner br"/>

          <div className="j-status">
            <div className="j-online"><div className="j-dot"/>SYSTÈME EN LIGNE</div>
            <div className="j-clock">{fmtTime(time)}<small>{fmtDate(time)}</small></div>
          </div>

          <div className="j-core-wrap">
            <Orb3D />
          </div>

          <div className="j-title">J.A.R.V.I.S</div>
          <div className="j-subtitle">Intelligence artificielle avancée</div>

          {recStatus === "recording"  && <div className="j-badge rec"><span className="j-bd"/>ENREGISTREMENT EN COURS</div>}
          {recStatus === "processing" && <div className="j-badge proc"><span className="j-bd"/>TRAITEMENT…</div>}
          {transcript && <div className="j-live-transcript">« {transcript} »</div>}

          <div className="j-controls">
            <button className="j-btn" title="Caméra"><Camera size={17}/></button>
            <button
              className={`j-btn ${recording ? "rec" : listening ? "on" : ""}`}
              onClick={toggleMic}
              title={recording ? "Arrêter l'enregistrement" : "Démarrer l'enregistrement"}
            >
              {recording ? <MicOff size={17}/> : <Mic size={17}/>}
            </button>
            <button className={`j-btn ${chatOpen?"on":""}`} onClick={toggleChat} title="Conversation">
              <MessageSquare size={17}/>
            </button>
          </div>
        </div>

        <div className={`j-chat ${chatOpen?"":"closed"}`}>
          <div className="j-chat-header">
            <div className="j-chat-title">◈ JARVIS INTERFACE</div>
            <button className="j-chat-close" onClick={toggleChat}><X size={15}/></button>
          </div>
          <ChatTabs
            messages={messages} input={input} setInput={setInput}
            handleSend={handleSend} messagesEndRef={messagesEndRef}
            voiceLogs={voiceLogs} deleteLog={deleteLog}
            downloadLog={downloadLog} toggleExpand={toggleExpand}
          />
        </div>
      </div>
    </>
  );
}
