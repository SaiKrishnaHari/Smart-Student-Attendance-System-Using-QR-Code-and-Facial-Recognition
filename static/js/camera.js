/**
 * Camera / Webcam Module
 * Handles webcam access, face capture, and video streaming.
 * SmartAttendance System
 */

// Store active streams for cleanup
const activeStreams = {};

/**
 * Start the webcam and stream to a video element.
 * @param {string} videoId - ID of the <video> element
 * @param {string} dotId - ID of the status dot element
 * @param {string} statusId - ID of the status text element
 * @returns {Promise} resolves when camera is ready
 */
async function startCamera(videoId, dotId, statusId) {
    const video = document.getElementById(videoId);
    const dot = document.getElementById(dotId);
    const statusText = document.getElementById(statusId);

    if (!video) {
        console.error(`Video element #${videoId} not found`);
        return;
    }

    try {
        // First check browser support
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            throw new Error('Camera API not supported in this browser');
        }

        console.log('Requesting camera access...');
        
        // Request camera access
        const stream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 640 },
                height: { ideal: 480 },
                facingMode: 'user'  // Front camera
            },
            audio: false
        });

        console.log('Camera stream obtained:', stream);
        console.log('Video tracks:', stream.getVideoTracks());

        video.srcObject = stream;
        activeStreams[videoId] = stream;

        // Ensure video plays
        video.muted = true;
        video.setAttribute('autoplay', 'true');
        video.setAttribute('playsinline', 'true');

        // Force video element to render
        video.style.display = 'block';
        video.style.width = '100%';
        video.style.height = '100%';
        video.style.objectFit = 'cover';

        // Wait for video to be ready with timeout
        await Promise.race([
            new Promise((resolve) => {
                const handleLoadedMetadata = () => {
                    console.log('Video metadata loaded', video.videoWidth, video.videoHeight);
                    video.removeEventListener('loadedmetadata', handleLoadedMetadata);
                    
                    // Ensure camera element has proper visibility
                    const container = video.parentElement;
                    if (container) {
                        container.style.display = 'block';
                        container.style.visibility = 'visible';
                    }
                    
                    // Try to play the video
                    const playPromise = video.play();
                    if (playPromise !== undefined) {
                        playPromise.catch(e => console.error('Play error:', e));
                    }
                    resolve();
                };
                video.addEventListener('loadedmetadata', handleLoadedMetadata);
            }),
            new Promise((_, reject) => 
                setTimeout(() => reject(new Error('Camera timeout - video did not load')), 5000)
            )
        ]);

        // Update status
        if (dot) {
            dot.classList.add('active');
        }
        if (statusText) {
            statusText.textContent = 'Camera active';
        }

        console.log('Camera started successfully');
        return stream;

    } catch (err) {
        console.error('Camera access error:', err);
        console.error('Error name:', err.name);
        console.error('Error message:', err.message);

        if (statusText) {
            if (err.name === 'NotAllowedError') {
                statusText.textContent = 'Camera access denied';
                showToast('error', 'Camera Blocked', 'Please allow camera access in your browser settings.');
            } else if (err.name === 'NotFoundError') {
                statusText.textContent = 'No camera found';
                showToast('error', 'No Camera', 'No camera device was found on this device.');
            } else if (err.name === 'NotReadableError') {
                statusText.textContent = 'Camera is in use';
                showToast('error', 'Camera In Use', 'Your camera is being used by another application. Please close it and try again.');
            } else {
                statusText.textContent = 'Camera error: ' + err.message;
                showToast('error', 'Camera Error', `Could not access camera: ${err.message}`);
            }
        }

        throw err;
    }
}

/**
 * Stop the webcam stream.
 * @param {string} videoId - ID of the <video> element
 */
function stopCamera(videoId) {
    const video = document.getElementById(videoId);
    const stream = activeStreams[videoId];

    if (stream) {
        stream.getTracks().forEach(track => track.stop());
        delete activeStreams[videoId];
    }

    if (video) {
        video.srcObject = null;
    }
}

/**
 * Capture a single frame from the video as a base64-encoded image.
 * @param {HTMLVideoElement} video - The video element
 * @param {HTMLCanvasElement} canvas - A canvas element for rendering
 * @returns {string|null} Base64 data URL of the captured frame
 */
function captureFrame(video, canvas) {
    if (!video || !canvas) return null;

    if (video.readyState < video.HAVE_ENOUGH_DATA) {
        showToast('warning', 'Camera Not Ready', 'Please wait for the camera to initialize.');
        return null;
    }

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext('2d');

    // Flip horizontally (mirror) for selfie camera
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Reset transform
    ctx.setTransform(1, 0, 0, 1, 0, 0);

    return canvas.toDataURL('image/jpeg', 0.9);
}

/**
 * Check if the browser supports getUserMedia.
 * @returns {boolean}
 */
function isCameraSupported() {
    return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
}

// Check camera support on load
document.addEventListener('DOMContentLoaded', function() {
    if (!isCameraSupported()) {
        console.warn('Camera API not supported in this browser.');
    }
});
