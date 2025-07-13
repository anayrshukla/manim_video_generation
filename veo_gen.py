import requests
import os
import time
import json
import weave
from pathlib import Path

@weave.op()
def generate_veo_thank_you_clip(output_path: str = "thank_you_clip.mp4") -> str:
    """
    Generate a 3-4 second thank you visualization clip using Google Veo API.
    Creates an engaging visual ending for the video.
    
    Args:
        output_path: Path where the generated video will be saved
        
    Returns:
        Path to the generated video file
    """
    
    # Try Google Veo API (official)
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if google_api_key and google_api_key != "your_google_api_key_here":
        print("🌟 Using Google Veo API for thank you visualization...")
        result = generate_veo_gemini_thank_you_clip(output_path)
        if result:
            return result
        print("⚠️  Google Veo failed, using Manim fallback...")
    else:
        print("🔑 No Google API key found, using Manim fallback...")
    
    # Fallback to Manim-generated thank you
    return create_fallback_thank_you_clip(output_path)

@weave.op()
def create_fallback_thank_you_clip(output_path: str) -> str:
    """
    Create a simple thank you clip using Manim as fallback if Veo fails.
    """
    try:
        print("🔄 Creating fallback thank you clip with Manim...")
        
        fallback_code = f'''
from manim import *

class SimpleScene(Scene):
    def construct(self):
        # Create thank you title
        title = Text("Thank You", font_size=48, color=WHITE)
        title.to_edge(UP)
        
        # Create subtitle
        subtitle = Text("For Watching", font_size=36, color=BLUE)
        subtitle.move_to(ORIGIN)
        
        # Add visual elements
        circle = Circle(radius=1.5, color=BLUE, fill_opacity=0.1)
        circle.move_to(ORIGIN)
        
        # Animate the thank you (exactly 3.5 seconds total)
        self.play(Write(title, run_time=0.8))
        self.wait(0.2)
        
        self.play(
            Create(circle, run_time=1),
            FadeIn(subtitle, run_time=1)
        )
        self.wait(1)
        
        # Quick fade transition
        self.play(
            FadeOut(title, run_time=0.25),
            FadeOut(subtitle, run_time=0.25),
            FadeOut(circle, run_time=0.25)
        )
'''
        
        # Generate using our existing Manim infrastructure
        import tempfile
        import subprocess
        
        # Create temporary Python file with the Manim code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            # Always include default imports
            full_code = "from manim import *\nimport numpy as np\n\n" + fallback_code
            temp_file.write(full_code)
            temp_file_path = temp_file.name
        
        try:
            # Run Manim command directly
            output_dir = os.path.dirname(output_path) or "clips"
            os.makedirs(output_dir, exist_ok=True)
            
            cmd = [
                "manim",
                temp_file_path,
                "SimpleScene",
                "-o", output_dir,
                "--media_dir", output_dir,
                "-v", "WARNING",
                "-qm",  # medium quality
                "--resolution", "1280,720",
                "--frame_rate", "24"
            ]
            
            print(f"🔄 Running fallback Manim command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Find the generated video file
                from pathlib import Path
                video_files = list(Path(output_dir).glob("**/*.mp4"))
                final_videos = [f for f in video_files if "partial" not in str(f)]
                
                if final_videos:
                    fallback_path = str(max(final_videos, key=os.path.getctime))
                else:
                    fallback_path = None
            else:
                print(f"❌ Manim fallback failed: {result.stderr}")
                fallback_path = None
                
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        
        if fallback_path and os.path.exists(fallback_path):
            # Move to the expected output path
            os.rename(fallback_path, output_path)
            print(f"✅ Fallback thank you clip created: {output_path}")
            return output_path
        else:
            print("❌ Fallback clip generation failed")
            return None
            
    except Exception as e:
        print(f"❌ Fallback generation error: {e}")
        return None

# Alternative: Google Gemini API approach (premium but official)
@weave.op()
def generate_veo_gemini_thank_you_clip(output_path: str = "thank_you_clip.mp4") -> str:
    """
    Generate thank you visualization clip using official Google Gemini API.
    Creates an engaging visual ending for the video.
    """
    try:
        print("🔄 Importing Google Gen AI SDK...")
        # This requires: pip install google-genai
        from google import genai
        from google.genai import types
        import time
        
        print("🔧 Initializing Google Veo client...")
        # Initialize client (automatically uses GOOGLE_API_KEY environment variable)
        client = genai.Client()
        
        # Create thank you prompts
        def create_thank_you_prompts():
            """Generate engaging visual prompts for thank you ending"""
            
            thank_you_prompts = [
                "Elegant thank you message with flowing particles and gentle animations, professional academic style, exactly 3 seconds duration",
                "Abstract thank you visualization with geometric shapes forming a thank you message, clean modern aesthetic, exactly 3 seconds duration",
                "Thank you text with subtle background animation and soft lighting effects, professional presentation style, exactly 3 seconds duration",
                "Minimalist thank you design with animated typography and smooth transitions, elegant academic finish, exactly 3 seconds duration"
            ]
            
            return thank_you_prompts
        
        import random
        thank_you_prompts = create_thank_you_prompts()
        prompt = random.choice(thank_you_prompts)
        
        print(f"📝 Using prompt: {prompt}")
        
        print("🚀 Starting Google Veo generation...")
        operation = client.models.generate_videos(
            model="veo-2.0-generate-001",
            prompt="Generate exactly 3 seconds of video for a thank you ending with the following prompt: " + prompt,
            config=types.GenerateVideosConfig(
                aspect_ratio="16:9",
                person_generation="dont_allow"
            ),
        )
        
        print(f"⏳ Operation started: {operation.name}")
        
        # Wait for generation to complete with timeout
        max_wait_time = 300  # 5 minutes timeout
        start_time = time.time()
        
        print("🎬 Generating with Google Veo (official API)...")
        while not operation.done:
            elapsed = time.time() - start_time
            if elapsed > max_wait_time:
                print(f"⏰ Timeout after {max_wait_time} seconds")
                return None
                
            print(f"⏳ Waiting... {elapsed:.0f}s elapsed")
            time.sleep(15)
            try:
                operation = client.operations.get(operation)
            except Exception as e:
                print(f"❌ Error checking operation status: {e}")
                return None
        
        print("✅ Generation completed!")
        
        # Save the generated video
        if operation.response and hasattr(operation.response, 'generated_videos') and operation.response.generated_videos:
            print(f"📹 Found {len(operation.response.generated_videos)} generated videos")
            
            for n, generated_video in enumerate(operation.response.generated_videos):
                try:
                    print(f"📥 Downloading video {n+1}...")
                    
                    # Create output directory
                    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
                    
                    # Download and save the video
                    client.files.download(file=generated_video.video)
                    generated_video.video.save(output_path)
                    
                    # Verify file was created and has content
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                        print(f"✅ Google Veo clip generated successfully: {output_path}")
                        return output_path
                    else:
                        print(f"❌ Generated file is empty or doesn't exist")
                        
                except Exception as e:
                    print(f"❌ Error downloading/saving video {n+1}: {e}")
                    
        else:
            print("❌ No videos in response")
            if hasattr(operation, 'response'):
                print(f"📄 Response: {operation.response}")
        
        return None
        
    except ImportError:
        print("❌ Google Gen AI SDK not installed. Run: pip install google-genai")
        return None
    except Exception as e:
        print(f"❌ Google Veo API error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # Test the function
    test_path = "test_thank_you.mp4"
    result = generate_veo_thank_you_clip(test_path)
    if result:
        print(f"✅ Test successful: {result}")
    else:
        print("❌ Test failed") 