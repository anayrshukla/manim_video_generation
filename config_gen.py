import anthropic
import os
import dotenv
import base64
import httpx
# Load environment variables from .env file
dotenv.load_dotenv()

API_KEY = os.getenv("ANTHROPIC_API_KEY", "your_api_key_here")

client = anthropic.Anthropic(
    api_key=API_KEY
)

prompt = """Imagine you are 3 Blue 1 Brown himself, an incredible teacher and instructor.
From this research paper, generate a JSON object for an educational video that is a list of clips.
Each clip should be of type "manim" with Python code to generate educational animations using Manim.

CRITICAL REQUIREMENTS:
- Only use basic Manim objects: Circle, Square, Rectangle, Line, Arrow, Dot, Text
- DO NOT use SVGMobject, DecimalNumber, or any LaTeX-dependent objects
- DO NOT reference external files like .svg, .png, .jpg
- Keep animations simple and clean
- Use only built-in Manim colors like RED, BLUE, GREEN, YELLOW, WHITE
- Each clip should be 10-15 seconds long
- Focus on key concepts from the paper using simple geometric visualizations

Example of GOOD code:
```python
class ExampleScene(Scene):
    def construct(self):
        title = Text("Research Title", font_size=48)
        circle = Circle(radius=2, color=BLUE)
        self.play(Write(title))
        self.play(Create(circle))
        self.wait(2)
```

Example of BAD code (DO NOT USE):
```python
# DON'T USE: SVGMobject('robot.svg')
# DON'T USE: DecimalNumber(0)
# DON'T USE: MathTex("\\frac{1}{2}")
```

Simply return the JSON object of this schema (no other text, no code blocks):
{
    "clips": [
        {
            "type": "manim",
            "code": "string",
            "voice_over": "string"
        }
    ]
}
"""

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