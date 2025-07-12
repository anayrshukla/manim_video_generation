import anthropic
import os
import dotenv
import base64
import httpx
import weave

# Load environment variables from .env file
dotenv.load_dotenv()

API_KEY = os.getenv("ANTHROPIC_API_KEY", "your_api_key_here")

client = anthropic.Anthropic(
    api_key=API_KEY
)

prompt = """You are an expert educational content creator like 3Blue1Brown. 
From this research paper, generate a JSON object for a 45-60 second educational video that breaks down the key concepts step by step.

Create exactly 4-5 clips that together form a complete mini-lesson:

TIMING & STRUCTURE:
- Total duration: 45-60 seconds
- Clip 1 (10-12s): Introduction/Hook - What problem does this solve?
- Clip 2 (10-12s): Core Concept - The main idea explained simply
- Clip 3 (10-12s): How It Works - The mechanism/process
- Clip 4 (10-12s): Impact/Results - Why it matters
- Clip 5 (optional, 5-8s): Quick summary/takeaway

EDUCATIONAL REQUIREMENTS:
- Start with a hook that grabs attention
- Build concepts progressively (simple → complex)
- Use analogies and visual metaphors
- End with clear impact/significance
- Make it accessible but not dumbed down

TECHNICAL CONSTRAINTS:
- Only use basic Manim objects: Circle, Square, Rectangle, Line, Arrow, Dot, Text
- DO NOT use SVGMobject, DecimalNumber, or LaTeX-dependent objects
- DO NOT reference external files (.svg, .png, .jpg)
- Use built-in colors: RED, BLUE, GREEN, YELLOW, WHITE, ORANGE, PURPLE
- Keep animations smooth and purposeful

VOICE-OVER STYLE:
- Conversational but authoritative
- Clear, concise explanations
- Natural pacing with pauses
- Connect each clip to the next

Example structure:
Clip 1: "Imagine you're trying to [relatable problem]..."
Clip 2: "Here's the key insight: [main concept]..."
Clip 3: "The way this works is [mechanism]..."
Clip 4: "This breakthrough means [impact]..."

Return ONLY this JSON (no other text):
{
    "clips": [
        {
            "type": "manim",
            "code": "class SceneN(Scene):\n    def construct(self):\n        # 10-12 second animation",
            "voice_over": "Educational narration that flows naturally"
        }
    ]
}
"""

@weave.op()
def generate_video_config(pdf_path, use_base64=False):
    """Generate video configuration from PDF using Claude AI"""
    
    if use_base64:
        # Load PDF from URL and encode as base64
        if pdf_path.startswith('http'):
            pdf_data = base64.standard_b64encode(httpx.get(pdf_path).content).decode("utf-8")
        else:
            # Load from local file
            with open(pdf_path, "rb") as f:
                pdf_data = base64.standard_b64encode(f.read()).decode("utf-8")
        
        document_content = {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": pdf_data
            }
        }
    else:
        # Use URL method
        document_content = {
            "type": "document",
            "source": {
                "type": "url",
                "url": pdf_path
            }
        }
    
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=8192,
        messages=[
            {
                "role": "user", 
                "content": [
                    document_content,
                    {
                        "type": "text",
                        "text": prompt,
                    }
                ]
            },
        ]
    )

    return message

if __name__ == "__main__":
    # Example usage
    pdf_path = "./sample_paper.pdf"
    response = generate_video_config(pdf_path, use_base64=True)
    print(response.content[0].text)

    # Save to file
    with open("manim_video_config.json", "w") as f:
        f.write(response.content[0].text) 