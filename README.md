# PDF to Video Summary Generator with W&B Weave

Convert any PDF research paper into a 1-minute educational video using AI and mathematical animations, with comprehensive tracking and monitoring powered by **Weights & Biases Weave**.

## 🎬 What it Does

1. **Input**: PDF URL
2. **Process**: AI analyzes the paper and generates animations
3. **Output**: 1-minute summary video
4. **Monitor**: Complete pipeline tracking with W&B Weave

## 🔥 New: W&B Weave Integration

This project now includes comprehensive monitoring and evaluation with **W&B Weave**:

### **📊 Complete Pipeline Tracking**

- **Every function call** tracked from PDF analysis to video generation
- **Performance metrics** for each component (Claude AI, Manim, Voice generation)
- **Success rates** and failure analysis
- **Execution times** and bottleneck identification

### **🔍 LLM Monitoring**

- **Claude AI calls** with input/output tracking
- **Token usage** and cost monitoring
- **Prompt performance** analysis

### **⚡ Video Generation Analytics**

- **Manim success rates** per clip
- **Voice generation performance**
- **End-to-end pipeline health**

### **🎯 Access Your Data**

1. Run the generator (it will automatically track everything)
2. Visit [weave.wandb.ai](https://weave.wandb.ai)
3. Find your project: `manim_video_generator`
4. Explore traces, costs, and performance metrics

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
- **W&B Account**: Free at https://wandb.ai (automatic setup)

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

Enter a PDF URL when prompted. Wait a few minutes. Get your video + complete analytics.

## 📊 Monitoring & Analytics

After running the generator, check your **W&B Weave dashboard** to see:

### **Trace View**

- Complete function call hierarchy
- Input/output for every step
- Execution times and performance

### **Success Metrics**

- Clip generation success rate
- Voice synthesis performance
- Overall pipeline health

### **Cost Tracking**

- Claude AI token usage
- LMNT voice generation costs
- Time-based resource usage

### **Error Analysis**

- Failed clip analysis
- Common failure patterns
- Performance bottlenecks

## 📁 Files

- `video_generator.py` - Main script with Weave tracking
- `config_gen.py` - PDF analysis with Claude AI (tracked)
- `manim_generator.py` - Mathematical animations (tracked)
- `voice_gen.py` - Voice-over generation (tracked)
- `requirements.txt` - Dependencies (includes Weave)
- `env_template.txt` - Environment variables template

## 🎯 Example with Analytics

```
🎬 PDF to Video Summary Generator
========================================
Enter PDF URL: https://example.com/paper.pdf
🚀 Generating 1-minute summary video from: https://example.com/paper.pdf
📄 Processing PDF: https://example.com/paper.pdf
🎬 Generating 4 video clips...
✅ Summary video created: summary_video.mp4
🎉 Done! Video saved as: summary_video.mp4
📊 Success rate: 100.0% (4/4 clips)
```

**Then visit [weave.wandb.ai](https://weave.wandb.ai) to see:**

- Complete execution trace
- Performance metrics
- Cost breakdown
- Success/failure analysis

## 🔧 What You Need

- Python 3.8+
- FFmpeg
- Cairo/Pango (for Manim)
- API keys for Anthropic and LMNT
- W&B account (free)

## 🚀 Advanced Features

### **Custom Evaluation**

Track video quality metrics, generation times, and success rates across different PDF types.

### **Performance Optimization**

Identify bottlenecks in your pipeline and optimize based on Weave analytics.

### **Cost Management**

Monitor LLM usage costs and optimize prompt efficiency.

### **A/B Testing**

Compare different prompts, models, or generation strategies.

That's it. **URL in, video + analytics out.**
