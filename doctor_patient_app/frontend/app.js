/**
 * Doctor-Patient Translator Frontend Application
 * Real-time audio streaming, transcription, and translation
 */

class DoctorPatientApp {
    constructor() {
        this.ws = null;
        this.audioContext = null;
        this.mediaStream = null;
        this.isRecording = false;
        this.recordingStartTime = null;
        this.timerInterval = null;
        this.doctorLang = "en";
        this.patientLang = "te";
        
        // Conversation storage
        this.conversationData = {
            original: "",
            doctor: "",
            patient: "",
            entries: []
        };
        
        this.initializeElements();
        this.attachEventListeners();
        this.checkServerHealth();
    }
    
    /**
     * Initialize DOM elements
     */
    initializeElements() {
        // Buttons
        this.startBtn = document.getElementById("start-btn");
        this.stopBtn = document.getElementById("stop-btn");
        this.clearBtn = document.getElementById("clear-btn");
        this.downloadBtn = document.getElementById("download-btn");
        this.exportTxtBtn = document.getElementById("export-txt-btn");
        
        // Selects
        this.doctorLangSelect = document.getElementById("doctor-lang");
        this.patientLangSelect = document.getElementById("patient-lang");
        
        // Checkboxes
        this.autoScrollCheckbox = document.getElementById("auto-scroll");
        
        // Display areas
        this.statusText = document.getElementById("status-text");
        this.timer = document.getElementById("timer");
        this.boxOriginal = document.getElementById("box-original");
        this.boxDoctor = document.getElementById("box-doctor");
        this.boxPatient = document.getElementById("box-patient");
        this.boxDoctorLang = document.getElementById("box-doctor-lang");
        this.boxPatientLang = document.getElementById("box-patient-lang");
        this.exportStatus = document.getElementById("export-status");
    }
    
    /**
     * Attach event listeners to buttons and controls
     */
    attachEventListeners() {
        this.startBtn.addEventListener("click", () => this.startRecording());
        this.stopBtn.addEventListener("click", () => this.stopRecording());
        this.clearBtn.addEventListener("click", () => this.clearAll());
        this.downloadBtn.addEventListener("click", () => this.downloadJSON());
        this.exportTxtBtn.addEventListener("click", () => this.exportText());
        
        // Update display when language changes
        this.doctorLangSelect.addEventListener("change", (e) => {
            this.doctorLang = e.target.value;
            this.boxDoctorLang.textContent = this.getLangName(this.doctorLang);
        });
        
        this.patientLangSelect.addEventListener("change", (e) => {
            this.patientLang = e.target.value;
            this.boxPatientLang.textContent = this.getLangName(this.patientLang);
        });
    }
    
    /**
     * Get human-readable language name
     */
    getLangName(code) {
        const names = {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "hi": "Hindi",
            "te": "Telugu",
            "ta": "Tamil",
            "kn": "Kannada",
            "ml": "Malayalam",
            "mr": "Marathi",
            "gu": "Gujarati",
            "bn": "Bengali",
            "pa": "Punjabi",
            "or": "Odia",
            "as": "Assamese",
            "ur": "Urdu"
        };
        return names[code] || code.toUpperCase();
    }
    
    /**
     * Check if server is healthy
     */
    async checkServerHealth() {
        try {
            const response = await fetch("/health");
            const data = await response.json();
            
            if (!data.api_key_configured) {
                this.statusText.textContent = "⚠️ API Key Not Configured";
                this.statusText.classList.add("error");
                this.startBtn.disabled = true;
            }
        } catch (error) {
            console.warn("Could not connect to server:", error);
            this.statusText.textContent = "⚠️ Server Not Available";
            this.startBtn.disabled = true;
        }
    }
    
    /**
     * Start recording and streaming audio
     */
    async startRecording() {
        try {
            // Get selected languages
            this.doctorLang = this.doctorLangSelect.value;
            this.patientLang = this.patientLangSelect.value;
            
            // Validate: Languages must be different (Soniox requirement)
            if (this.doctorLang === this.patientLang) {
                this.statusText.textContent = "❌ Doctor and Patient languages must be different";
                this.statusText.classList.add("error");
                return;
            }
            
            // Update display
            this.boxDoctorLang.textContent = this.getLangName(this.doctorLang);
            this.boxPatientLang.textContent = this.getLangName(this.patientLang);
            
            // Request microphone access
            this.mediaStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });
            
            // Initialize WebSocket
            this.initializeWebSocket();
            
            // Setup audio processing
            this.setupAudioProcessing();
            
            // Update UI
            this.isRecording = true;
            this.recordingStartTime = Date.now();
            this.startBtn.disabled = true;
            this.stopBtn.disabled = false;
            this.clearBtn.disabled = true;
            this.doctorLangSelect.disabled = true;
            this.patientLangSelect.disabled = true;
            this.statusText.textContent = "🔴 Recording...";
            this.statusText.classList.add("recording");
            this.exportStatus.textContent = "";
            this.startTimer();
            
            // Clear boxes on start
            this.clearBoxes();
            
            console.log("🎙️ Recording started");
            
        } catch (error) {
            console.error("Error accessing microphone:", error);
            this.statusText.textContent = `❌ Microphone error: ${error.message}`;
            this.statusText.classList.add("error");
        }
    }
    
    /**
     * Stop recording and close connections
     */
    stopRecording() {
        console.log("⛔ Stopping recording...");
        
        // Stop recording
        this.isRecording = false;
        
        // Stop media stream
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
        }
        
        // Close WebSocket
        if (this.ws) {
            this.ws.close();
        }
        
        // Stop timer
        this.stopTimer();
        
        // Update UI
        this.startBtn.disabled = false;
        this.stopBtn.disabled = true;
        this.clearBtn.disabled = false;
        this.doctorLangSelect.disabled = false;
        this.patientLangSelect.disabled = false;
        this.statusText.textContent = "✅ Recording Complete";
        this.statusText.classList.remove("recording");
        this.downloadBtn.disabled = false;
        this.exportTxtBtn.disabled = false;
    }
    
    /**
     * Initialize WebSocket connection
     */
    initializeWebSocket() {
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        this.ws = new WebSocket(wsUrl);
        this.ws.binaryType = "arraybuffer";
        
        this.ws.onopen = () => {
            console.log("✓ WebSocket connected");
            
            // Send initial configuration
            this.ws.send(JSON.stringify({
                doctor_lang: this.doctorLang,
                patient_lang: this.patientLang
            }));
        };
        
        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                
                if (data.status === "connected") {
                    console.log("✓ Backend connected to Soniox");
                } else if (data.type === "partial" || data.type === "final") {
                    // Handle both partial and final tokens
                    const tokenType = data.type === "final" ? "🔵 FINAL" : "⚫ PARTIAL";
                    console.log(`${tokenType}: ${data.text}`);
                    
                    // Update boxes with latest data
                    if (data.boxes) {
                        this.updateBoxes(data.boxes);
                    }
                    
                    // Store conversation data
                    if (data.is_final) {
                        this.conversationData.entries.push({
                            text: data.text,
                            timestamp: new Date().toISOString()
                        });
                    }
                } else if (data.type === "update") {
                    // Legacy update format
                    this.updateBoxes(data.boxes);
                    this.conversationData.entries.push(...(data.tokens || []));
                } else if (data.type === "saved") {
                    console.log("✓ Conversation saved to files");
                }
            } catch (error) {
                console.error("Error processing WebSocket message:", error);
            }
        };
        
        this.ws.onerror = (error) => {
            console.error("WebSocket error:", error);
            this.statusText.textContent = "❌ Connection Error";
            this.statusText.classList.add("error");
        };
        
        this.ws.onclose = () => {
            console.log("WebSocket closed");
        };
    }
    
    /**
     * Setup audio processing pipeline
     */
    setupAudioProcessing() {
        // CRITICAL FIX: Create audio context with 16000 Hz sample rate to match Soniox requirement
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
            sampleRate: 16000
        });
        
        console.log(`🎵 Audio Context Sample Rate: ${this.audioContext.sampleRate} Hz (Soniox requires 16000 Hz)`);
        
        // Create source from media stream
        const source = this.audioContext.createMediaStreamSource(this.mediaStream);
        
        // Create processor - smaller buffer for lower latency
        const processor = this.audioContext.createScriptProcessor(2048, 1, 1);
        
        let audioChunkCount = 0;
        let totalBytesSent = 0;
        
        processor.onaudioprocess = (event) => {
            if (this.isRecording && this.ws && this.ws.readyState === WebSocket.OPEN) {
                // Get audio data from input buffer
                const audioData = event.inputBuffer.getChannelData(0);
                
                // Convert Float32 to PCM16 with proper scaling
                const pcm16 = new Int16Array(audioData.length);
                for (let i = 0; i < audioData.length; i++) {
                    // Clamp to [-1, 1] and scale to 16-bit range
                    let sample = Math.max(-1, Math.min(1, audioData[i]));
                    pcm16[i] = sample < 0 
                        ? sample * 0x8000  // -32768 to -1
                        : sample * 0x7FFF;  // 0 to 32767
                }
                
                audioChunkCount++;
                totalBytesSent += pcm16.byteLength;
                
                // Log every 10 chunks
                if (audioChunkCount % 10 === 0) {
                    console.log(`🔊 Audio: ${audioChunkCount} chunks (${totalBytesSent} bytes, rate: 16000 Hz)`);
                }
                
                // Send PCM16 buffer to server
                this.ws.send(pcm16.buffer);
            }
        };
        
        source.connect(processor);
        processor.connect(this.audioContext.destination);
    }
    
    /**
     * Convert Float32 audio to PCM16
     */
    float32ToPCM16(float32Array) {
        const int16Array = new Int16Array(float32Array.length);
        for (let i = 0; i < float32Array.length; i++) {
            int16Array[i] = float32Array[i] < 0
                ? float32Array[i] * 0x8000
                : float32Array[i] * 0x7FFF;
        }
        return int16Array.buffer;
    }
    
    /**
     * Update all three boxes with latest content
     */
    updateBoxes(boxes) {
        if (boxes) {
            const original = boxes.original || "[No content]";
            const doctor = boxes.doctor || "[No content]";
            const patient = boxes.patient || "[No content]";
            
            // Update content
            this.boxOriginal.textContent = original;
            this.boxDoctor.textContent = doctor;
            this.boxPatient.textContent = patient;
            
            // Store for export
            this.conversationData.original = original;
            this.conversationData.doctor = doctor;
            this.conversationData.patient = patient;
            
            // Auto-scroll if enabled
            if (this.autoScrollCheckbox.checked) {
                this.boxOriginal.scrollTop = this.boxOriginal.scrollHeight;
                this.boxDoctor.scrollTop = this.boxDoctor.scrollHeight;
                this.boxPatient.scrollTop = this.boxPatient.scrollHeight;
            }
            
            // Add animation
            [this.boxOriginal, this.boxDoctor, this.boxPatient].forEach(box => {
                box.classList.add("updating");
                setTimeout(() => box.classList.remove("updating"), 300);
            });
        }
    }
    
    /**
     * Clear all boxes
     */
    clearBoxes() {
        this.boxOriginal.innerHTML = '<p class="placeholder">[Listening for audio...]</p>';
        this.boxDoctor.innerHTML = '<p class="placeholder">[Listening for audio...]</p>';
        this.boxPatient.innerHTML = '<p class="placeholder">[Listening for audio...]</p>';
    }
    
    /**
     * Clear all content and reset
     */
    clearAll() {
        this.conversationData = {
            original: "",
            doctor: "",
            patient: "",
            entries: []
        };
        this.clearBoxes();
        this.timer.textContent = "00:00";
        this.statusText.textContent = "Ready";
        this.statusText.classList.remove("error", "recording");
        this.downloadBtn.disabled = true;
        this.exportTxtBtn.disabled = true;
        this.exportStatus.textContent = "";
        console.log("🗑️ Content cleared");
    }
    
    /**
     * Start timer
     */
    startTimer() {
        this.timerInterval = setInterval(() => {
            const elapsed = Date.now() - this.recordingStartTime;
            const seconds = Math.floor(elapsed / 1000);
            const minutes = Math.floor(seconds / 60);
            const secs = seconds % 60;
            this.timer.textContent = `${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
        }, 100);
    }
    
    /**
     * Stop timer
     */
    stopTimer() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
        }
    }
    
    /**
     * Download as JSON
     */
    downloadJSON() {
        const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
        const filename = `conversation_${timestamp}.json`;
        
        const data = {
            timestamp: new Date().toISOString(),
            doctor_language: this.doctorLang,
            patient_language: this.patientLang,
            boxes: {
                original: this.conversationData.original,
                doctor: this.conversationData.doctor,
                patient: this.conversationData.patient
            },
            entries: this.conversationData.entries
        };
        
        const content = JSON.stringify(data, null, 2);
        this.downloadFile(content, filename, "application/json");
        
        this.exportStatus.textContent = `✓ Downloaded: ${filename}`;
        this.exportStatus.classList.add("success");
        setTimeout(() => {
            this.exportStatus.textContent = "";
            this.exportStatus.classList.remove("success");
        }, 3000);
    }
    
    /**
     * Export as formatted text
     */
    exportText() {
        const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
        const filename = `conversation_${timestamp}.txt`;
        
        let content = "=".repeat(80) + "\n";
        content += "DOCTOR-PATIENT REAL-TIME CONVERSATION TRANSCRIPT\n";
        content += "=".repeat(80) + "\n\n";
        
        content += `Doctor Language: ${this.getLangName(this.doctorLang)}\n`;
        content += `Patient Language: ${this.getLangName(this.patientLang)}\n`;
        content += `Timestamp: ${new Date().toISOString()}\n\n`;
        
        content += "🟦 BOX #1: ORIGINAL CONVERSATION\n";
        content += "-".repeat(80) + "\n";
        content += this.conversationData.original + "\n\n";
        
        content += "🟩 BOX #2: DOCTOR'S VIEW\n";
        content += "-".repeat(80) + "\n";
        content += this.conversationData.doctor + "\n\n";
        
        content += "🟨 BOX #3: PATIENT'S VIEW\n";
        content += "-".repeat(80) + "\n";
        content += this.conversationData.patient + "\n";
        content += "=".repeat(80) + "\n";
        
        this.downloadFile(content, filename, "text/plain");
        
        this.exportStatus.textContent = `✓ Downloaded: ${filename}`;
        this.exportStatus.classList.add("success");
        setTimeout(() => {
            this.exportStatus.textContent = "";
            this.exportStatus.classList.remove("success");
        }, 3000);
    }
    
    /**
     * Helper to download file
     */
    downloadFile(content, filename, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
}

// Initialize app when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
    console.log("🚀 Initializing Doctor-Patient Translator App");
    window.app = new DoctorPatientApp();
});
