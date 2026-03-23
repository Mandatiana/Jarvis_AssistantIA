import React, { useEffect, useRef } from "react";
import * as THREE from "three";

export default function Orb3D() {

  const canvasRef = useRef();

  useEffect(() => {

    const canvas = canvasRef.current;

    // ----- Renderer (moteur WebGL) -----
    const renderer = new THREE.WebGLRenderer({
      canvas: canvas,
      antialias: true,
      alpha: true
    });

    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setClearColor(0x000000, 0);

    const scene = new THREE.Scene();

    const camera = new THREE.PerspectiveCamera(
      40,
      window.innerWidth / window.innerHeight,
      0.1,
      100
    );

    camera.position.z = 5.2;

    const lumiereAmbiante = new THREE.AmbientLight(0x102040, 0.8);
    scene.add(lumiereAmbiante);

    const lumiereBleu = new THREE.PointLight(0x00f2ff, 3, 20);
    lumiereBleu.position.set(5, 5, 5);
    scene.add(lumiereBleu);

    const lumiereViolette = new THREE.PointLight(0x7000ff, 2, 15);
    lumiereViolette.position.set(-5, -3, 2);
    scene.add(lumiereViolette);

    const uniforms = {
      uTime: { value: 0 },
      uAmp: { value: 0.09 },
      uColorBase: { value: new THREE.Color("#1e4bb3") },
      uColorInternal: { value: new THREE.Color("#1e4bb3") },
      uColorHighlight: { value: new THREE.Color("#99f3ff") }
    };

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

      q0*=nm.x;
      q1*=nm.y;
      q2*=nm.z;
      q3*=nm.w;

      vec4 m4 = max(0.6-vec4(dot(x0,x0),dot(x1,x1),dot(x2,x2),dot(x3,x3)),0.0);
      m4 = m4*m4;

      return 42.0*dot(m4*m4,
      vec4(dot(q0,x0),dot(q1,x1),dot(q2,x2),dot(q3,x3)));
    }

    void main(){

      vN = normalMatrix * normal;
      vP = position;

      float t = uTime * 0.2;

      float deformation =
        sn(position * 2.4 + t) * 0.35 +
        sn(position * 4.5 - t * 1.2) * 0.35;

      vD = deformation;

      gl_Position =
        projectionMatrix *
        modelViewMatrix *
        vec4(position + normal * deformation * uAmp, 1.0);
    }
  `; 
    const fragmentShader = `uniform vec3 uColorHighlight;

    varying vec3 vN;
    varying vec3 vP;
    varying float vD;
    
    void main(){
    
      vec3 N = normalize(vN);
      vec3 view = vec3(0.0,0.0,1.0);
    
      float NdV = clamp(dot(N, view), 0.0, 1.0);
    
      float cloud = clamp(vD * 1.2 + 0.5, 0.0, 1.0);
    
      //  palette plus dark
      vec3 colorBottom = vec3(0.005, 0.01, 0.02);
      vec3 colorTop = vec3(0.01, 0.03, 0.06);
    
      vec3 couleur = mix(colorBottom, colorTop, vP.y * 0.5 + 0.5);
    
      
      couleur = mix(couleur, uColorHighlight, cloud * 0.1);
    
      float fresnel = pow(1.0 - NdV, 4.0);
      couleur += uColorHighlight * fresnel * 0.15;
    
      
      vec3 lightDir = normalize(vec3(1.5,2.0,3.0));
    
      float spec =
        pow(max(dot(reflect(-lightDir, N), view),0.0), 60.0);
    
      couleur += uColorHighlight * spec * 0.4;
    
      //  background encore plus dark
      vec3 background = vec3(0.005, 0.008, 0.012);
    
      couleur = mix(background, couleur, 0.98);
    
      gl_FragColor = vec4(couleur, 0.9);
    
    }`; 

    const material = new THREE.ShaderMaterial({
      vertexShader: vertexShader,
      fragmentShader: fragmentShader,
      uniforms: uniforms,
      transparent: true,
      depthWrite: false
    });

    const sphere = new THREE.Mesh(
      new THREE.SphereGeometry(0.85, 128, 128),
      material
    );

    scene.add(sphere);

    let drag = false;
    let px = 0;
    let py = 0;

    let rotY = 0;
    let rotX = 0;

    let targetRotY = 0;
    let targetRotX = 0;

    const onMouseDown = (e) => {
      drag = true;
      px = e.clientX;
      py = e.clientY;
    };

    const onMouseMove = (e) => {

      if (!drag) return;

      targetRotY += (e.clientX - px) * 0.007;

      targetRotX = Math.max(
        -0.8,
        Math.min(0.8, targetRotX + (e.clientY - py) * 0.007)
      );

      px = e.clientX;
      py = e.clientY;
    };

    canvas.addEventListener("mousedown", onMouseDown);
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", () => drag = false);

    let animationId;

    function animate(){

      animationId = requestAnimationFrame(animate);

      uniforms.uTime.value = performance.now() / 1000;

      if(!drag) targetRotY += 0.003;

      rotY += (targetRotY - rotY) * 0.05;
      rotX += (targetRotX - rotX) * 0.05;

      sphere.rotation.y = rotY;
      sphere.rotation.x = rotX;

      renderer.render(scene, camera);
    }

    animate();

    const resize = () => {

      renderer.setSize(window.innerWidth, window.innerHeight);

      camera.aspect =
        window.innerWidth / window.innerHeight;

      camera.updateProjectionMatrix();
    };

    window.addEventListener("resize", resize);

    return () => {

      cancelAnimationFrame(animationId);

      window.removeEventListener("resize", resize);

      renderer.dispose();
    };

  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        cursor: "grab",
        width: "100%",
        height: "100%"
      }}
    />
  );
}