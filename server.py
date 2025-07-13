from fastapi import FastAPI, BackgroundTasks, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os
import uuid
from datetime import datetime
from typing import Dict, Optional
import asyncio
import weave
import fitz  # PyMuPDF for PDF compression

# Import our video generation pipeline
from video_generator import generate_summary_video, generate_summary_video_upload

# Initialize Weave for API tracking (with fallback)
try:
    weave.init("manim_video_api")
    print("✅ W&B Weave tracking initialized")
except Exception as e:
    print(f"⚠️  W&B Weave not available: {e}")
    print("📊 Server will run without tracking")

app = FastAPI(title="Manim Video Generation API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JSON file to store job status
JOBS_FILE = "jobs.json"

class VideoRequest(BaseModel):
    pdf_url: str
    quality: str = "medium_quality"

class JobStatus(BaseModel):
    job_id: str
    status: str  # pending, processing, completed, failed
    created_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None
    video_path: Optional[str] = None
    pdf_source: Optional[str] = None
    video_name: Optional[str] = None
    generation_metrics: Optional[Dict] = None

class RenameVideoRequest(BaseModel):
    video_name: str

def load_jobs() -> Dict[str, Dict]:
    """Load jobs from JSON file"""
    if os.path.exists(JOBS_FILE):
        try:
            with open(JOBS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_jobs(jobs: Dict[str, Dict]):
    """Save jobs to JSON file"""
    with open(JOBS_FILE, 'w') as f:
        json.dump(jobs, f, indent=2)

def update_job_status(job_id: str, status: str, **kwargs):
    """Update job status in JSON file"""
    jobs = load_jobs()
    if job_id in jobs:
        jobs[job_id]["status"] = status
        if status == "completed":
            jobs[job_id]["completed_at"] = datetime.now().isoformat()
        for key, value in kwargs.items():
            jobs[job_id][key] = value
        save_jobs(jobs)

def compress_pdf(input_path: str, output_path: str, target_size_mb: float = 2.5) -> str:
    """
    Compress PDF to reduce file size while maintaining readability.
    Returns the output path of the compressed PDF.
    """
    try:
        # Open the original PDF
        doc = fitz.open(input_path)
        
        # Create a new PDF with compression settings
        compressed_doc = fitz.open()  # New empty document
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Reduce image quality and resolution for compression
            # Get page as pixmap with lower resolution
            mat = fitz.Matrix(0.8, 0.8)  # 80% scale to reduce size
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # Convert to image bytes with compression
            img_data = pix.tobytes("jpeg", jpg_quality=75)  # 75% JPEG quality
            
            # Create new page and insert compressed image
            new_page = compressed_doc.new_page(width=page.rect.width, height=page.rect.height)
            new_page.insert_image(new_page.rect, stream=img_data)
        
        # Save with additional compression options
        compressed_doc.save(
            output_path,
            garbage=4,  # Garbage collection level (max compression)
            deflate=True,  # Use deflate compression
            clean=True,    # Clean unused objects
            linear=True    # Linearize for web optimization
        )
        
        # Clean up
        doc.close()
        compressed_doc.close()
        pix = None
        
        # Check if compression was successful
        if os.path.exists(output_path):
            original_size = os.path.getsize(input_path)
            compressed_size = os.path.getsize(output_path)
            compression_ratio = compressed_size / original_size
            
            print(f"📦 PDF compressed: {original_size/1024/1024:.1f}MB → {compressed_size/1024/1024:.1f}MB ({compression_ratio:.1%})")
            
            # If still too large, try more aggressive compression
            if compressed_size > target_size_mb * 1024 * 1024:
                print(f"🔄 File still too large, trying aggressive compression...")
                return compress_pdf_aggressive(input_path, output_path, target_size_mb)
            
            return output_path
        else:
            raise Exception("Compression failed - output file not created")
            
    except Exception as e:
        print(f"❌ PDF compression failed: {e}")
        # Return original file if compression fails
        return input_path

def compress_pdf_aggressive(input_path: str, output_path: str, target_size_mb: float = 2.5) -> str:
    """
    More aggressive PDF compression by converting to lower resolution images.
    """
    try:
        doc = fitz.open(input_path)
        compressed_doc = fitz.open()
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Very aggressive scaling and quality reduction
            mat = fitz.Matrix(0.6, 0.6)  # 60% scale
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # Lower JPEG quality for maximum compression
            img_data = pix.tobytes("jpeg", jpg_quality=50)  # 50% JPEG quality
            
            new_page = compressed_doc.new_page(width=page.rect.width, height=page.rect.height)
            new_page.insert_image(new_page.rect, stream=img_data)
        
        # Save with maximum compression
        compressed_doc.save(
            output_path,
            garbage=4,
            deflate=True,
            clean=True,
            linear=True
        )
        
        doc.close()
        compressed_doc.close()
        pix = None
        
        if os.path.exists(output_path):
            compressed_size = os.path.getsize(output_path)
            print(f"📦 Aggressive compression: {compressed_size/1024/1024:.1f}MB")
            return output_path
        else:
            return input_path
            
    except Exception as e:
        print(f"❌ Aggressive compression failed: {e}")
        return input_path

@weave.op()
async def process_video_generation(job_id: str, pdf_source: str, is_upload: bool = False):
    """Background task to generate video with Weave tracking"""
    try:
        update_job_status(job_id, "processing")
        print(f"Job {job_id}: Starting video generation...")
        
        # Use our existing video generation pipeline
        if is_upload:
            # For uploaded files, we need to use base64 encoding
            result = await generate_summary_video_upload(pdf_source)
        else:
            # For URLs, pass directly
            result = await generate_summary_video(pdf_source)
        
        # Move video to outputs directory with job ID
        os.makedirs("outputs", exist_ok=True)
        original_path = result["video_path"]
        final_path = f"outputs/video_{job_id}.mp4"
        
        # Move the file
        if os.path.exists(original_path):
            os.rename(original_path, final_path)
            result["video_path"] = final_path
        
        # Update job as completed with full metrics
        update_job_status(
            job_id, 
            "completed", 
            video_path=final_path,
            generation_metrics=result
        )
        print(f"Job {job_id}: Completed successfully!")
        
    except Exception as e:
        error_msg = str(e)
        print(f"Job {job_id}: Failed with error: {error_msg}")
        update_job_status(job_id, "failed", error=error_msg)

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the simple frontend"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PDF to Video Generator</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh; padding: 20px;
            }
            .container { 
                max-width: 1200px; margin: 0 auto; 
                background: white; border-radius: 20px; 
                padding: 40px; box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            }
            .header { text-align: center; margin-bottom: 40px; }
            .header h1 { color: #333; font-size: 2.5em; margin-bottom: 10px; }
            .header p { color: #666; font-size: 1.2em; }
            .upload-section { 
                background: #f8f9fa; padding: 30px; border-radius: 15px; 
                margin-bottom: 30px; text-align: center;
            }
            .upload-area { 
                border: 2px dashed #ddd; padding: 40px; border-radius: 10px;
                transition: all 0.3s ease; cursor: pointer;
            }
            .upload-area:hover { border-color: #667eea; background: #f0f4ff; }
            .upload-area.dragover { border-color: #667eea; background: #f0f4ff; }
            input[type="file"] { display: none; }
            .btn { 
                background: #667eea; color: white; padding: 15px 30px;
                border: none; border-radius: 10px; font-size: 16px;
                cursor: pointer; transition: all 0.3s ease;
            }
            .btn:hover { background: #5a6fd8; transform: translateY(-2px); }
            .btn:disabled { background: #ccc; cursor: not-allowed; transform: none; }
            .url-section { margin: 20px 0; }
            .url-input { 
                width: 100%; padding: 15px; border: 2px solid #ddd;
                border-radius: 10px; font-size: 16px; margin-bottom: 15px;
            }
            .jobs-section { margin-top: 40px; }
            .job-item { 
                background: #f8f9fa; padding: 20px; border-radius: 10px;
                margin-bottom: 15px; border-left: 4px solid #667eea;
            }
            .job-header { display: flex; justify-content: between; align-items: center; }
            .status { 
                padding: 5px 15px; border-radius: 20px; font-size: 12px;
                font-weight: bold; text-transform: uppercase;
            }
            .status.pending { background: #ffeaa7; color: #fdcb6e; }
            .status.processing { background: #74b9ff; color: white; }
            .status.completed { background: #00b894; color: white; }
            .status.failed { background: #e17055; color: white; }
            .progress-bar { 
                width: 100%; height: 4px; background: #eee; 
                border-radius: 2px; margin: 10px 0; overflow: hidden;
            }
            .progress-fill { 
                height: 100%; background: #667eea; 
                transition: width 0.3s ease;
                animation: pulse 2s infinite;
            }
            @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
            .video-player { margin-top: 15px; }
            video { width: 100%; max-width: 500px; border-radius: 10px; }
            .metrics { 
                margin-top: 10px; font-size: 14px; color: #666;
                display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 10px;
            }
            .metric { background: white; padding: 10px; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎬 PDF to Video Generator</h1>
                <p>Convert research papers into educational videos with AI + Manim</p>
            </div>
            
            <div class="upload-section">
                <h3>📄 Upload PDF or Enter URL</h3>
                
                <div class="upload-area" onclick="document.getElementById('fileInput').click()">
                    <div id="uploadText">
                        <h4>📁 Click to Upload PDF</h4>
                        <p>Or drag and drop a PDF file here</p>
                        <small style="color: #888; margin-top: 10px; display: block;">Large files will be automatically compressed</small>
                    </div>
                </div>
                <input type="file" id="fileInput" accept=".pdf">
                
                <div class="url-section">
                    <input type="url" id="urlInput" class="url-input" placeholder="Or enter PDF URL (e.g., https://arxiv.org/pdf/2301.07041.pdf)">
                </div>
                
                <button class="btn" id="generateBtn" onclick="generateVideo()">🚀 Generate Video</button>
            </div>
            
            <div class="jobs-section">
                <h3>📊 Video Generation Jobs</h3>
                <div id="jobsList"></div>
            </div>
        </div>

        <script>
            let jobs = {};
            let pollInterval;

            // Drag and drop functionality
            const uploadArea = document.querySelector('.upload-area');
            const fileInput = document.getElementById('fileInput');
            
            uploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadArea.classList.add('dragover');
            });
            
            uploadArea.addEventListener('dragleave', () => {
                uploadArea.classList.remove('dragover');
            });
            
            uploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadArea.classList.remove('dragover');
                const files = e.dataTransfer.files;
                if (files.length > 0 && files[0].type === 'application/pdf') {
                    fileInput.files = files;
                    document.getElementById('uploadText').innerHTML = `
                        <h4>📄 ${files[0].name}</h4>
                        <p>Ready to generate video</p>
                    `;
                }
            });
            
            fileInput.addEventListener('change', (e) => {
                if (e.target.files.length > 0) {
                    document.getElementById('uploadText').innerHTML = `
                        <h4>📄 ${e.target.files[0].name}</h4>
                        <p>Ready to generate video</p>
                    `;
                }
            });

            async function generateVideo() {
                const fileInput = document.getElementById('fileInput');
                const urlInput = document.getElementById('urlInput');
                const generateBtn = document.getElementById('generateBtn');
                
                generateBtn.disabled = true;
                generateBtn.textContent = '🔄 Generating...';
                
                try {
                    let response;
                    
                    if (fileInput.files.length > 0) {
                        // Upload file
                        const formData = new FormData();
                        formData.append('file', fileInput.files[0]);
                        formData.append('quality', 'medium_quality');
                        
                        response = await fetch('/generate-video-upload', {
                            method: 'POST',
                            body: formData
                        });
                    } else if (urlInput.value) {
                        // Use URL
                        response = await fetch('/generate-video-url', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                pdf_url: urlInput.value,
                                quality: 'medium_quality'
                            })
                        });
                    } else {
                        alert('Please upload a PDF file or enter a URL');
                        return;
                    }
                    
                    const result = await response.json();
                    
                    if (response.ok) {
                        // Reset form
                        fileInput.value = '';
                        urlInput.value = '';
                        document.getElementById('uploadText').innerHTML = `
                            <h4>📁 Click to Upload PDF</h4>
                            <p>Or drag and drop a PDF file here</p>
                        `;
                        
                        // Start polling for this job
                        startPolling();
                        
                        alert(`Video generation started! Job ID: ${result.job_id}`);
                    } else {
                        alert(`Error: ${result.detail}`);
                    }
                } catch (error) {
                    alert(`Error: ${error.message}`);
                } finally {
                    generateBtn.disabled = false;
                    generateBtn.textContent = '🚀 Generate Video';
                }
            }
            
            function startPolling() {
                if (pollInterval) clearInterval(pollInterval);
                
                pollInterval = setInterval(async () => {
                    try {
                        const response = await fetch('/jobs');
                        const data = await response.json();
                        jobs = {};
                        data.jobs.forEach(job => jobs[job.job_id] = job);
                        updateJobsDisplay();
                    } catch (error) {
                        console.error('Error polling jobs:', error);
                    }
                }, 2000);
            }
            
            function updateJobsDisplay() {
                const jobsList = document.getElementById('jobsList');
                const jobsArray = Object.values(jobs).sort((a, b) => 
                    new Date(b.created_at) - new Date(a.created_at)
                );
                
                if (jobsArray.length === 0) {
                    jobsList.innerHTML = '<p>No video generation jobs yet. Upload a PDF to get started!</p>';
                    return;
                }
                
                jobsList.innerHTML = jobsArray.map(job => `
                    <div class="job-item">
                        <div class="job-header">
                            <div>
                                <strong>${job.video_name || `Video ${job.job_id.substring(0, 8)}`}</strong>
                                <span class="status ${job.status}">${job.status}</span>
                            </div>
                            <div>
                                ${new Date(job.created_at).toLocaleString()}
                            </div>
                        </div>
                        
                        ${job.status === 'processing' ? `
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: 50%"></div>
                            </div>
                            <p>⏳ Generating video clips and voice-over...</p>
                        ` : ''}
                        
                        ${job.status === 'completed' ? `
                            <div class="video-player">
                                <video controls>
                                    <source src="/download/${job.job_id}" type="video/mp4">
                                    Your browser does not support the video tag.
                                </video>
                                <div class="metrics">
                                    ${job.generation_metrics ? `
                                        <div class="metric">
                                            <strong>Success Rate:</strong> 
                                            ${(job.generation_metrics.success_rate * 100).toFixed(1)}%
                                        </div>
                                        <div class="metric">
                                            <strong>Total Clips:</strong> 
                                            ${job.generation_metrics.total_clips}
                                        </div>
                                        <div class="metric">
                                            <strong>Successful:</strong> 
                                            ${job.generation_metrics.successful_clips}
                                        </div>
                                    ` : ''}
                                </div>
                            </div>
                            <button class="btn" onclick="downloadVideo('${job.job_id}')">📥 Download</button>
                        ` : ''}
                        
                        ${job.status === 'failed' ? `
                            <p style="color: #e17055;">❌ ${job.error}</p>
                        ` : ''}
                    </div>
                `).join('');
            }
            
            function downloadVideo(jobId) {
                window.open(`/download/${jobId}`, '_blank');
            }
            
            // Start polling on page load
            startPolling();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/generate-video-upload")
async def generate_video_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """Upload PDF and start video generation"""
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Read file content to check size
    content = await file.read()
    
    # Create uploads directory
    os.makedirs("uploads", exist_ok=True)
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    original_file_path = f"uploads/{file_id}_{file.filename}"
    
    # Save uploaded file
    with open(original_file_path, "wb") as f:
        f.write(content)
    
    # Check file size and compress if necessary
    file_size_mb = len(content) / (1024 * 1024)
    print(f"📄 Uploaded PDF: {file.filename} ({file_size_mb:.1f}MB)")
    
    final_file_path = original_file_path
    
    if file_size_mb > 2.5:  # Compress if larger than 2.5MB
        print(f"🔄 File is {file_size_mb:.1f}MB, compressing to reduce API load...")
        compressed_file_path = f"uploads/{file_id}_compressed_{file.filename}"
        
        try:
            final_file_path = compress_pdf(original_file_path, compressed_file_path, target_size_mb=2.5)
            
            # Check final size
            if os.path.exists(final_file_path):
                final_size = os.path.getsize(final_file_path) / (1024 * 1024)
                
                # If compression was successful and file is smaller
                if final_file_path != original_file_path and final_size < file_size_mb:
                    print(f"✅ Using compressed version: {final_size:.1f}MB")
                    # Remove original large file to save space
                    if os.path.exists(original_file_path):
                        os.remove(original_file_path)
                else:
                    print(f"⚠️  Compression didn't help much, using original")
                    final_file_path = original_file_path
                    # Remove failed compression attempt
                    if os.path.exists(compressed_file_path):
                        os.remove(compressed_file_path)
                
                # Final check - if still too large for Claude API
                if final_size > 5.0:  # 5MB absolute limit for Claude
                    raise HTTPException(
                        status_code=400, 
                        detail=f"PDF is too large even after compression ({final_size:.1f}MB). Please try a smaller file or use a URL instead."
                    )
            else:
                print(f"⚠️  Compression failed, using original file")
                final_file_path = original_file_path
                
        except Exception as e:
            print(f"⚠️  Compression error: {e}, using original file")
            final_file_path = original_file_path
            # Remove failed compression attempt
            compressed_file_path_check = f"uploads/{file_id}_compressed_{file.filename}"
            if os.path.exists(compressed_file_path_check):
                os.remove(compressed_file_path_check)
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Create job record
    job_data = {
        "job_id": job_id,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "pdf_source": final_file_path,
        "original_filename": file.filename,
        "video_name": None
    }
    
    jobs = load_jobs()
    jobs[job_id] = job_data
    save_jobs(jobs)
    
    # Start background task
    background_tasks.add_task(
        process_video_generation,
        job_id,
        final_file_path,
        True  # is_upload = True
    )
    
    return {
        "job_id": job_id, 
        "status": "pending", 
        "message": "PDF uploaded, video generation started"
    }

@app.post("/generate-video-url")
async def generate_video_url(request: VideoRequest, background_tasks: BackgroundTasks):
    """Start video generation with PDF URL"""
    
    if not request.pdf_url:
        raise HTTPException(status_code=400, detail="PDF URL is required")
    
    if not request.pdf_url.startswith(('http://', 'https://')):
        raise HTTPException(status_code=400, detail="Please provide a valid URL")
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Create job record
    job_data = {
        "job_id": job_id,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "pdf_source": request.pdf_url,
        "quality": request.quality,
        "video_name": None
    }
    
    jobs = load_jobs()
    jobs[job_id] = job_data
    save_jobs(jobs)
    
    # Start background task
    background_tasks.add_task(
        process_video_generation,
        job_id,
        request.pdf_url,
        False  # is_upload = False
    )
    
    return {"job_id": job_id, "status": "pending", "message": "Video generation started"}

@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get job status"""
    jobs = load_jobs()
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return jobs[job_id]

@app.get("/jobs")
async def list_jobs():
    """List all jobs"""
    jobs = load_jobs()
    return {"jobs": list(jobs.values())}

@app.get("/download/{job_id}")
async def download_video(job_id: str):
    """Download generated video"""
    jobs = load_jobs()
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Video not ready yet")
    
    video_path = job.get("video_path")
    if not video_path or not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found")
    
    return FileResponse(
        video_path,
        media_type='video/mp4',
        filename=f"video_{job_id}.mp4"
    )

@app.put("/jobs/{job_id}/rename")
async def rename_video(job_id: str, request: RenameVideoRequest):
    """Rename a video"""
    jobs = load_jobs()
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Update video name
    jobs[job_id]["video_name"] = request.video_name
    save_jobs(jobs)
    
    return {"message": "Video renamed successfully", "video_name": request.video_name}

@app.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete job and associated files"""
    jobs = load_jobs()
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    # Delete video file if it exists
    if job.get("video_path") and os.path.exists(job["video_path"]):
        os.remove(job["video_path"])
    
    # Delete uploaded PDF if it exists
    if job.get("pdf_source") and job["pdf_source"].startswith("uploads/") and os.path.exists(job["pdf_source"]):
        os.remove(job["pdf_source"])
    
    # Remove from jobs
    del jobs[job_id]
    save_jobs(jobs)
    
    return {"message": "Job deleted successfully"}

@app.get("/api-info")
async def api_info():
    """API information"""
    return {
        "message": "Manim Video Generation API with W&B Weave Tracking",
        "features": [
            "PDF upload or URL input",
            "Background video generation",
            "Real-time job tracking",
            "W&B Weave integration",
            "Video download and streaming"
        ],
        "endpoints": {
            "GET /": "Frontend interface",
            "POST /generate-video-upload": "Upload PDF and start generation",
            "POST /generate-video-url": "Start generation with PDF URL",
            "GET /jobs": "List all jobs",
            "GET /jobs/{job_id}": "Get job status", 
            "GET /download/{job_id}": "Download video",
            "PUT /jobs/{job_id}/rename": "Rename video",
            "DELETE /jobs/{job_id}": "Delete job"
        },
        "weave_project": "manim_video_api"
    }

if __name__ == "__main__":
    import uvicorn
    
    # Create necessary directories
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)
    
    print("🚀 Starting Manim Video Generation API with W&B Weave")
    print("📊 Weave project: manim_video_api") 
    print("🌐 Frontend: http://localhost:8000")
    print("📖 API docs: http://localhost:8000/docs")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True) 