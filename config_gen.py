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

prompt = """You are creating a simple, clean educational video from this research paper. 
Generate a JSON for a 45-60 second video with exactly 4 clips that are visually clean and easy to follow.

CRITICAL LAYOUT RULES:
- Title text always goes at the TOP (y=2.5 to 3)
- Main content in CENTER (y=-0.5 to 1.5)  
- Simple shapes ONLY in the center, never overlapping text
- Keep animations MINIMAL and SMOOTH
- Use clear spacing between elements

CLIP STRUCTURE (exactly 4 clips):
1. Introduction (12s): Present the problem/topic
2. Core Concept (12s): Main idea with simple visual
3. Key Mechanism (12s): How it works (basic shapes/arrows)
4. Impact/Result (12s): Why it matters

VISUAL DESIGN CONSTRAINTS:
- Only use: Circle, Square, Rectangle, Text, Arrow, Line, Dot
- Colors: BLUE, RED, GREEN, YELLOW, WHITE (pick 2-3 max per clip)
- NO complex animations - just FadeIn, FadeOut, Create, Write
- NO moving text - text stays in position once placed
- Simple geometric shapes only - no complex drawings
- Clear visual hierarchy: title → content → simple illustration

CODE TEMPLATE TO FOLLOW:
```python
class SimpleScene(Scene):
    def construct(self):
        # Title at top (never moves)
        title = Text("Clear Title Here", font_size=48).to_edge(UP)
        self.play(Write(title))
        self.wait(1)
        
        # Simple visual in center (basic shapes only)  
        shape = Circle(radius=1, color=BLUE).move_to(ORIGIN)
        self.play(Create(shape))
        self.wait(2)
        
        # Optional simple text below center
        subtitle = Text("Key point", font_size=36).shift(DOWN*2)
        self.play(FadeIn(subtitle))
        self.wait(3)
        
        # Always end with this
        self.wait(1)
```

CRITICAL CODE REQUIREMENTS:
- Class name must be exactly "SimpleScene"
- Always start with a title using Text().to_edge(UP)
- Use self.wait() between animations (minimum 1 second)
- Maximum 3 objects per scene (title + 2 others)
- Keep total animation time to exactly 12 seconds
- End every scene with self.wait(1)

VOICE-OVER STYLE:
- Conversational and clear
- Match the visual timing
- 2-3 sentences per clip maximum
- Natural pacing with pauses

Return ONLY this JSON (no markdown, no explanation):
{
    "clips": [
        {
            "type": "manim", 
            "code": "class SimpleScene(Scene):\n    def construct(self):\n        # Simple, clean animation following the template exactly\n        title = Text('Topic Title', font_size=48).to_edge(UP)\n        self.play(Write(title))\n        self.wait(1)\n        # Add 1-2 more simple elements here\n        self.wait(1)",
            "voice_over": "Clear, concise narration matching the 12-second timing"
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