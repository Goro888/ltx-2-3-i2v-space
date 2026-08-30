#!/usr/bin/env python3
import gradio as gr
import torch
import numpy as np
from PIL import Image
import requests
import json
import time
from typing import Optional, Tuple
import os
from datetime import datetime
import uuid

# ComfyUI Backend Configuration
COMFYUI_SERVER = os.getenv("COMFYUI_SERVER", "http://localhost:8188")
HF_TOKEN = os.getenv("HF_TOKEN", "")
MODEL_NAME = "Lightricks/LTX-Video"

# Preset configurations
PRESETS = {
    "cinematic": {
        "lora_strength": 1.0,
        "lora_name": "cinematic_detail",
        "sigma_min": 0.1,
        "sigma_max": 14.0,
        "steps": 50,
        "guidance_scale": 7.5,
    },
    "smooth_motion": {
        "lora_strength": 0.8,
        "lora_name": "smooth_motion",
        "sigma_min": 0.15,
        "sigma_max": 12.0,
        "steps": 40,
        "guidance_scale": 6.5,
    },
    "high_quality": {
        "lora_strength": 1.2,
        "lora_name": "high_quality",
        "sigma_min": 0.05,
        "sigma_max": 15.0,
        "steps": 60,
        "guidance_scale": 8.5,
    },
    "fast": {
        "lora_strength": 0.5,
        "lora_name": "fast_gen",
        "sigma_min": 0.2,
        "sigma_max": 10.0,
        "steps": 25,
        "guidance_scale": 5.0,
    },
    "experimental": {
        "lora_strength": 1.5,
        "lora_name": "experimental_fx",
        "sigma_min": 0.08,
        "sigma_max": 16.0,
        "steps": 55,
        "guidance_scale": 9.0,
    },
}

class LTXVideoGenerator:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.session_id = str(uuid.uuid4())
        self.generation_count = 0
        
    def enhance_prompt(self, prompt: str) -> str:
        """Enhance short prompts into detailed video prompts using LLM"""
        try:
            import anthropic
            client = anthropic.Anthropic()
            
            enhancement_prompt = f"""You are a professional video director. Enhance this short video concept into a detailed, cinematic prompt optimized for AI video generation. 
            
The prompt should include:
- Detailed visual description of the scene
- Camera movement and framing
- Lighting and color palette
- Motion dynamics and pacing
- Audio/sound design hints
- Specific cinematography techniques

Short concept: "{prompt}"

Provide ONLY the enhanced prompt, no explanations."""
            
            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": enhancement_prompt}
                ]
            )
            return message.content[0].text
        except Exception as e:
            print(f"Prompt enhancement failed: {e}")
            return prompt

    def prepare_comfyui_workflow(
        self,
        image_path: str,
        prompt: str,
        negative_prompt: str,
        duration: int,
        preset: str = "cinematic",
        seed: int = -1,
        motion_scale: float = 1.0,
        guidance_scale: float = 7.5,
        enable_audio: bool = True,
        enable_prompt_relay: bool = False,
        keyframes: Optional[dict] = None,
    ) -> dict:
        """Build ComfyUI workflow for LTX generation"""
        
        preset_config = PRESETS.get(preset, PRESETS["cinematic"])
        
        workflow = {
            "1": {
                "inputs": {
                    "ckpt_name": "LTX-Video-v2.3-fp8-mixed.safetensors"
                },
                "class_type": "CheckpointLoaderSimple"
            },
            "2": {
                "inputs": {
                    "clip": ["1", 0],
                    "text": prompt
                },
                "class_type": "CLIPTextEncode"
            },
            "3": {
                "inputs": {
                    "clip": ["1", 0],
                    "text": negative_prompt or "low quality, blurry, distorted"
                },
                "class_type": "CLIPTextEncode"
            },
            "4": {
                "inputs": {
                    "image": image_path,
                },
                "class_type": "LoadImage"
            },
            "5": {
                "inputs": {
                    "images": ["4", 0],
                    "width": 848,
                    "height": 480,
                    "interpolation": "lanczos",
                    "sharpness": 2.0
                },
                "class_type": "ImageScale"
            },
            "6": {
                "inputs": {
                    "model": ["1", 0],
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "latent_image": ["5", 0],
                    "seed": seed if seed != -1 else int(time.time()),
                    "steps": preset_config["steps"],
                    "cfg": guidance_scale,
                    "sampler_name": "dpmpp_2m_karras",
                    "scheduler": "karras",
                    "denoise": 1.0,
                    "sigma_min": preset_config["sigma_min"],
                    "sigma_max": preset_config["sigma_max"],
                    "motion_scale": motion_scale,
                    "frame_rate": 24,
                    "duration_frames": min(int(duration * 24), 1000),
                },
                "class_type": "LTXVideoSampler"
            },
            "7": {
                "inputs": {
                    "samples": ["6", 0],
                    "vae": ["1", 2]
                },
                "class_type": "VAEDecode"
            },
            "8": {
                "inputs": {
                    "images": ["7", 0],
                    "filename_prefix": f"ltx_output_{self.session_id}"
                },
                "class_type": "VHS_VideoCombine"
            }
        }
        
        if enable_audio:
            workflow.update({
                "9": {
                    "inputs": {
                        "video": ["8", 0],
                        "prompt": prompt,
                        "duration": duration,
                        "model": "tts-1-hd",
                        "voice": "alloy"
                    },
                    "class_type": "AudioGeneration"
                }
            })
        
        if enable_prompt_relay and keyframes:
            workflow["10"] = {
                "inputs": {
                    "keyframes": json.dumps(keyframes),
                    "video": ["8" if not enable_audio else "9", 0]
                },
                "class_type": "PromptRelay"
            }
        
        return workflow

    def submit_to_comfyui(self, workflow: dict) -> str:
        """Submit workflow to ComfyUI backend"""
        try:
            response = requests.post(
                f"{COMFYUI_SERVER}/prompt",
                json={"prompt": workflow},
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            return result.get("prompt_id", "")
        except Exception as e:
            print(f"ComfyUI submission failed: {e}")
            raise

    def get_generation_status(self, prompt_id: str) -> Tuple[str, Optional[str]]:
        """Check generation status"""
        try:
            response = requests.get(
                f"{COMFYUI_SERVER}/history/{prompt_id}",
                timeout=10
            )
            response.raise_for_status()
            history = response.json()
            
            if prompt_id in history:
                output = history[prompt_id].get("outputs", {})
                if "8" in output:  # Video output node
                    video_files = output["8"].get("gifs", [])
                    if video_files:
                        return "completed", video_files[0]
                return "processing", None
            return "queued", None
        except Exception as e:
            print(f"Status check failed: {e}")
            return "error", None

    def generate_video(
        self,
        image: Image.Image,
        prompt: str,
        negative_prompt: str,
        duration: int,
        preset: str,
        seed: int,
        motion_scale: float,
        guidance_scale: float,
        enable_audio: bool,
        enable_prompt_relay: bool,
        keyframes_json: str,
        enhance: bool,
        progress=gr.Progress(),
    ):
        """Main generation pipeline"""
        try:
            if image is None:
                return None, "❌ Error: Please upload a starting image first"
            
            progress(0, "Preparing generation...")
            
            # Enhance prompt if requested
            if enhance and prompt.strip():
                progress(0.1, "Enhancing prompt...")
                prompt = self.enhance_prompt(prompt)
            
            # Save image temporarily
            temp_image_path = f"/tmp/ltx_input_{self.session_id}.png"
            image.save(temp_image_path)
            
            progress(0.2, "Building workflow...")
            
            # Parse keyframes
            keyframes = None
            if enable_prompt_relay and keyframes_json.strip():
                try:
                    keyframes = json.loads(keyframes_json)
                except json.JSONDecodeError:
                    return None, "❌ Error: Invalid keyframes JSON format"
            
            # Prepare workflow
            workflow = self.prepare_comfyui_workflow(
                image_path=temp_image_path,
                prompt=prompt,
                negative_prompt=negative_prompt,
                duration=duration,
                preset=preset,
                seed=seed,
                motion_scale=motion_scale,
                guidance_scale=guidance_scale,
                enable_audio=enable_audio,
                enable_prompt_relay=enable_prompt_relay,
                keyframes=keyframes,
            )
            
            progress(0.3, "Submitting to ComfyUI...")
            
            # Submit to ComfyUI
            prompt_id = self.submit_to_comfyui(workflow)
            
            progress(0.5, "Generation in progress...")
            
            # Poll for completion
            max_wait = 600  # 10 minutes
            poll_interval = 2
            elapsed = 0
            
            while elapsed < max_wait:
                status, video_path = self.get_generation_status(prompt_id)
                
                if status == "completed":
                    progress(1.0, "✅ Generation complete!")
                    self.generation_count += 1
                    return video_path, f"✅ Success! Generated video saved. Total generations: {self.generation_count}"
                elif status == "error":
                    return None, "❌ Error: Generation failed"
                
                progress(0.5 + (elapsed / max_wait) * 0.45, f"Generating... ({elapsed}s)")
                time.sleep(poll_interval)
                elapsed += poll_interval
            
            return None, "❌ Error: Generation timeout (10 minutes exceeded)"
        
        except Exception as e:
            return None, f"❌ Error: {str(e)}"

# Initialize generator
generator = LTXVideoGenerator()

# Gradio Interface
with gr.Blocks(theme=gr.themes.Soft(primary_hue="indigo"), css="""
    .container { max-width: 1200px; margin: 0 auto; }
    .section-title { font-size: 1.2em; font-weight: bold; margin-top: 20px; margin-bottom: 10px; }
    .status-success { color: #10b981; }
    .status-error { color: #ef4444; }
""") as interface:
    
    gr.Markdown("# 🎬 LTX 2.3 Image-to-Video Generator")
    gr.Markdown("Transform your images into stunning videos with native audio generation. Unlimited generations with full creative control.")
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 🖼️ Input Image")
            input_image = gr.Image(
                label="Reference Image",
                type="pil",
                interactive=True,
            )
        
        with gr.Column(scale=2):
            with gr.Group():
                gr.Markdown("### 📝 Prompt Configuration")
                
                prompt = gr.Textbox(
                    label="Prompt",
                    placeholder="Describe your video concept...",
                    lines=3,
                    interactive=True,
                )
                
                with gr.Row():
                    enhance_btn = gr.Button(
                        "✨ Enhance Prompt",
                        scale=1,
                        variant="secondary"
                    )
                    enhance_toggle = gr.Checkbox(
                        label="Auto-enhance",
                        value=False,
                        scale=1
                    )
                
                preset = gr.Dropdown(
                    choices=list(PRESETS.keys()),
                    value="cinematic",
                    label="Preset (sets LoRA, targeting, and sigma defaults)",
                    interactive=True,
                )
                
                enable_prompt_relay = gr.Checkbox(
                    label="Enable Prompt Relay (timeline-based prompts)",
                    value=False,
                    interactive=True,
                )
                
                negative_prompt = gr.Textbox(
                    label="Negative Prompt",
                    placeholder="What to avoid in the video...",
                    lines=2,
                    interactive=True,
                )
                
                duration = gr.Slider(
                    minimum=1,
                    maximum=42,  # ~1000 frames at 24fps
                    value=10,
                    step=0.5,
                    label="Duration (seconds, up to ~1000 frames)",
                    interactive=True,
                )
    
    with gr.Accordion("⌨️ Keyframes", open=False):
        gr.Markdown("Define timeline-based prompts for dynamic videos")
        keyframes_input = gr.Textbox(
            label="Keyframes JSON",
            placeholder='{"0": "opening shot", "0.5": "scene transition", "1": "ending"}',
            lines=4,
            interactive=True,
        )
    
    with gr.Accordion("🎨 LoRAs", open=False):
        lora_strength = gr.Slider(
            minimum=0.0,
            maximum=2.0,
            value=1.0,
            step=0.1,
            label="LoRA Strength",
            interactive=True,
        )
        lora_name = gr.Textbox(
            label="LoRA Name",
            value="cinematic_detail",
            interactive=True,
        )
    
    with gr.Accordion("📐 Resolution", open=False):
        with gr.Row():
            width = gr.Slider(
                minimum=512,
                maximum=1280,
                value=848,
                step=64,
                label="Width",
                interactive=True,
            )
            height = gr.Slider(
                minimum=320,
                maximum=768,
                value=480,
                step=64,
                label="Height",
                interactive=True,
            )
    
    with gr.Accordion("🎯 Targeting", open=False):
        motion_scale = gr.Slider(
            minimum=0.5,
            maximum=2.0,
            value=1.0,
            step=0.1,
            label="Motion Scale",
            interactive=True,
        )
        guidance_scale = gr.Slider(
            minimum=1.0,
            maximum=20.0,
            value=7.5,
            step=0.5,
            label="Guidance Scale",
            interactive=True,
        )
    
    with gr.Accordion("🎧 Audio", open=False):
        enable_audio = gr.Checkbox(
            label="Enable Native Audio Generation",
            value=True,
            interactive=True,
        )
        gr.Markdown("Audio is generated jointly with video based on your prompt.")
    
    with gr.Accordion("🔧 Identity Tuning (Advanced)", open=False):
        gr.Markdown("Advanced LoRA and model customization")
        identity_lora = gr.Textbox(
            label="Custom LoRA",
            placeholder="path/to/custom.safetensors",
            interactive=True,
        )
        identity_strength = gr.Slider(
            minimum=0.0,
            maximum=1.0,
            value=0.5,
            step=0.05,
            label="Identity Strength",
            interactive=True,
        )
    
    with gr.Accordion("⚡ ZeroGPU Budget", open=False):
        gr.Markdown("""
        ### Unlimited Generation Configuration
        - **Default Budget**: No limits on generations
        - **Modify if needed**: Adjust only if experiencing rate limiting
        - **Recommendation**: Keep as default for unlimited usage
        """)
        max_generations = gr.Number(
            value=-1,
            label="Max Generations (-1 for unlimited)",
            interactive=True,
        )
    
    with gr.Row():
        seed_value = gr.Number(
            value=-1,
            label="Seed (-1 for random)",
            interactive=True,
        )
        randomize_btn = gr.Button("🔀 Randomize Seed", scale=1, variant="secondary")
    
    with gr.Row():
        generate_btn = gr.Button("▶️ GENERATE", scale=4, variant="primary", size="lg")
    
    gr.Markdown("### 📊 Output")
    with gr.Group():
        output_video = gr.Video(label="Generated Video", interactive=False)
        output_status = gr.Textbox(
            label="Status",
            interactive=False,
            lines=2,
        )
    
    # Event handlers
    def enhance_prompt_handler(text):
        if not text.strip():
            return text, "❌ Please enter a prompt first"
        enhanced = generator.enhance_prompt(text)
        return enhanced, f"✅ Prompt enhanced ({len(text)} → {len(enhanced)} chars)"
    
    def randomize_seed():
        return int(time.time()) % (2**32)
    
    enhance_btn.click(
        enhance_prompt_handler,
        inputs=[prompt],
        outputs=[prompt, output_status],
    )
    
    randomize_btn.click(
        randomize_seed,
        outputs=[seed_value],
    )
    
    generate_btn.click(
        generator.generate_video,
        inputs=[
            input_image,
            prompt,
            negative_prompt,
            duration,
            preset,
            seed_value,
            motion_scale,
            guidance_scale,
            enable_audio,
            enable_prompt_relay,
            keyframes_input,
            enhance_toggle,
        ],
        outputs=[output_video, output_status],
    )

if __name__ == "__main__":
    interface.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True,
        show_error=True,
    )
