# 🎬 LTX 2.3 Image-to-Video Generator - Hugging Face Space

A powerful, unlimited image-to-video generation Space powered by LTX 2.3 with native audio generation, advanced prompt enhancement, and professional video controls.

## ✨ Features

### Core Generation
- **Image-to-Video Conversion**: Transform any reference image into stunning videos
- **Native Audio Generation**: Automatically generate audio synchronized with video
- **Professional Presets**: 5 tuned configurations (Cinematic, Smooth Motion, High Quality, Fast, Experimental)
- **Up to 42 seconds**: Generate videos up to ~1000 frames at 24fps

### Advanced Controls
- **Prompt Enhancement**: AI-powered prompt expansion with Claude 3.5 Sonnet
- **Timeline-based Prompts**: Keyframe system for dynamic scene transitions
- **Motion Control**: Adjustable motion scale (0.5x - 2.0x)
- **Guidance Scale**: Fine-tune prompt adherence (1.0 - 20.0)
- **Custom LoRAs**: Apply identity tuning and specialized models

### Quality & Customization
- **Adjustable Resolution**: From 512x320 to 1280x768
- **Negative Prompting**: Exclude unwanted visual elements
- **Seed Control**: Reproducible generations or randomized outputs
- **Multiple Sampling**: DPM++ 2M Karras with Karras scheduler

### No Limits
- **Unlimited Generations**: Generate as much as you want
- **No Token Restrictions**: Full creative freedom
- **Flexible ZeroGPU Budget**: Adjust only if needed

## 🚀 Quick Start

### Deploy to Hugging Face Spaces

1. **Create a new Space**:
   - Go to [huggingface.co/new-space](https://huggingface.co/new-space)
   - Select this repository
   - Choose Docker runtime

2. **Set Environment Variables**:
   ```
   HF_TOKEN=your_huggingface_token
   COMFYUI_SERVER=http://localhost:8188
   ```

3. **Space will auto-launch** with Gradio interface

### Local Development

```bash
git clone https://github.com/Goro888/ltx-2-3-i2v-space.git
cd ltx-2-3-i2v-space

pip install -r requirements.txt
python app.py
```

Then open `http://localhost:7860`

## 📋 User Guide

### Basic Workflow

1. **Upload Image**: Click to upload or drag-drop a reference image
2. **Write Prompt**: Describe your video concept
3. **Enhance** (Optional): Click "✨ Enhance Prompt" to expand into cinematic detail
4. **Choose Preset**: Select from 5 tuned configurations
5. **Adjust Settings** (Optional): Fine-tune resolution, motion, guidance, etc.
6. **Generate**: Click "▶️ GENERATE" and wait for results

### Preset Descriptions

| Preset | Use Case | Quality | Speed |
|--------|----------|---------|-------|
| **Cinematic** | Default, polished look | ⭐⭐⭐⭐ | Medium |
| **Smooth Motion** | Natural movement, transitions | ⭐⭐⭐⭐ | Fast |
| **High Quality** | Maximum detail, 60 steps | ⭐⭐⭐⭐⭐ | Slow |
| **Fast** | Quick previews, 25 steps | ⭐⭐⭐ | Very Fast |
| **Experimental** | Creative, extreme effects | ⭐⭐⭐⭐ | Slow |

### Advanced Features

#### Prompt Relay (Timeline-based Prompts)
Enable to control different scenes throughout the video:

```json
{
  "0": "opening shot of a sunset",
  "0.3": "camera pans left revealing mountains",
  "0.7": "transition to starry night sky",
  "1": "final frame with moonlight"
}
```

#### Custom LoRAs
- **Path**: `/path/to/custom.safetensors`
- **Strength**: 0.0 - 1.0 (0.5 recommended)
- Combine with identity tuning for character consistency

#### Audio Configuration
- **Enabled by Default**: Native audio generation
- **Model**: TTS-1-HD for high quality
- **Voice**: Alloy (customizable)
- Automatically synced with video duration

## 🎯 Tips & Tricks

### For Best Results

1. **Use High-Quality Reference Images**
   - Clear, well-lit, high resolution preferred
   - Aspect ratio ~16:9 works best

2. **Detailed Prompts**
   - Specific: "fast-moving action scene" → "high-speed motorcycle chase through desert at golden hour with dust clouds and dynamic camera movements"
   - Include cinematography: "pan left", "slow zoom", "quick cuts"
   - Mention style: "cinematic", "documentary", "anime", "photorealistic"

3. **Preset Selection**
   - Start with "Cinematic" for general use
   - Use "Smooth Motion" for action/movement
   - Try "High Quality" for hero shots
   - Use "Fast" for rapid iteration/testing

4. **Motion Scale Tuning**
   - **0.5 - 0.8**: Subtle, slow motion
   - **1.0**: Balanced (default)
   - **1.2 - 1.5**: Dynamic, energetic motion

5. **Guidance Scale Tips**
   - **4.0 - 6.0**: More creative freedom, less prompt adherence
   - **7.0 - 9.0**: Balanced (recommended)
   - **10.0 - 15.0**: Strict prompt following
   - **16.0+**: Very rigid, may cause artifacts

## 📊 Specifications

### Model
- **Base Model**: LTX-Video v2.3
- **Quantization**: FP8 Mixed Precision
- **VRAM**: ~14GB (optimized)
- **Framework**: PyTorch + Diffusers

### Video Output
- **Format**: MP4 (H.264)
- **Frame Rate**: 24 fps
- **Max Duration**: ~42 seconds (1000 frames)
- **Resolutions**: 512x320 to 1280x768

### Audio Output
- **Format**: MP3 (AAC)
- **Model**: OpenAI TTS-1-HD
- **Sync**: Automatic frame-perfect sync

## 🔧 ComfyUI Backend Integration

This Space uses ComfyUI for video generation:

```
ComfyUI Server → LTX Checkpoint Loading
    ↓
Text Encoding (CLIP)
    ↓
Image Processing & Scaling
    ↓
LTX Video Sampling
    ↓
VAE Decoding
    ↓
Video & Audio Output
```

To use custom ComfyUI server, set `COMFYUI_SERVER` environment variable.

## 📝 Supported Prompting Techniques

### Style Modifiers
- Cinematic, documentary, anime, photorealistic, stylized
- 35mm film, found footage, slow-motion

### Camera Movements
- Pan left/right, zoom in/out, dolly, crane shot
- Fixed camera, handheld, tracking shot

### Lighting Terms
- Golden hour, blue hour, neon, dramatic shadows
- Volumetric lighting, rim lighting, backlighting

### Motion Descriptors
- Flowing, jerky, smooth, dynamic, energetic
- Slow-motion, time-lapse, fast-paced

## 🤝 Policy Compliance

**ALL GENERATED CONTENT MUST FOLLOW HUGGING FACE POLICY**

This Space enforces:
- ✅ No NSFW content
- ✅ No violent content
- ✅ No discriminatory content
- ✅ No copyrighted material
- ✅ No deepfakes of real people

Generation requests violating policy will be rejected.

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| "Upload image first" | Ensure image is selected before generating |
| Invalid keyframes JSON | Check JSON syntax, use proper quotes |
| Generation timeout | Try shorter duration or reduce resolution |
| Out of memory | Lower resolution or use "Fast" preset |
| No audio in output | Enable "Native Audio Generation" |
| Prompt not followed | Increase guidance scale (7.5 → 10.0) |

## 📚 Resources

- [LTX Video Paper](https://arxiv.org/abs/2404.01204)
- [ComfyUI Documentation](https://github.com/comfyanonymous/ComfyUI)
- [Hugging Face Spaces Docs](https://huggingface.co/docs/hub/spaces)

## 📜 License

Apache 2.0 - Free for research and commercial use with attribution

## 🙏 Credits

- **LTX Model**: Lightricks AI
- **ComfyUI**: Anonymous contributor
- **Gradio**: Hugging Face
- **TTS**: OpenAI Whisper

## 💬 Support

For issues or feature requests, please open an issue on [GitHub](https://github.com/Goro888/ltx-2-3-i2v-space/issues).

---

**Made with ❤️ for creative professionals and enthusiasts**

*Unlimited generations. No restrictions. Pure creativity.*
