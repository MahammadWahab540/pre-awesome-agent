'use client';

import { useEffect, useRef } from 'react';
import * as THREE from 'three';

interface FluidVisualizerProps {
    volume: number; // 0 to 1 (agent output volume)
    inVolume: number; // 0 to 1 (user input volume)
    isActive: boolean;
}

export const FluidVisualizer: React.FC<FluidVisualizerProps> = ({ volume, inVolume, isActive }) => {
    const mountRef = useRef<HTMLDivElement>(null);
    const frameIdRef = useRef<number>();
    const isInitializedRef = useRef(false);

    const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
    const sphereRef = useRef<THREE.Mesh | null>(null);
    const materialRef = useRef<THREE.MeshPhysicalMaterial | null>(null);
    const rendererRef = useRef<THREE.WebGLRenderer | null>(null);

    const isActiveRef = useRef(isActive);
    const volumeRef = useRef(volume);
    const inVolumeRef = useRef(inVolume);

    useEffect(() => {
        isActiveRef.current = isActive;
        volumeRef.current = volume;
        inVolumeRef.current = inVolume;
    }, [isActive, volume, inVolume]);

    useEffect(() => {
        if (!mountRef.current || isInitializedRef.current) return;

        isInitializedRef.current = true;

        const container = mountRef.current;
        const existingCanvas = container.querySelector('canvas');
        if (existingCanvas) {
            existingCanvas.remove();
        }

        const width = container.clientWidth;
        const height = container.clientHeight;

        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
        camera.position.z = 5;
        cameraRef.current = camera;

        const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        renderer.setSize(width, height);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.setClearColor(0x0B0F17, 1); // Match background
        container.appendChild(renderer.domElement);
        rendererRef.current = renderer;

        // Create the mercury orb with pearlescent material
        const geometry = new THREE.IcosahedronGeometry(1.1, 64);
        const material = new THREE.MeshPhysicalMaterial({
            color: new THREE.Color("#dcdcdc"),
            metalness: 0.1,
            roughness: 0.15,
            clearcoat: 1.0,
            clearcoatRoughness: 0.1,
            sheen: 1.0,
            sheenColor: new THREE.Color("#a7b7ff"),
            emissive: new THREE.Color("#2b2b44"),
            emissiveIntensity: 0.15,
        });
        materialRef.current = material;

        // Shader for audio-reactive deformation
        material.onBeforeCompile = (shader) => {
            shader.uniforms.time = { value: 0 };
            shader.uniforms.inputData = { value: new THREE.Vector4() };
            shader.uniforms.outputData = { value: new THREE.Vector4() };
            (material as any).userData.shader = shader;

            const deformationCode = `
                uniform float time;
                uniform vec4 inputData;
                uniform vec4 outputData;
                
                vec3 calc(vec3 pos) {
                    vec3 dir = normalize(pos);
                    vec3 deformation = 1.0 * inputData.x * inputData.y * dir * (0.5 + 0.5 * sin(inputData.z * pos.x + time));
                    deformation += 1.0 * outputData.x * outputData.y * dir * (0.5 + 0.5 * sin(outputData.z * (pos.y+pos.x) + time));
                    return pos + deformation;
                }
            `;

            const vertexReplacement = `
                #include <begin_vertex>
                float inc = 0.001;
                vec3 newPosition = calc(position);
                
                vec3 tangent = normalize(calc(position + vec3(inc, 0.0, 0.0)) - newPosition);
                vec3 bitangent = normalize(calc(position + vec3(0.0, inc, 0.0)) - newPosition);
                vec3 newNormal = -normalize(cross(tangent, bitangent));
                
                transformed = newPosition;
                objectNormal = newNormal;
            `;

            shader.vertexShader = deformationCode + '\n' + shader.vertexShader;
            shader.vertexShader = shader.vertexShader.replace('#include <begin_vertex>', vertexReplacement);
        };

        const sphere = new THREE.Mesh(geometry, material);
        sphereRef.current = sphere;
        scene.add(sphere);

        // Lighting setup
        scene.add(new THREE.AmbientLight(0xffffff, 0.3));

        const keyLight = new THREE.DirectionalLight(0xffffff, 2.0);
        keyLight.position.set(-3, 3, 4);
        scene.add(keyLight);

        let prevTime = performance.now();
        const rotation = new THREE.Vector3(0, 0, 0);

        const animate = () => {
            frameIdRef.current = requestAnimationFrame(animate);

            const t = performance.now() / 1000.0;

            const currentOutputVolume = volumeRef.current;
            const currentInputVolume = inVolumeRef.current;
            const currentActive = isActiveRef.current;

            // --- FIX START: PRE-AMPLIFICATION ---
            // 1. We boost the raw volume by 4x or 5x because raw audio is usually quiet (0.1-0.2).
            // 2. We add a tiny base value (0.1) if active, so the blob is never totally frozen when "Live".
            // 3. We clamp Math.min to 1.2 so it doesn't explode on loud noises.
            
            const boost = 5.0; 
            const baseObj = 0.1;

            const effectiveOutput = currentActive && currentOutputVolume > 0.01 
                ? Math.min(currentOutputVolume * boost + baseObj, 1.2) 
                : 0.0;
                
            const effectiveInput = currentActive && currentInputVolume > 0.01 
                ? Math.min(currentInputVolume * boost + baseObj, 1.2) 
                : 0.0;

            const outputDeform = effectiveOutput;
            const inputDeform = effectiveInput;
            // --- FIX END ---

            // Output deformation (agent speaking)
            const dataOutput = [
                outputDeform * (0.6 + 0.4 * Math.sin(t * 5.0)),
                outputDeform * (0.7 + 0.3 * Math.cos(t * 3.0)),
                outputDeform * (0.8 + 0.2 * Math.sin(t * 7.0)),
            ].map(v => v * 255);

            // Input deformation (user speaking)
            const dataInput = [
                inputDeform * (0.6 + 0.4 * Math.cos(t * 4.0)),
                inputDeform * (0.7 + 0.3 * Math.sin(t * 6.0)),
                inputDeform * (0.8 + 0.2 * Math.cos(t * 2.0)),
            ].map(v => v * 255);

            const now = performance.now();
            const dt = (now - prevTime) / (1000 / 60);
            prevTime = now;

            if (sphereRef.current && materialRef.current && cameraRef.current && rendererRef.current) {
                const material = materialRef.current;
                const shader = (material as any).userData.shader;
                const cam = cameraRef.current;
                const sph = sphereRef.current;

                const f = 0.001;

                // Check for activity (Lowered threshold to ensure movement)
                const hasActivity = currentActive && (effectiveOutput > 0.01 || effectiveInput > 0.01);

                if (hasActivity) {
                    rotation.x += (dt * f * 0.5 * dataOutput[1]) / 255;
                    rotation.z += (dt * f * 0.5 * dataInput[1]) / 255;
                    rotation.y += (dt * f * 0.25 * (dataInput[2] + dataOutput[2])) / 255;
                }

                const euler = new THREE.Euler(rotation.x, rotation.y, rotation.z);
                const quaternion = new THREE.Quaternion().setFromEuler(euler);
                const vector = new THREE.Vector3(0, 0, 5);
                vector.applyQuaternion(quaternion);
                cam.position.copy(vector);
                cam.lookAt(sph.position);

                if (shader?.uniforms) {
                    if (hasActivity) {
                        shader.uniforms.time.value += (dt * 0.2 * (dataOutput[0] + dataInput[0])) / 255;
                    }
                    
                    // You can keep your existing multipliers here, or tune them slightly down 
                    // if the Boost above makes it too crazy. 
                    // Current settings:
                    shader.uniforms.inputData.value.set(
                        (4.0 * dataInput[0]) / 255,   
                        (0.3 * dataInput[1]) / 255,   
                        (15 * dataInput[2]) / 255,     
                        0
                    );
                    shader.uniforms.outputData.value.set(
                        (5.0 * dataOutput[0]) / 255,   
                        (0.3 * dataOutput[1]) / 255,   
                        (15 * dataOutput[2]) / 255,    
                        0
                    );
                }

                rendererRef.current.render(scene, cam);
            }
        };
        animate();

        const handleResize = () => {
            if (!mountRef.current || !cameraRef.current || !rendererRef.current) return;
            const newWidth = mountRef.current.clientWidth;
            const newHeight = mountRef.current.clientHeight;
            cameraRef.current.aspect = newWidth / newHeight;
            cameraRef.current.updateProjectionMatrix();
            rendererRef.current.setSize(newWidth, newHeight);
        };
        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            if (frameIdRef.current) {
                cancelAnimationFrame(frameIdRef.current);
            }
            if (rendererRef.current) {
                if (container.contains(rendererRef.current.domElement)) {
                    container.removeChild(rendererRef.current.domElement);
                }
                rendererRef.current.dispose();
            }
            geometry.dispose();
            material.dispose();
            isInitializedRef.current = false;
        };
    }, []);

    return (
        <div className="relative w-full h-full flex items-center justify-center overflow-hidden bg-[#0B0F17]">
            {/* Status Text */}
            <div className="absolute top-1/4 left-0 right-0 text-center z-10 pointer-events-none">
                {isActive ? (
                    <div className="flex items-center justify-center gap-2 px-3 py-1">
                        <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse" />
                        <span className="text-blue-200 text-xs font-medium tracking-wider uppercase">Live</span>
                    </div>
                ) : (
                    <span className="text-white/30 text-xs font-medium tracking-widest uppercase">Idle</span>
                )}
            </div>

            {/* 3D Canvas Container */}
            <div ref={mountRef} className="w-full h-full absolute inset-0" />
        </div>
    );
};
