import asyncio
import os
import json
from pathlib import Path
import warnings
import weave

# MoviePy imports
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips, ImageClip

# Local imports
from config_gen import generate_video_config
from manim_generator import generate_manim_clips
from voice_gen import generate_voice
from veo_gen import generate_veo_thank_you_clip


@weave.op()
def combine_video_with_audio_sync(video_path: str, audio_path: str, output_path: str) -> str:
    """Combine video with audio using MoviePy."""
    try:
        video = VideoFileClip(video_path)
        audio = AudioFileClip(audio_path)
        
        # If audio is longer than video, extend video
        if audio.duration > video.duration:
            extra_duration = audio.duration - video.duration
            last_frame = video.get_frame(video.duration - 0.01)
            still_clip = ImageClip(last_frame, duration=(extra_duration + 0.1))
            extended_video = concatenate_videoclips([video, still_clip])
            final_video = extended_video.with_audio(audio)
        else:
            final_video = video.with_audio(audio)
        
        final_video.write_videofile(output_path, logger=None)
        
        # Clean up
        video.close()
        audio.close()
        final_video.close()
        if 'extended_video' in locals():
            extended_video.close()
        
        return output_path
    except Exception as e:
        print(f"Error combining video and audio: {e}")
        return video_path


@weave.op()
def normalize_video_clip(clip, target_fps: int = 24, target_resolution: tuple = (1280, 720)) -> VideoFileClip:
    """
    Normalize video clip to consistent format for stitching.
    
    Args:
        clip: VideoFileClip to normalize
        target_fps: Target frame rate (Veo uses 24fps)
        target_resolution: Target resolution (width, height) - Veo uses 720p
    
    Returns:
        Normalized VideoFileClip
    """
    try:
        # Get current dimensions
        current_w, current_h = clip.size
        target_w, target_h = target_resolution
        
        # Resize if needed (maintain aspect ratio)
        if (current_w, current_h) != (target_w, target_h):
            print(f"📐 Resizing clip from {current_w}x{current_h} to {target_w}x{target_h}")
            clip = clip.resized(newsize=(target_w, target_h))
        
        # Adjust frame rate if needed
        if abs(clip.fps - target_fps) > 0.1:  # Small tolerance for floating point
            print(f"🎬 Adjusting frame rate from {clip.fps}fps to {target_fps}fps")
            clip = clip.with_fps(target_fps)
        
        return clip
        
    except Exception as e:
        print(f"⚠️  Warning: Could not normalize clip - {e}")
        return clip

@weave.op()
def stitch_videos(video_paths: list, output_path: str = "summary_video.mp4", add_thank_you: bool = True) -> str:
    """Stitch multiple video files together with optional Veo 'Thank You' ending."""
    try:
        clips = []
        print("🔧 Loading and normalizing video clips...")
        
        for i, path in enumerate(video_paths):
            if os.path.exists(path):
                print(f"📹 Processing clip {i+1}/{len(video_paths)}: {os.path.basename(path)}")
                clip = VideoFileClip(path)
                
                # Normalize each clip to ensure consistent format
                normalized_clip = normalize_video_clip(clip)
                clips.append(normalized_clip)
                
                # Close original clip to free memory
                if normalized_clip != clip:
                    clip.close()
        
        if not clips:
            raise ValueError("No valid video clips found")
        
        # Add Veo "Thank You" clip at the end
        if add_thank_you:
            print("🎬 Adding Veo 'Thank You' clip to the end...")
            try:
                thank_you_path = "clips/thank_you_veo.mp4"
                veo_clip_path = generate_veo_thank_you_clip(thank_you_path)
                
                if veo_clip_path and os.path.exists(veo_clip_path):
                    print("📹 Processing Veo 'Thank You' clip...")
                    thank_you_clip = VideoFileClip(veo_clip_path)
                    
                    # Normalize the Veo clip to match other clips
                    normalized_thank_you = normalize_video_clip(thank_you_clip)
                    clips.append(normalized_thank_you)
                    
                    # Close original if different
                    if normalized_thank_you != thank_you_clip:
                        thank_you_clip.close()
                    
                    print("✅ Veo 'Thank You' clip added and normalized!")
                else:
                    print("⚠️  Veo clip generation failed, continuing without thank you")
                    
            except Exception as e:
                print(f"⚠️  Could not add Veo thank you clip: {e}")
        
        # Concatenate all clips (main content + thank you)
        final_clip = concatenate_videoclips(clips, method="chain")
        final_clip.write_videofile(output_path, logger=None)
        
        # Clean up
        final_clip.close()
        for clip in clips:
            clip.close()
        
        return output_path
    except Exception as e:
        print(f"Error stitching videos: {e}")
        raise


@weave.op()
async def generate_summary_video_upload(pdf_path: str) -> dict:
    """Generate a 1-minute summary video from an uploaded PDF file."""
    print(f"📄 Processing uploaded PDF: {pdf_path}")
    
    # Generate video config from PDF using base64 encoding
    response = generate_video_config(pdf_path, use_base64=True)
    config_text = response.content[0].text
    
    # Parse JSON config
    try:
        config = json.loads(config_text)
    except json.JSONDecodeError:
        import re
        json_match = re.search(r'\{.*\}', config_text, re.DOTALL)
        if json_match:
            config = json.loads(json_match.group())
        else:
            raise ValueError("Could not parse video configuration")
    
    clips = config.get("clips", [])
    if not clips:
        raise ValueError("No clips generated from PDF")
    
    # Limit to ~1 minute (take first few clips)
    max_clips = min(len(clips), 4)  # Roughly 4 clips for 1 minute
    clips = clips[:max_clips]
    
    print(f"🎬 Generating {len(clips)} video clips...")
    
    # Generate Manim videos
    output_dir = "clips"
    os.makedirs(output_dir, exist_ok=True)
    
    video_paths = await generate_manim_clips(clips, output_dir, "medium_quality")
    
    # Track video generation metrics
    successful_clips = 0
    failed_clips = 0
    
    # Add voice-over to each clip (with fallback to silent video)
    final_clips = []
    for i, (clip_config, video_path) in enumerate(zip(clips, video_paths)):
        if video_path:
            # Try to generate voice-over, but continue if it fails
            try:
                if clip_config.get('voice_over'):
                    audio_path = f"{output_dir}/audio_{i}.wav"
                    audio_result = await generate_voice(clip_config['voice_over'], audio_path)
                    
                    if audio_result and os.path.exists(audio_result):
                        final_path = f"{output_dir}/final_{i}.mp4"
                        combined_path = combine_video_with_audio_sync(video_path, audio_path, final_path)
                        final_clips.append(combined_path)
                        successful_clips += 1
                        print(f"✓ Clip {i+1} with voice-over")
                    else:
                        final_clips.append(video_path)
                        successful_clips += 1
                        print(f"✓ Clip {i+1} (silent - voice failed)")
                else:
                    final_clips.append(video_path)
                    successful_clips += 1
                    print(f"✓ Clip {i+1} (silent)")
            except Exception as e:
                print(f"Voice generation failed for clip {i+1}: {e}")
                final_clips.append(video_path)
                successful_clips += 1
                print(f"✓ Clip {i+1} (silent - voice failed)")
        else:
            failed_clips += 1
            print(f"✗ Clip {i+1} failed to generate")
    
    if not final_clips:
        raise ValueError("No clips were successfully generated")
    
    # Stitch all clips together
    final_video = stitch_videos(final_clips, "summary_video.mp4")
    
    print(f"✅ Summary video created: {final_video}")
    
    # Return comprehensive results for Weave tracking
    return {
        "video_path": final_video,
        "total_clips": len(clips),
        "successful_clips": successful_clips,
        "failed_clips": failed_clips,
        "success_rate": successful_clips / len(clips) if clips else 0,
        "pdf_path": pdf_path,
        "clips_config": clips
    }


@weave.op()
async def generate_summary_video(pdf_url: str) -> dict:
    """Generate a 1-minute summary video from a PDF URL."""
    print(f"📄 Processing PDF: {pdf_url}")
    
    # Generate video config from PDF
    response = generate_video_config(pdf_url, use_base64=False)
    config_text = response.content[0].text
    
    # Parse JSON config
    try:
        config = json.loads(config_text)
    except json.JSONDecodeError:
        import re
        json_match = re.search(r'\{.*\}', config_text, re.DOTALL)
        if json_match:
            config = json.loads(json_match.group())
        else:
            raise ValueError("Could not parse video configuration")
    
    clips = config.get("clips", [])
    if not clips:
        raise ValueError("No clips generated from PDF")
    
    # Limit to ~1 minute (take first few clips)
    max_clips = min(len(clips), 4)  # Roughly 4 clips for 1 minute
    clips = clips[:max_clips]
    
    print(f"🎬 Generating {len(clips)} video clips...")
    
    # Generate Manim videos
    output_dir = "clips"
    os.makedirs(output_dir, exist_ok=True)
    
    video_paths = await generate_manim_clips(clips, output_dir, "medium_quality")
    
    # Track video generation metrics
    successful_clips = 0
    failed_clips = 0
    
    # Add voice-over to each clip (with fallback to silent video)
    final_clips = []
    for i, (clip_config, video_path) in enumerate(zip(clips, video_paths)):
        if video_path:
            # Try to generate voice-over, but continue if it fails
            try:
                if clip_config.get('voice_over'):
                    audio_path = f"{output_dir}/audio_{i}.wav"
                    audio_result = await generate_voice(clip_config['voice_over'], audio_path)
                    
                    if audio_result and os.path.exists(audio_result):
                        final_path = f"{output_dir}/final_{i}.mp4"
                        combined_path = combine_video_with_audio_sync(video_path, audio_path, final_path)
                        final_clips.append(combined_path)
                        successful_clips += 1
                        print(f"✓ Clip {i+1} with voice-over")
                    else:
                        final_clips.append(video_path)
                        successful_clips += 1
                        print(f"✓ Clip {i+1} (silent - voice failed)")
                else:
                    final_clips.append(video_path)
                    successful_clips += 1
                    print(f"✓ Clip {i+1} (silent)")
            except Exception as e:
                print(f"Voice generation failed for clip {i+1}: {e}")
                final_clips.append(video_path)
                successful_clips += 1
                print(f"✓ Clip {i+1} (silent - voice failed)")
        else:
            failed_clips += 1
            print(f"✗ Clip {i+1} failed to generate")
    
    if not final_clips:
        raise ValueError("No clips were successfully generated")
    
    # Stitch all clips together
    final_video = stitch_videos(final_clips, "summary_video.mp4")
    
    print(f"✅ Summary video created: {final_video}")
    
    # Return comprehensive results for Weave tracking
    return {
        "video_path": final_video,
        "total_clips": len(clips),
        "successful_clips": successful_clips,
        "failed_clips": failed_clips,
        "success_rate": successful_clips / len(clips) if clips else 0,
        "pdf_url": pdf_url,
        "clips_config": clips
    }


def main():
    """Simple main function - just ask for URL and generate video."""
    # Initialize Weave tracking (with fallback)
    try:
        weave.init("manim_video_generator")
        print("✅ W&B Weave tracking initialized")
    except Exception as e:
        print(f"⚠️  W&B Weave not available: {e}")
        print("📊 Running without tracking")
    
    print("🎬 PDF to Video Summary Generator")
    print("=" * 40)
    
    # Get PDF URL
    pdf_url = input("Enter PDF URL: ").strip()
    
    if not pdf_url:
        print("❌ No URL provided")
        return
    
    if not pdf_url.startswith(('http://', 'https://')):
        print("❌ Please provide a valid URL")
        return
    
    print(f"🚀 Generating 1-minute summary video from: {pdf_url}")
    
    try:
        # Generate the video with full tracking
        result = asyncio.run(generate_summary_video(pdf_url))
        
        print(f"🎉 Done! Video saved as: {result['video_path']}")
        print(f"📁 Full path: {os.path.abspath(result['video_path'])}")
        print(f"📊 Success rate: {result['success_rate']:.1%} ({result['successful_clips']}/{result['total_clips']} clips)")
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main() 