#!/usr/bin/env python3
"""
ComfyUI Backend Integration for LTX 2.3 I2V Space
Handles workflow submission, status polling, and result retrieval
"""

import requests
import json
import time
import logging
from typing import Dict, Optional, Tuple, List
from enum import Enum
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GenerationStatus(Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    ERROR = "error"

class ComfyUIBackend:
    def __init__(self, server_url: str = None):
        """Initialize ComfyUI backend connection"""
        self.server_url = server_url or os.getenv("COMFYUI_SERVER", "http://localhost:8188")
        self.timeout = 30
        self.poll_interval = 2
        self.max_retries = 3
        
    def health_check(self) -> bool:
        """Check if ComfyUI server is running"""
        try:
            response = requests.get(
                f"{self.server_url}/system_stats",
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def get_models(self) -> Dict[str, List[str]]:
        """Get available models on ComfyUI server"""
        try:
            response = requests.get(
                f"{self.server_url}/models",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get models: {e}")
            return {}
    
    def upload_image(self, image_path: str, subfolder: str = "input") -> Dict:
        """Upload image to ComfyUI server"""
        try:
            with open(image_path, "rb") as f:
                files = {"image": f}
                data = {"subfolder": subfolder}
                
                response = requests.post(
                    f"{self.server_url}/upload/image",
                    files=files,
                    data=data,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Image upload failed: {e}")
            raise
    
    def submit_workflow(self, workflow: Dict) -> str:
        """Submit workflow to ComfyUI and get prompt_id"""
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    f"{self.server_url}/prompt",
                    json={"prompt": workflow},
                    timeout=self.timeout
                )
                response.raise_for_status()
                result = response.json()
                prompt_id = result.get("prompt_id")
                
                if prompt_id:
                    logger.info(f"Workflow submitted with prompt_id: {prompt_id}")
                    return prompt_id
                else:
                    logger.error(f"No prompt_id in response: {result}")
                    raise ValueError("No prompt_id returned")
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt + 1}/{self.max_retries} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
    
    def get_generation_status(self, prompt_id: str) -> Tuple[GenerationStatus, Optional[Dict]]:
        """Get current status of generation"""
        try:
            response = requests.get(
                f"{self.server_url}/history/{prompt_id}",
                timeout=self.timeout
            )
            response.raise_for_status()
            history = response.json()
            
            if prompt_id not in history:
                return GenerationStatus.QUEUED, None
            
            prompt_history = history[prompt_id]
            
            # Check if generation has outputs
            if "outputs" in prompt_history and prompt_history["outputs"]:
                return GenerationStatus.COMPLETED, prompt_history["outputs"]
            
            # Check for errors
            if "errors" in prompt_history and prompt_history["errors"]:
                logger.error(f"Generation errors: {prompt_history['errors']}")
                return GenerationStatus.FAILED, None
            
            return GenerationStatus.PROCESSING, None
            
        except Exception as e:
            logger.error(f"Status check failed: {e}")
            return GenerationStatus.ERROR, None
    
    def wait_for_completion(
        self,
        prompt_id: str,
        max_wait: int = 600,
        progress_callback=None
    ) -> Tuple[GenerationStatus, Optional[Dict]]:
        """Poll for generation completion with timeout"""
        start_time = time.time()
        last_status = GenerationStatus.QUEUED
        
        while time.time() - start_time < max_wait:
            status, outputs = self.get_generation_status(prompt_id)
            
            if status == GenerationStatus.COMPLETED:
                logger.info(f"Generation completed in {time.time() - start_time:.1f}s")
                return status, outputs
            
            if status == GenerationStatus.FAILED:
                return status, outputs
            
            if status != last_status:
                last_status = status
                elapsed = int(time.time() - start_time)
                progress_text = f"Status: {status.value} ({elapsed}s elapsed)"
                
                if progress_callback:
                    progress_callback(progress_text)
                logger.info(progress_text)
            
            time.sleep(self.poll_interval)
        
        logger.error(f"Generation timeout after {max_wait}s")
        return GenerationStatus.ERROR, None
    
    def extract_video_output(self, outputs: Dict) -> Optional[str]:
        """Extract video file path from generation outputs"""
        try:
            # Look for video in outputs (node 8 by default)
            for node_id, node_output in outputs.items():
                if isinstance(node_output, dict):
                    # Check for video files
                    if "gifs" in node_output and node_output["gifs"]:
                        return node_output["gifs"][0]
                    if "videos" in node_output and node_output["videos"]:
                        return node_output["videos"][0]
            
            return None
        except Exception as e:
            logger.error(f"Failed to extract video output: {e}")
            return None
    
    def extract_audio_output(self, outputs: Dict) -> Optional[str]:
        """Extract audio file path from generation outputs"""
        try:
            for node_id, node_output in outputs.items():
                if isinstance(node_output, dict):
                    if "audio" in node_output and node_output["audio"]:
                        return node_output["audio"][0]
            return None
        except Exception as e:
            logger.error(f"Failed to extract audio output: {e}")
            return None
    
    def download_file(self, filename: str, subfolder: str = "output") -> bytes:
        """Download generated file from ComfyUI"""
        try:
            url = f"{self.server_url}/view"
            params = {"filename": filename, "subfolder": subfolder}
            
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"Download failed for {filename}: {e}")
            raise
    
    def cancel_generation(self, prompt_id: str) -> bool:
        """Cancel an ongoing generation"""
        try:
            response = requests.post(
                f"{self.server_url}/interrupt",
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.info(f"Generation {prompt_id} cancelled")
            return True
        except Exception as e:
            logger.error(f"Cancel failed: {e}")
            return False
    
    def get_queue_status(self) -> Dict:
        """Get current queue status"""
        try:
            response = requests.get(
                f"{self.server_url}/queue",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Queue status check failed: {e}")
            return {"queue_pending": [], "queue_running": []}
    
    def clear_queue(self) -> bool:
        """Clear the generation queue"""
        try:
            response = requests.post(
                f"{self.server_url}/queue",
                json={},
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.info("Queue cleared")
            return True
        except Exception as e:
            logger.error(f"Queue clear failed: {e}")
            return False

class WorkflowBuilder:
    """Helper class to build ComfyUI workflows"""
    
    @staticmethod
    def build_ltx_workflow(
        image_path: str,
        prompt: str,
        negative_prompt: str,
        duration_frames: int,
        seed: int,
        guidance_scale: float = 7.5,
        steps: int = 50,
        sigma_min: float = 0.1,
        sigma_max: float = 14.0,
        motion_scale: float = 1.0,
        width: int = 848,
        height: int = 480,
        lora_name: Optional[str] = None,
        lora_strength: float = 1.0,
    ) -> Dict:
        """Build a complete LTX video generation workflow"""
        
        workflow = {
            "1": {
                "inputs": {"ckpt_name": "LTX-Video-v2.3-fp8-mixed.safetensors"},
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
                "inputs": {"image": image_path},
                "class_type": "LoadImage"
            },
            "5": {
                "inputs": {
                    "images": ["4", 0],
                    "width": width,
                    "height": height,
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
                    "seed": seed,
                    "steps": steps,
                    "cfg": guidance_scale,
                    "sampler_name": "dpmpp_2m_karras",
                    "scheduler": "karras",
                    "denoise": 1.0,
                    "sigma_min": sigma_min,
                    "sigma_max": sigma_max,
                    "motion_scale": motion_scale,
                    "frame_rate": 24,
                    "duration_frames": min(duration_frames, 1000),
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
                    "filename_prefix": f"ltx_video"
                },
                "class_type": "VHS_VideoCombine"
            }
        }
        
        # Add LoRA if specified
        if lora_name:
            workflow["9"] = {
                "inputs": {
                    "lora_name": lora_name,
                    "strength_model": lora_strength,
                    "strength_clip": lora_strength,
                    "model": ["1", 0],
                    "clip": ["1", 1]
                },
                "class_type": "LoraLoader"
            }
            # Update sampler to use LoRA model
            workflow["6"]["inputs"]["model"] = ["9", 0]
        
        return workflow

if __name__ == "__main__":
    # Test backend connectivity
    backend = ComfyUIBackend()
    if backend.health_check():
        print("✅ ComfyUI backend is healthy")
        print(f"Server: {backend.server_url}")
    else:
        print("❌ ComfyUI backend is not responding")
