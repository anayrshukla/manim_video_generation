import os
import asyncio
import ssl
import certifi
import aiohttp
from dotenv import load_dotenv
from lmnt.api import Speech

# Load environment variables
load_dotenv()

LMNT_API_KEY = os.getenv("LMNT_API_KEY")

async def generate_voice(text: str, output_path: str, voice_id: str = "brandon", format: str = "wav") -> str:
    """
    Generate voice audio from text using LMNT API.
    
    Args:
        text: Text to convert to speech
        output_path: Path where the audio file will be saved
        voice_id: Voice ID to use for generation (default: "brandon")
        format: Audio format (mp3, wav, aac)
        
    Returns:
        Path to the generated audio file
    """
    if not LMNT_API_KEY:
        raise ValueError("LMNT_API_KEY not found in environment variables")
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    
    print(f"Generating voice for: {text[:50]}...")
    print(f"Using voice: {voice_id}")
    print(f"Output path: {output_path}")
    
    try:
        # Try using proper SSL context with certifi
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        
        # Create aiohttp connector with SSL context
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        async with Speech(LMNT_API_KEY, connector=connector) as speech:
            # Synthesize the text
            synthesis = await speech.synthesize(
                text=text,
                voice=voice_id,
                format=format,
                sample_rate=24000
            )
            
            # Save the audio to file
            with open(output_path, 'wb') as f:
                f.write(synthesis['audio'])
            
            print(f"✓ Voice generated successfully: {output_path}")
            return output_path
            
    except Exception as e:
        print(f"SSL method failed: {e}")
        # Fallback: disable SSL verification entirely
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            
            async with Speech(LMNT_API_KEY, connector=connector) as speech:
                synthesis = await speech.synthesize(
                    text=text,
                    voice=voice_id,
                    format=format,
                    sample_rate=24000
                )
                
                with open(output_path, 'wb') as f:
                    f.write(synthesis['audio'])
                
                print(f"✓ Voice generated successfully (insecure): {output_path}")
                return output_path
                
        except Exception as e2:
            print(f"✗ Error generating voice: {e2}")
            return None

async def list_available_voices():
    """
    List all available voices from LMNT API.
    
    Returns:
        List of voice metadata objects
    """
    if not LMNT_API_KEY:
        raise ValueError("LMNT_API_KEY not found in environment variables")
    
    async with Speech(LMNT_API_KEY) as speech:
        voices = await speech.list_voices()
        return voices

async def get_voice_info(voice_id: str):
    """
    Get information about a specific voice.
    
    Args:
        voice_id: The ID of the voice to get info for
        
    Returns:
        Voice metadata object
    """
    if not LMNT_API_KEY:
        raise ValueError("LMNT_API_KEY not found in environment variables")
    
    async with Speech(LMNT_API_KEY) as speech:
        voice_info = await speech.voice_info(voice_id)
        return voice_info

async def main():
    """Example usage and testing"""
    try:
        # List available voices
        print("Available voices:")
        voices = await list_available_voices()
        for voice in voices[:5]:  # Show first 5 voices
            print(f"- {voice['name']} ({voice['id']}) - {voice.get('description', 'No description')}")
        
        # Generate a test voice
        text = "Hello, this is a test of the LMNT voice generation system for educational videos. The quick brown fox jumps over the lazy dog."
        output_path = "test_voice.wav"
        
        result = await generate_voice(text, output_path, voice_id="brandon")
        if result:
            print(f"✓ Voice generated: {result}")
        else:
            print("✗ Voice generation failed")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 