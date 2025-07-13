import asyncio
import subprocess
import os
import tempfile
import json
from typing import List, Dict, Any
from pathlib import Path
import weave

@weave.op()
async def generate_manim_video(code: str, output_dir: str = "output", clip_name: str = None, quality: str = "medium_quality") -> str:
    """
    Generate a video from Manim code asynchronously.
    
    Args:
        code: The Manim Python code to execute
        output_dir: Directory to save the output video
        clip_name: Optional name for the clip file
        quality: Manim quality setting (low_quality, medium_quality, high_quality)
        
    Returns:
        Path to the generated video file
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate a unique filename if not provided
    if not clip_name:
        clip_name = f"clip_{hash(code) % 10000}"
    
    # Validate and clean the code
    if "class SimpleScene" not in code:
        print(f"Warning: Code doesn't contain 'class SimpleScene', attempting to fix...")
        # Try to fix common class name issues
        code = code.replace("class Scene", "class SimpleScene")
        if "class SimpleScene" not in code:
            print(f"Error: Could not fix class name in code")
            return None
    
    # Create temporary Python file with the Manim code
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
        # Always include default imports and ensure clean code
        full_code = "from manim import *\nimport numpy as np\n\n" + code
        temp_file.write(full_code)
        temp_file_path = temp_file.name
        
        # Debug: Print the code being executed
        print(f"Generated Manim code for {clip_name}:")
        print("=" * 50)
        print(full_code)
        print("=" * 50)
    
    try:
        # Run Manim command asynchronously
        quality_flag = {
            "low_quality": "l",
            "medium_quality": "m", 
            "high_quality": "h"
        }.get(quality, "m")
        
        cmd = [
            "manim",
            temp_file_path,
            "SimpleScene",  # Specify the exact scene class to render
            "-o", output_dir,
            "--media_dir", output_dir,
            "-v", "WARNING",  # Reduce verbosity
            f"-q{quality_flag}",  # Quality flag: -ql (low), -qm (medium), -qh (high)
            "--resolution", "1280,720",  # Match Veo's 720p resolution
            "--frame_rate", "24"  # Match Veo's 24fps
        ]
        
        print(f"Running Manim command: {' '.join(cmd)}")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            print(f"Error: Manim execution failed for clip {clip_name}")
            print(f"stdout: {stdout.decode()}")
            print(f"stderr: {stderr.decode()}")
            return None
        
        # Find the generated video file
        video_files = list(Path(output_dir).glob("**/*.mp4"))
        if not video_files:
            print(f"Error: No video file was generated for clip {clip_name}")
            return None
        
        # Filter out partial files and find the most recent
        final_videos = [f for f in video_files if "partial" not in str(f)]
        if not final_videos:
            print(f"Warning: No final video file found for clip {clip_name}, using latest available")
            final_videos = video_files
        
        # Return the most recently created video file
        latest_video = max(final_videos, key=os.path.getctime)
        print(f"✓ Generated Manim video: {latest_video}")
        return str(latest_video)
        
    except Exception as e:
        print(f"Exception during Manim generation: {e}")
        return None
    finally:
        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

@weave.op()
async def generate_manim_clips(clips_config: List[Dict[str, Any]], output_dir: str = "clips", quality: str = "medium_quality") -> List[str]:
    """
    Generate multiple Manim clips sequentially (to avoid resource conflicts).
    
    Args:
        clips_config: List of clip configurations with 'code' and optional 'voice_over'
        output_dir: Directory to save output videos
        quality: Manim quality setting (low_quality, medium_quality, high_quality)
        
    Returns:
        List of paths to generated video files
    """
    manim_clips = [clip for clip in clips_config if clip.get('type') == 'manim' and clip.get('code')]
    
    video_paths = []
    
    for i, clip in enumerate(manim_clips):
        clip_name = f"manim_clip_{i:03d}"
        print(f"Generating clip {i+1}/{len(manim_clips)}: {clip_name}")
        
        try:
            video_path = await generate_manim_video(clip['code'], output_dir, clip_name, quality)
            if video_path:
                video_paths.append(video_path)
                print(f"✓ Successfully generated clip {i+1}")
            else:
                print(f"✗ Failed to generate clip {i+1}")
        except Exception as e:
            print(f"✗ Error generating clip {i+1}: {e}")
    
    return video_paths

async def main():
    """Example usage"""
    # Example clip configuration
    sample_clips = [
        {
            "type": "manim",
            "code": """
class SimpleScene(Scene):
    def construct(self):
        # Create a simple mathematical visualization
        title = Text("Mathematical Visualization", font_size=48)
        title.to_edge(UP)
        
        # Create a circle and square
        circle = Circle(radius=2, color=BLUE)
        square = Square(side_length=3, color=RED)
        
        # Animation sequence
        self.play(Write(title))
        self.play(Create(circle))
        self.play(Transform(circle, square))
        self.wait(1)
        self.play(FadeOut(title), FadeOut(circle))
""",
            "voice_over": "Welcome to our mathematical visualization. Here we see the transformation of geometric shapes."
        }
    ]
    
    video_paths = await generate_manim_clips(sample_clips)
    print(f"Generated videos: {video_paths}")

if __name__ == "__main__":
    asyncio.run(main()) 