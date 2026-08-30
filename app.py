#!/usr/bin/env python3
"""
LTX 2.3 Image-to-Video Generator - Hugging Face Space
Main Gradio application with ComfyUI backend integration
"""

import gradio as gr
import os
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List
import tempfile
import uuid

from comfyui_backend import ComfyUIBackend, WorkflowBuilder, GenerationStatus
from policy_checker import ContentModerator, validate_image_content

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
COMFYUI_SERVER = os.getenv("COMFYUI_SERVER", "http://localhost:8188")
MAX_GENERATION_TIME = 600  # 10 minutes
ENABLE_POLICY_CHECK = os.getenv("ENABLE_POLICY_CHECK", "true").lower() == "true"

# Initialize backend services
backend = ComfyUIBackend(COMFYUI_SERVER)
moderator = ContentModerator()

# Preset configurations
PRESETS = {
    "🎬 Cinematic": {
        "steps": 50,
        "guidance_scale": 7.5,
        "sigma_min": 0.1,
        "sigma_max": 14.0,
        "description": "Professional cinematic look with balanced motion"
    },
    "🎞️ Smooth Motion": {
        "steps": 40,
        "guidance_scale": 7.0,
        "sigma_min": 0.2,
        "sigma_max": 14.0,
        "description": "Natural, smooth camera movements and transitions"
    },
    "✨ High Quality": {
        "steps": 60,
        "guidance_scale": 8.0,
        "sigma_min": 0.05,
        "sigma_max": 14.0,
        "description": "Maximum detail and quality (slower)"
    },
    "⚡ Fast": {
        "steps": 25,
        "guidance_scale": 6.5,
        "sigma_min": 0.3,
        "sigma_max": 14.0,
        "description": "Quick previews and rapid iteration"
    },
    "🎨 Experimental": {
        "steps": 55,
        "guidance_scale": 9.0,
        "sigma_min": 0.1,
        "sigma_max": 15.0,
        "description": "Creative, dynamic effects"
    }
}

def enhance_prompt_with_claude(prompt: str) -> str:
    """Enhance prompt using Claude 3.5 Sonnet via Anthropic API"""
    try:
        from anthropic import Anthropic
        
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not set, skipping prompt enhancement")
            return prompt
        
        client = Anthropic()
        
        enhancement_prompt = f"""You are a cinematic video prompt engineer. 
Enhance this video generation prompt with vivid cinematography details, camera movements, 
lighting, and mood. Keep it concise but descriptive. Focus on visual storytelling.

Original prompt: {prompt}

Enhanced prompt (only return the enhanced prompt, no explanation):"""
        
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=200,
            messages=[{"role": "user", "content": enhancement_prompt}]
        )
        
        enhanced = message.content[0].text.strip()
        logger.info(f"Prompt enhanced: {len(enhanced)} chars")
        return enhanced
        
    except Exception as e:
        logger.error(f"Prompt enhancement failed: {e}")
        return prompt

def validate_generation_request(
    image,
    prompt: str,
    negative_prompt: str,
    keyframes_json: str
) -> Tuple[bool, str]:
    """Validate generation request before submission"""
    
    # Check image
    if image is None:
        return False, "❌ Please upload an image first"
    
    # Check prompt
    if not prompt or len(prompt.strip()) == 0:
        return False, "❌ Please enter a prompt"
    
    # Validate with policy checker
    if ENABLE_POLICY_CHECK:
        session_id = str(uuid.uuid4())
        approved, message = moderator.check_generation_request(
            session_id, prompt, negative_prompt, keyframes_json
        )
        if not approved:
            return False, message
    
    # Validate image content
    if isinstance(image, str):
        image_path = image
    else:
        # Save uploaded image temporarily
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            image.save(tmp.name)
            image_path = tmp.name
    
    is_valid, validation_msg = validate_image_content(image_path)
    if not is_valid:
        return False, f"❌ {validation_msg}"
    
    return True, "✅ Request validated"

def generate_video(
    image,
    prompt: str,
    negative_prompt: str,
    preset: str = "🎬 Cinematic",
    duration_seconds: float = 10,
    resolution: str = "848x480",
    motion_scale: float = 1.0,
    guidance_scale: float = 7.5,
    seed: int = -1,
    keyframes_json: str = "",
    lora_name: str = "",
    lora_strength: float = 0.5,
    enhance_prompt: bool = False,
    generate_audio: bool = True,
    progress=gr.Progress()
) -> Tuple[Optional[str], str, Optional[str]]:
    """
    Generate video from image and prompt
    Returns: (video_path, status_message, audio_path)
    """
    
    session_id = str(uuid.uuid4())
    logger.info(f"Starting generation {session_id}")
    
    try:
        # Validate request
        is_valid, validation_msg = validate_generation_request(
            image, prompt, negative_prompt, keyframes_json
        )
        if not is_valid:
            return None, validation_msg, None
        
        progress(0.1, "Validating request...")
        
        # Enhance prompt if requested
        if enhance_prompt:
            progress(0.15, "Enhancing prompt...")
            prompt = enhance_prompt_with_claude(prompt)
        
        # Parse resolution
        width, height = map(int, resolution.split("x"))
        
        # Calculate duration in frames (24fps)
        duration_frames = min(int(duration_seconds * 24), 1000)
        
        # Get preset config
        preset_config = PRESETS.get(preset, PRESETS["🎬 Cinematic"])
        
        # Override with user values if provided
        steps = preset_config["steps"]
        if guidance_scale is None:
            guidance_scale = preset_config["guidance_scale"]
        
        # Generate seed if not provided
        if seed < 0:
            seed = int(time.time() * 1000) % (2**31)
        
        # Check ComfyUI health
        progress(0.2, "Checking backend...")
        if not backend.health_check():
            return None, "❌ ComfyUI backend not available", None
        
        # Upload image to ComfyUI
        progress(0.3, "📤 Uploading image...")
        logger.info("Uploading image")
        
        if isinstance(image, str):
            image_path = image
        else:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                image.save(tmp.name)
                image_path = tmp.name
        
        upload_result = backend.upload_image(image_path)
        if not upload_result or "name" not in upload_result:
            return None, "❌ Image upload failed", None
        
        image_filename = upload_result["name"]
        
        # Build workflow
        progress(0.4, "🔨 Building workflow...")
        logger.info("Building workflow")
        
        workflow = WorkflowBuilder.build_ltx_workflow(
            image_path=image_filename,
            prompt=prompt,
            negative_prompt=negative_prompt or "low quality, blurry, distorted",
            duration_frames=duration_frames,
            seed=seed,
            guidance_scale=guidance_scale,
            steps=steps,
            sigma_min=preset_config["sigma_min"],
            sigma_max=preset_config["sigma_max"],
            motion_scale=motion_scale,
            width=width,
            height=height,
            lora_name=lora_name if lora_name else None,
            lora_strength=lora_strength
        )
        
        # Submit workflow
        progress(0.5, "📤 Submitting to ComfyUI...")
        logger.info("Submitting workflow")
        
        prompt_id = backend.submit_workflow(workflow)
        
        # Wait for completion
        progress(0.6, f"⏳ Generating video ({duration_seconds}s)...")
        
        status, outputs = backend.wait_for_completion(
            prompt_id,
            max_wait=MAX_GENERATION_TIME,
            progress_callback=lambda msg: progress(0.6 + 0.3 * min(1.0, time.time() / MAX_GENERATION_TIME), msg)
        )
        
        if status != GenerationStatus.COMPLETED:
            return None, f"❌ Generation failed: {status.value}", None
        
        # Extract outputs
        progress(0.9, "📥 Downloading results...")
        video_file = backend.extract_video_output(outputs)
        audio_file = backend.extract_audio_output(outputs) if generate_audio else None
        
        if not video_file:
            return None, "❌ No video output generated", None
        
        # Download files
        logger.info("Downloading results")
        
        video_data = backend.download_file(video_file, "output")
        
        # Save video to temp file
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp.write(video_data)
            video_output_path = tmp.name
        
        # Download audio if available
        audio_output_path = None
        if audio_file:
            try:
                audio_data = backend.download_file(audio_file, "output")
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                    tmp.write(audio_data)
                    audio_output_path = tmp.name
            except Exception as e:
                logger.warning(f"Audio download failed: {e}")
        
        completion_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        success_msg = f"""✅ **Generation Complete!**

📊 Details:
- Duration: {duration_seconds}s ({duration_frames} frames)
- Resolution: {resolution}
- Preset: {preset}
- Guidance: {guidance_scale}
- Steps: {steps}
- Seed: {seed}
- Completed: {completion_time}

🎬 Video ready for download!"""
        
        progress(1.0, "✅ Done!")
        logger.info(f"Generation {session_id} completed successfully")
        return video_output_path, success_msg, audio_output_path
        
    except Exception as e:
        logger.error(f"Generation failed: {e}", exc_info=True)
        return None, f"❌ Error: {str(e)}", None

def create_interface():
    """Create Gradio interface"""
    
    with gr.Blocks(
        title="LTX 2.3 Image-to-Video Generator",
        theme=gr.themes.Soft()
    ) as demo:
        
        # Header
        gr.Markdown("""
# 🎬 LTX 2.3 Image-to-Video Generator
### Unlimited image-to-video generation with native audio synthesis

Transform your images into stunning videos with professional cinematography controls.
        """)
        
        with gr.Row():
            # Left column - Inputs
            with gr.Column(scale=1):
                gr.Markdown("### 📸 Input")
                
                image_input = gr.Image(
                    label="Reference Image",
                    type="pil",
                    sources=["upload", "clipboard"]
                )
                
                gr.Markdown("### 📝 Prompt")
                prompt_input = gr.Textbox(
                    label="Video Description",
                    placeholder="Describe your video concept in detail...",
                    lines=4,
                    max_length=1000
                )
                
                enhance_btn = gr.Button(
                    "✨ Enhance Prompt with Claude",
                    variant="secondary"
                )
                
                negative_prompt_input = gr.Textbox(
                    label="Negative Prompt (Optional)",
                    placeholder="Things to exclude from the video...",
                    lines=2,
                    max_length=500
                )
                
                gr.Markdown("### 🎯 Preset")
                preset_select = gr.Dropdown(
                    choices=list(PRESETS.keys()),
                    value="🎬 Cinematic",
                    label="Generation Preset",
                    info="Pre-configured quality/speed settings"
                )
            
            # Right column - Advanced controls
            with gr.Column(scale=1):
                gr.Markdown("### ⚙️ Advanced Settings")
                
                duration_slider = gr.Slider(
                    minimum=1,
                    maximum=42,
                    value=10,
                    step=0.5,
                    label="Duration (seconds)"
                )
                
                resolution_select = gr.Dropdown(
                    choices=["512x320", "848x480", "1280x768"],
                    value="848x480",
                    label="Resolution",
                    info="Higher = slower but better quality"
                )
                
                motion_slider = gr.Slider(
                    minimum=0.5,
                    maximum=2.0,
                    value=1.0,
                    step=0.1,
                    label="Motion Scale",
                    info="0.5=subtle, 1.0=normal, 2.0=dynamic"
                )
                
                guidance_slider = gr.Slider(
                    minimum=1.0,
                    maximum=20.0,
                    value=7.5,
                    step=0.5,
                    label="Guidance Scale",
                    info="Higher = more prompt adherence"
                )
                
                seed_input = gr.Number(
                    label="Seed (-1 for random)",
                    value=-1,
                    precision=0
                )
                
                gr.Markdown("### 🎨 Advanced")
                
                keyframes_input = gr.Textbox(
                    label="Timeline Keyframes (JSON, Optional)",
                    placeholder='{"0": "opening", "0.5": "middle", "1": "end"}',
                    lines=2,
                    max_length=500
                )
                
                lora_input = gr.Textbox(
                    label="Custom LoRA Path (Optional)",
                    placeholder="/path/to/lora.safetensors",
                    max_length=200
                )
                
                lora_strength = gr.Slider(
                    minimum=0.0,
                    maximum=1.0,
                    value=0.5,
                    step=0.1,
                    label="LoRA Strength"
                )
                
                audio_checkbox = gr.Checkbox(
                    label="🎵 Generate Audio",
                    value=True
                )
        
        # Generation button
        with gr.Row():
            generate_btn = gr.Button(
                "▶️ GENERATE",
                variant="primary",
                size="lg"
            )
            clear_btn = gr.Button("🔄 Clear", size="lg")
        
        # Output section
        gr.Markdown("### 📹 Results")
        with gr.Row():
            with gr.Column():
                video_output = gr.Video(
                    label="Generated Video",
                    interactive=False
                )
            
            with gr.Column():
                audio_output = gr.Audio(
                    label="Generated Audio",
                    interactive=False,
                    type="filepath"
                )
        
        status_output = gr.Markdown("Ready to generate...")
        
        # Event handlers
        def enhance_prompt(prompt):
            if not prompt:
                return "Please enter a prompt first"
            enhanced = enhance_prompt_with_claude(prompt)
            return enhanced
        
        enhance_btn.click(
            enhance_prompt,
            inputs=[prompt_input],
            outputs=[prompt_input]
        )
        
        def clear_all():
            return None, "", "", "🎬 Cinematic", 10, "848x480", 1.0, 7.5, -1, "", "", 0.5, True, None, None, "Ready to generate..."
        
        clear_btn.click(
            clear_all,
            outputs=[
                image_input, prompt_input, negative_prompt_input,
                preset_select, duration_slider, resolution_select,
                motion_slider, guidance_slider, seed_input,
                keyframes_input, lora_input, lora_strength,
                audio_checkbox, video_output, audio_output,
                status_output
            ]
        )
        
        generate_btn.click(
            generate_video,
            inputs=[
                image_input, prompt_input, negative_prompt_input,
                preset_select, duration_slider, resolution_select,
                motion_slider, guidance_slider, seed_input,
                keyframes_input, lora_input, lora_strength,
                gr.Checkbox(value=False), audio_checkbox
            ],
            outputs=[video_output, status_output, audio_output]
        )
        
        # Footer
        gr.Markdown("""
---
### 📋 Tips
- **Prompts**: Be specific about cinematography, lighting, and mood
- **Resolution**: 512x320 is fast, 1280x768 is highest quality
- **Motion**: Adjust based on desired camera movement intensity
- **Audio**: Automatically synced with video duration

### 🔒 Content Policy
All generations must follow Hugging Face community guidelines. NSFW, violent, and discriminatory content is not permitted.
        """)
    
    return demo

if __name__ == "__main__":
    # Check backend health
    logger.info(f"Checking ComfyUI at {COMFYUI_SERVER}...")
    if not backend.health_check():
        logger.warning("⚠️ ComfyUI backend not responding - some features may not work")
    else:
        logger.info("✅ ComfyUI backend is healthy")
    
    # Create and launch interface
    demo = create_interface()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )
