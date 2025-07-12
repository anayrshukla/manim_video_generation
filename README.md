# PDF to Video Summary Generator

Convert any PDF research paper into a 1-minute educational video using AI and mathematical animations.

## 🎬 What it Does

1. **Input**: PDF URL
2. **Process**: AI analyzes the paper and generates animations
3. **Output**: 1-minute summary video

That's it. Simple.

## 🛠️ Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up API Keys

```bash
cp env_template.txt .env
# Edit .env with your API keys
```

**Required API Keys:**

- **Anthropic API Key**: Get from https://console.anthropic.com/
- **LMNT API Key**: Get from https://app.lmnt.com/

### 3. Install System Dependencies

**macOS:**

```bash
brew install ffmpeg cairo pango
```

**Linux:**

```bash
sudo apt install ffmpeg libcairo2-dev libpango1.0-dev
```

## 🚀 Usage

```bash
python video_generator.py
```

Enter a PDF URL when prompted. Wait a few minutes. Get your video.

## 📁 Files

- `video_generator.py` - Main script
- `config_gen.py` - PDF analysis with Claude AI
- `manim_generator.py` - Mathematical animations
- `voice_gen.py` - Voice-over generation
- `requirements.txt` - Dependencies
- `env_template.txt` - Environment variables template

## 🎯 Example

```
🎬 PDF to Video Summary Generator
========================================
Enter PDF URL: https://example.com/paper.pdf
🚀 Generating 1-minute summary video from: https://example.com/paper.pdf
📄 Processing PDF: https://example.com/paper.pdf
🎬 Generating 4 video clips...
✅ Summary video created: summary_video.mp4
🎉 Done! Video saved as: summary_video.mp4
```

## 🔧 What You Need

- Python 3.8+
- FFmpeg
- Cairo/Pango (for Manim)
- API keys for Anthropic and LMNT

That's it. No complicated setup, no multiple modes, no extra features. URL in, video out.
