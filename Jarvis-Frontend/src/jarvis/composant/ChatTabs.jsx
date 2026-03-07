import { useState } from "react";
import {  Send, Download, Trash2, ChevronDown, ChevronUp } from "lucide-react";

// ── Onglets ───────────────────────────────────────────────────────
export default function ChatTabs({ messages, input, setInput, handleSend, messagesEndRef, voiceLogs, deleteLog, downloadLog, toggleExpand }) {
  const [tab, setTab] = useState("chat");

  return (
    <>
      <div className="j-tabs">
        <button className={`j-tab ${tab==="chat"?"active":""}`} onClick={()=>setTab("chat")}>CONVERSATION</button>
        <button className={`j-tab ${tab==="logs"?"active":""}`} onClick={()=>setTab("logs")}>
          VOCAUX{voiceLogs.length > 0 ? ` (${voiceLogs.length})` : ""}
        </button>
      </div>

      {tab === "chat" ? (
        <>
          <div className="j-msgs">
            {messages.map((msg,i) => (
              <div key={i} className={`j-msg ${msg.sender}`}>
                <div className="j-msg-label">{msg.sender==="ai"?"JARVIS":"VOUS"}</div>
                {msg.text}
              </div>
            ))}
            <div ref={messagesEndRef}/>
          </div>
          <div className="j-input-row">
            <input className="j-input" type="text" value={input}
              onChange={e=>setInput(e.target.value)}
              onKeyDown={e=>e.key==="Enter"&&handleSend()}
              placeholder="Message…"
            />
            <button className="j-send" onClick={handleSend}><Send size={15}/></button>
          </div>
        </>
      ) : (
        <div className="j-logs">
          {voiceLogs.length === 0 ? (
            <div className="j-logs-empty">AUCUN ENREGISTREMENT<br/>Appuyez sur le micro<br/>pour commencer</div>
          ) : voiceLogs.map(log => (
            <div key={log.id} className="j-log">

              {/* En-tête */}
              <div className="j-log-head" onClick={()=>toggleExpand(log.id)}>
                <span className="j-log-icon">🎙</span>
                <span className="j-log-time">{log.label}</span>
                <div className="j-log-actions" onClick={e=>e.stopPropagation()}>
                  <button className="j-icon-btn" onClick={()=>downloadLog(log)} title="Télécharger"><Download size={13}/></button>
                  <button className="j-icon-btn del" onClick={()=>deleteLog(log.id)} title="Supprimer"><Trash2 size={13}/></button>
                  <button className="j-icon-btn" style={{color:"rgba(6,182,212,.35)"}}>
                    {log.expanded ? <ChevronUp size={13}/> : <ChevronDown size={13}/>}
                  </button>
                </div>
              </div>

              {/* Corps */}
              {log.expanded && (
                <div className="j-log-body">

                  {/* ── Lecteur audio natif avec key pour forcer le remount ── */}
                  <div>
                    <div className="j-log-section-label" style={{marginBottom:5}}>Lecture</div>
                    <audio
                      key={log.id + "-audio"}
                      className="j-audio"
                      controls
                      preload="metadata"
                    >
                      <source src={log.url} type={log.ext==="ogg"?"audio/ogg":"audio/webm"}/>
                      Votre navigateur ne supporte pas la lecture audio.
                    </audio>
                  </div>

                  {/* ── Transcription ── */}
                  <div>
                    <div className="j-log-section-label" style={{marginBottom:5}}>Transcription</div>
                    {log.text === "(aucune transcription)" ? (
                      <div className="j-log-text empty">
                        Aucune transcription — Speech API non disponible sur ce navigateur (utilisez Chrome ou Edge)
                      </div>
                    ) : (
                      <div className="j-log-text">« {log.text} »</div>
                    )}
                  </div>

                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </>
  );
}