import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";

export default function Orb3D() {
  const canvasRef  = useRef();
  const uniformsRef = useRef(null);

  // TTS state
  const wsRef      = useRef(null);
  const audioRef   = useRef(null);
  const queueRef   = useRef([]);
  const playingRef = useRef(false);
  const doneRef    = useRef(false);
  const [ttsStatus, setTtsStatus] = useState("idle"); // idle | loading | playing

  // Orb scale ref — modifié pendant la lecture audio
  const orbScaleRef    = useRef(1.0);
  const targetScaleRef = useRef(1.0);

  //TTS WebSocket 
  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws/tts/");
    ws.binaryType = "arraybuffer";
    wsRef.current = ws;

    ws.onmessage = (event) => {
      if (typeof event.data === "string") {
        const msg = JSON.parse(event.data);
        if (msg.type === "done") {
          doneRef.current = true;
          if (!playingRef.current && queueRef.current.length === 0) {
            setTtsStatus("idle");
            targetScaleRef.current = 1.0; // retour taille normale
          }
        }
        return;
      }

      // Phrase audio reçue
      const blob = new Blob([event.data], { type: "audio/wav" });
      queueRef.current.push(blob);
      if (!playingRef.current) playNext();
    };

    ws.onclose = () => {
      setTimeout(() => {
        const ws2 = new WebSocket("ws://localhost:8000/ws/tts/");
        ws2.binaryType = "arraybuffer";
        wsRef.current = ws2;
      }, 2000);
    };

    ws.onerror = (e) => console.error("[TTS] erreur", e);

    // Appel unique au montage
    ws.onopen = async () => {
      try {
        // Vérifie d'abord si ia.txt a du contenu
        const check = await fetch("http://localhost:8000/Jarvis/verifier/");
        const data  = await check.json();
    
        if (!data.has_content) {
          console.log("[TTS] ia.txt vide — rien à jouer");
          return; // sort immédiatement sans rien faire
        }
    
        // Contenu présent → lance le TTS immédiatement
        setTtsStatus("loading");
        await fetch("http://localhost:8000/Jarvis/lire/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        });
      } catch (e) {
        console.error("[TTS] erreur", e);
      }
    };
    return () => {
      ws.close();
    };
  }, []);

  const playNext = () => {
    if (playingRef.current) return;
    if (queueRef.current.length === 0) {
      if (doneRef.current) {
        setTtsStatus("idle");
        targetScaleRef.current = 1.0;
      }
      return;
    }

    playingRef.current = true;
    setTtsStatus("playing");
    targetScaleRef.current = 1.18; // orb grandit pendant lecture

    const blob  = queueRef.current.shift();
    const url   = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audioRef.current = audio;

    audio.onended = async () => {
      URL.revokeObjectURL(url);
      playingRef.current = false;
      audioRef.current = null;
    
      //  si plus rien en queue → fin totale
      if (queueRef.current.length === 0) {
        targetScaleRef.current = 1.0;
    
        try {
          await fetch("http://localhost:8000/Jarvis/vider/", {
            method: "POST"
          });
          console.log("[IA] fichier vidé");
        } catch (e) {
          console.error("[IA] erreur vidage", e);
        }
      }
    
      playNext();
    };

    audio.onerror = () => {
      URL.revokeObjectURL(url);
      playingRef.current = false;
      playNext();
    };

    audio.play().catch(() => {
      playingRef.current = false;
      playNext();
    });
  };

  useEffect(() => {

    const interval = setInterval(async () => {
  
      //  si déjà en train de lire → skip
      if (ttsStatus === "playing" || ttsStatus === "loading") return;
  
      try {
        const res = await fetch("http://localhost:8000/Jarvis/verifier/");
        const data = await res.json();
  
        if (!data.has_content) return;
  
        console.log("[IA] contenu détecté");
  
        //  lancer TTS
        setTtsStatus("loading");
  
        await fetch("http://localhost:8000/Jarvis/lire/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        });
  
      } catch (e) {
        console.error("[Loop IA]", e);
      }
  
    }, 1500); // toutes les 1.5 secondes
  
    return () => clearInterval(interval);
  
  }, [ttsStatus]);
  
  //  Three.js Orb 
  useEffect(() => {
    const canvas = canvasRef.current;
    const width = canvas.clientWidth;
   const height = canvas.clientHeight;


    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(width, height, false);
    renderer.setClearColor(0x000000, 0);

    const scene  = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(38, window.innerWidth / window.innerHeight, 0.5, 180);
    camera.position.z = 3.2;

    const lumiereAmbiante  = new THREE.AmbientLight(0x102040, 0.8);
    scene.add(lumiereAmbiante);
    const lumiereBleu      = new THREE.PointLight(0x00f2ff, 3, 20);
    lumiereBleu.position.set(5, 5, 5);
    scene.add(lumiereBleu);
    const lumiereViolette  = new THREE.PointLight(0x7000ff, 2, 15);
    lumiereViolette.position.set(-5, -3, 2);
    scene.add(lumiereViolette);

    const uniforms = {
      uTime:           { value: 0 },
      uAmp:            { value: 0.09 },
      uColorBase:      { value: new THREE.Color("#1e4bb3") },
      uColorInternal:  { value: new THREE.Color("#1e4bb3") },
      uColorHighlight: { value: new THREE.Color("#99f3ff") }
    };
    uniformsRef.current = uniforms;

    const vertexShader = `uniform float uTime;
    uniform float uAmp;
    varying vec3 vN;
    varying vec3 vP;
    varying float vD;
    vec3 m289v3(vec3 x){ return x - floor(x*(1./289.))*289.; }
    vec4 m289v4(vec4 x){ return x - floor(x*(1./289.))*289.; }
    vec4 pm(vec4 x){ return m289v4((x*34.+1.)*x); }
    vec4 ti(vec4 r){ return 1.79284291400159 - 0.85373472095314*r; }
    float sn(vec3 v){
      const vec2 C = vec2(1./6.,1./3.);
      vec3 i = floor(v + dot(v, vec3(C.y)));
      vec3 x0 = v - i + dot(i, vec3(C.x));
      vec3 g = step(x0.yzx, x0.xyz);
      vec3 l = 1.0 - g;
      vec3 i1 = min(g, l.zxy);
      vec3 i2 = max(g, l.zxy);
      vec3 x1 = x0 - i1 + C.x;
      vec3 x2 = x0 - i2 + 2.0*C.x;
      vec3 x3 = x0 - 0.5;
      i = m289v3(i);
      vec4 p = pm(pm(pm(vec4(i.z)+vec4(0.,i1.z,i2.z,1.))
      +vec4(i.y)+vec4(0.,i1.y,i2.y,1.))
      +vec4(i.x)+vec4(0.,i1.x,i2.x,1.));
      vec4 jj = p - 49.*floor(p*(1./49.));
      vec4 xx = floor(jj*(1./7.));
      vec4 yy = floor(jj - 7.*xx);
      vec4 xs = xx*(2./7.) - 1.0;
      vec4 ys = yy*(2./7.) - 1.0;
      vec4 h = 1.0 - abs(xs) - abs(ys);
      vec4 b0 = vec4(xs.xy, ys.xy);
      vec4 b1 = vec4(xs.zw, ys.zw);
      vec4 s0 = floor(b0)*2.0+1.0;
      vec4 s1 = floor(b1)*2.0+1.0;
      vec4 sh = -step(h, vec4(0.0));
      vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy;
      vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww;
      vec3 q0 = vec3(a0.xy,h.x);
      vec3 q1 = vec3(a0.zw,h.y);
      vec3 q2 = vec3(a1.xy,h.z);
      vec3 q3 = vec3(a1.zw,h.w);
      vec4 nm = ti(vec4(dot(q0,q0),dot(q1,q1),dot(q2,q2),dot(q3,q3)));
      q0*=nm.x; q1*=nm.y; q2*=nm.z; q3*=nm.w;
      vec4 m4 = max(0.6-vec4(dot(x0,x0),dot(x1,x1),dot(x2,x2),dot(x3,x3)),0.0);
      m4 = m4*m4;
      return 42.0*dot(m4*m4, vec4(dot(q0,x0),dot(q1,x1),dot(q2,x2),dot(q3,x3)));
    }
    void main(){
      vN = normalMatrix * normal;
      vP = position;
      float t = uTime * 0.2;
      float deformation =
        sn(position * 2.4 + t) * 0.35 +
        sn(position * 4.5 - t * 1.2) * 0.35;
      vD = deformation;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position + normal * deformation * uAmp, 1.0);
    }`;

    const fragmentShader = `uniform vec3 uColorHighlight;
    varying vec3 vN;
    varying vec3 vP;
    varying float vD;
    void main(){
      vec3 N = normalize(vN);
      vec3 view = vec3(0.0,0.0,1.0);
      float NdV = clamp(dot(N, view), 0.0, 1.0);
      float cloud = clamp(vD * 1.2 + 0.5, 0.0, 1.0);
      vec3 colorBottom = vec3(0.005, 0.01, 0.02);
      vec3 colorTop = vec3(0.01, 0.03, 0.06);
      vec3 couleur = mix(colorBottom, colorTop, vP.y * 0.5 + 0.5);
      couleur = mix(couleur, uColorHighlight, cloud * 0.1);
      float fresnel = pow(1.0 - NdV, 4.0);
      couleur += uColorHighlight * fresnel * 0.15;
      vec3 lightDir = normalize(vec3(1.5,2.0,3.0));
      float spec = pow(max(dot(reflect(-lightDir, N), view),0.0), 60.0);
      couleur += uColorHighlight * spec * 0.4;
      vec3 background = vec3(0.005, 0.008, 0.012);
      couleur = mix(background, couleur, 0.98);
      gl_FragColor = vec4(couleur, 0.9);
    }`;

    const material = new THREE.ShaderMaterial({
      vertexShader, fragmentShader, uniforms,
      transparent: true, depthWrite: false
    });

    const sphere = new THREE.Mesh(new THREE.SphereGeometry(0.85, 128, 128), material);
    scene.add(sphere);

    let drag = false, px = 0, py = 0;
    let rotY = 0, rotX = 0, targetRotY = 0, targetRotX = 0;

    const onMouseDown = (e) => { drag = true; px = e.clientX; py = e.clientY; };
    const onMouseMove = (e) => {
      if (!drag) return;
      targetRotY += (e.clientX - px) * 0.007;
      targetRotX = Math.max(-0.8, Math.min(0.8, targetRotX + (e.clientY - py) * 0.007));
      px = e.clientX; py = e.clientY;
    };

    canvas.addEventListener("mousedown", onMouseDown);
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", () => drag = false);

    let animationId;

    function animate() {
      animationId = requestAnimationFrame(animate);
      uniforms.uTime.value = performance.now() / 1000;

      if (!drag) targetRotY += 0.003;
      rotY += (targetRotY - rotY) * 0.05;
      rotX += (targetRotX - rotX) * 0.05;
      sphere.rotation.y = rotY;
      sphere.rotation.x = rotX;

      // Scale smooth pendant lecture audio
      orbScaleRef.current += (targetScaleRef.current - orbScaleRef.current) * 0.04;
      sphere.scale.setScalar(orbScaleRef.current);

      // Amp légèrement augmenté pendant lecture
      uniforms.uAmp.value += (
        (targetScaleRef.current > 1.0 ? 0.14 : 0.09) - uniforms.uAmp.value
      ) * 0.04;

      renderer.render(scene, camera);
    }

    animate();

    const resize = () => {
      const width = canvas.clientWidth;
      const height = canvas.clientHeight;
    
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    };
    window.addEventListener("resize", resize);

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener("resize", resize);
      canvas.removeEventListener("mousedown", onMouseDown);
      renderer.dispose();
    };
  }, []);

  return (
    <div style={{ 
      position: "relative", 
      width: "100%", 
      height: "100%",
      display: "flex",
      alignItems: "center",
      justifyContent: "center"
    }}>
      <canvas
        ref={canvasRef}
        style={{ cursor: "grab", width: "100%", height: "100%" , display: "block" }}
      />
      {/* Indicateur TTS discret */}
      <div style={{
        position: "absolute", bottom: -25, left: "50%",
        transform: "translateX(-50%)",
        fontFamily: "'Orbitron', monospace",
        fontSize: 10, letterSpacing: "0.15em",
        color: ttsStatus === "playing" ? "#22d3ee" : "rgba(6,182,212,0.3)",
        transition: "color 0.4s",
        pointerEvents: "none",
        textShadow: ttsStatus === "playing" ? "0 0 10px #22d3ee" : "none"
      }}>
        {ttsStatus === "playing" ? "● LECTURE" : ttsStatus === "loading" ? "○ CHARGEMENT" : "○ EN ATTENTE"}
      </div>
    </div>
  );
}