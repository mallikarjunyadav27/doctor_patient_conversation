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
        
        // Participant info
        this.selectedDoctor = null;
        this.selectedPatient = null;
        this.searchTimeout = null;
        
        // Conversation storage
        this.conversationData = {
            original: "",
            doctor: "",
            patient: "",
            entries: []
        };
        
        // Post-recording state
        this.postRecordingData = null;
        this.conversationCompleted = false;
        this.conversationDuration = null;
        
        this.initializeElements();
        this.attachEventListeners();
        this.checkServerHealth();
        this._loadParamsFromURL();
    }
    
    /**
     * Initialize DOM elements
     */
    initializeElements() {
        // Buttons
        this.selectParticipantsBtn = document.getElementById("select-participants-btn");
        this.startBtn = document.getElementById("start-btn");
        this.stopBtn = document.getElementById("stop-btn");
        this.clearBtn = document.getElementById("clear-btn");
        this.downloadBtn = document.getElementById("download-btn");
        this.exportTxtBtn = document.getElementById("export-txt-btn");
        
        // Modal elements
        this.modal = document.getElementById("participant-modal");
        this.closeModal = document.querySelector(".close-modal");
        this.doctorSearch = document.getElementById("doctor-search");
        this.patientSearch = document.getElementById("patient-search");
        this.doctorSuggestions = document.getElementById("doctor-suggestions");
        this.patientSuggestions = document.getElementById("patient-suggestions");
        this.doctorInfo = document.getElementById("doctor-info");
        this.patientInfo = document.getElementById("patient-info");
        this.confirmParticipantsBtn = document.getElementById("confirm-participants-btn");
        this.cancelModalBtn = document.getElementById("cancel-modal-btn");
        this.modalError = document.getElementById("modal-error");
        
        // Participant display
        this.participantInfo = document.getElementById("participant-info");
        this.currentDoctorName = document.getElementById("current-doctor-name");
        this.currentPatientName = document.getElementById("current-patient-name");
        
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
        
        // Post-recording elements
        this.completionBanner = document.getElementById("completion-banner");
        this.bannerText = document.getElementById("banner-text");
        this.medicalSummarySection = document.getElementById("medical-summary-section");
        this.clinicalSummaryContent = document.getElementById("clinical-summary-content");
        this.conclusionContent = document.getElementById("conclusion-content");
        this.pdfSection = document.getElementById("pdf-section");
        this.pdfConversationBtn = document.getElementById("pdf-conversation-btn");
        this.pdfPatientSummaryBtn = document.getElementById("pdf-patient-summary-btn");
        this.pdfResearchBtn = document.getElementById("pdf-research-btn");
        this.pdfStatus = document.getElementById("pdf-status");
        
        // Error modal elements
        this.errorModal = document.getElementById("error-modal");
        this.errorModalTitle = document.getElementById("error-modal-title");
        this.errorModalMessage = document.getElementById("error-modal-message");
        this.errorModalRetryBtn = document.getElementById("error-modal-retry-btn");
        this.errorModalCloseBtn = document.getElementById("error-modal-close-btn");
        this.closeErrorModal = document.querySelector(".close-error-modal");
        
        // Summary modal elements
        this.summaryModal = document.getElementById("summary-modal");
        this.closeSummaryModalBtn = document.getElementById("close-summary-modal-btn");
        this.summaryDoctorName = document.getElementById("summary-doctor-name");
        this.summaryPatientName = document.getElementById("summary-patient-name");
        this.summaryDate = document.getElementById("summary-date");
        this.summaryLanguage = document.getElementById("summary-language");
        this.summarySegments = document.getElementById("summary-segments");
        this.conversationSegments = document.getElementById("conversation-segments");
        this.transcriptEditor = document.getElementById("transcript-editor");
        this.generateSummaryBtn = document.getElementById("generate-summary-btn");
        this.generatingIndicator = document.getElementById("generating-indicator");
        this.medicalSummaryModalSection = document.getElementById("medical-summary-section");
        this.conclusionModalSection = document.getElementById("conclusion-section");
        this.summaryEditor = document.getElementById("summary-editor");
        this.conclusionEditor = document.getElementById("conclusion-editor");
        this.savePdfBtn = document.getElementById("save-pdf-btn");
    }
    
    /**
     * Attach event listeners to buttons and controls
     */
    attachEventListeners() {
        this.selectParticipantsBtn.addEventListener("click", () => this.openModal());
        this.startBtn.addEventListener("click", () => this.startRecording());
        this.stopBtn.addEventListener("click", () => this.stopRecording());
        this.clearBtn.addEventListener("click", () => this.clearAll());
        this.downloadBtn.addEventListener("click", () => this.downloadJSON());
        this.exportTxtBtn.addEventListener("click", () => this.exportText());
        
        // Modal events
        this.closeModal.addEventListener("click", () => this.closeModalDialog());
        this.cancelModalBtn.addEventListener("click", () => this.closeModalDialog());
        this.confirmParticipantsBtn.addEventListener("click", () => this.confirmParticipants());
        this.doctorSearch.addEventListener("input", (e) => this.onDoctorSearch(e));
        this.patientSearch.addEventListener("input", (e) => this.onPatientSearch(e));
        
        // Close modal when clicking outside
        window.addEventListener("click", (e) => {
            if (e.target === this.modal) {
                this.closeModalDialog();
            }
        });
        
        // Update display when language changes
        this.doctorLangSelect.addEventListener("change", (e) => {
            this.doctorLang = e.target.value;
            this.boxDoctorLang.textContent = this.getLangName(this.doctorLang);
            this.updateBoxVisibility();
        });
        
        this.patientLangSelect.addEventListener("change", (e) => {
            this.patientLang = e.target.value;
            this.boxPatientLang.textContent = this.getLangName(this.patientLang);
            this.updateBoxVisibility();
        });
        
        // PDF generation buttons
        this.pdfConversationBtn.addEventListener("click", () => this.generatePDF("conversation"));
        this.pdfPatientSummaryBtn.addEventListener("click", () => this.generatePDF("patient_summary"));
        this.pdfResearchBtn.addEventListener("click", () => this.generatePDF("research"));
        
        // Summary panel toggle
        document.getElementById("clinical-summary-header").addEventListener("click", (e) => this.toggleSummaryPanel(e.currentTarget));
        document.getElementById("conclusion-header").addEventListener("click", (e) => this.toggleSummaryPanel(e.currentTarget));
        
        // Summary modal events
        this.closeSummaryModalBtn.addEventListener("click", () => this.closeSummaryModal());
        this.generateSummaryBtn.addEventListener("click", () => this.generateMedicalSummary());
        this.savePdfBtn.addEventListener("click", () => this.savePdfFromModal());
        
        // Close summary modal when clicking outside
        window.addEventListener("click", (e) => {
            if (e.target === this.summaryModal) {
                this.closeSummaryModal();
            }
        });
        document.getElementById("conclusion-header").addEventListener("click", (e) => this.toggleSummaryPanel(e.currentTarget));
        
        // Error modal events
        this.closeErrorModal.addEventListener("click", () => this.hideErrorModal());
        this.errorModalCloseBtn.addEventListener("click", () => this.hideErrorModal());
        window.addEventListener("click", (e) => {
            if (e.target === this.errorModal) {
                this.hideErrorModal();
            }
        });
    }
    
    /**
     * Pre-populate doctor and patient from PCES RAG App URL query parameters.
     * When PCES opens this app with ?doctor=<name>&patient=<name>&patient_id=<id>,
     * skip the manual selection modal and auto-confirm participants.
     */
    _loadParamsFromURL() {
        const params = new URLSearchParams(window.location.search);
        const doctorName  = params.get('doctor')     || '';
        const patientName = params.get('patient')    || '';
        const patientId   = params.get('patient_id') || '';
        const doctorId    = params.get('doctor_id')  || '';

        if (!doctorName || !patientName) return; // nothing to pre-fill

        this.selectedDoctor = {
            first_name: doctorName.split(' ')[0] || doctorName,
            last_name:  doctorName.split(' ').slice(1).join(' ') || '',
            full_name:  doctorName
        };
        this.selectedPatient = {
            patient_id: patientId || null,
            first_name: patientName.split(' ')[0] || patientName,
            last_name:  patientName.split(' ').slice(1).join(' ') || '',
            full_name:  patientName
        };

        // Update header display
        this.currentDoctorName.textContent  = doctorName;
        this.currentPatientName.textContent = patientName;
        if (this.participantInfo) this.participantInfo.style.display = 'flex';

        // Enable start button and update selection button label
        this.startBtn.disabled = false;
        this.selectParticipantsBtn.textContent = '👥 Change Participants';

        // Show a banner so user knows context was passed from PCES
        this._showPCESBanner(doctorName, patientName);

        console.log(`✓ [PCES] Pre-filled — Doctor: ${doctorName}  Patient: ${patientName} (ID: ${patientId || 'n/a'})`);
    }

    /**
     * Show a brief auto-dismissing banner when context is passed from PCES.
     */
    _showPCESBanner(doctorName, patientName) {
        const existing = document.getElementById('pces-context-banner');
        if (existing) existing.remove();

        const banner = document.createElement('div');
        banner.id = 'pces-context-banner';
        banner.style.cssText = [
            'position:fixed', 'top:16px', 'left:50%', 'transform:translateX(-50%)',
            'background:#2563eb', 'color:#fff', 'padding:10px 22px',
            'border-radius:8px', 'font-size:14px', 'font-weight:600',
            'box-shadow:0 4px 12px rgba(0,0,0,0.25)', 'z-index:9999',
            'transition:opacity 0.5s'
        ].join(';');
        banner.textContent = `✅ PCES context loaded — Dr. ${doctorName} / ${patientName}`;
        document.body.appendChild(banner);

        setTimeout(() => { banner.style.opacity = '0'; }, 3500);
        setTimeout(() => { banner.remove(); }, 4100);
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
                this.selectParticipantsBtn.disabled = true;
            }
        } catch (error) {
            console.warn("Could not connect to server:", error);
            this.statusText.textContent = "⚠️ Server Not Available";
            this.selectParticipantsBtn.disabled = true;
        }
    }
    
    /**
     * Handle doctor search input
     */
    async onDoctorSearch(e) {
        const query = e.target.value.trim();
        
        // Clear previous timeout
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }
        
        if (query.length < 2) {
            this.doctorSuggestions.innerHTML = "";
            this.doctorSuggestions.style.display = "none";
            return;
        }
        
        // Debounce search
        this.searchTimeout = setTimeout(async () => {
            try {
                const response = await fetch(`/api/search_doctors?q=${encodeURIComponent(query)}`);
                const data = await response.json();
                
                if (data.success && data.doctors.length > 0) {
                    this.showDoctorSuggestions(data.doctors);
                } else {
                    this.doctorSuggestions.innerHTML = '<div class="no-results">No doctors found</div>';
                    this.doctorSuggestions.style.display = "block";
                }
            } catch (error) {
                console.error("Error searching doctors:", error);
            }
        }, 300);
    }
    
    /**
     * Show doctor suggestions
     */
    showDoctorSuggestions(doctors) {
        this.doctorSuggestions.innerHTML = "";
        this.doctorSuggestions.style.display = "block";
        
        doctors.forEach(doctor => {
            const div = document.createElement("div");
            div.className = "suggestion-item";
            div.textContent = doctor.full_name;
            div.dataset.firstName = doctor.first_name;
            div.dataset.lastName = doctor.last_name;
            div.dataset.fullName = doctor.full_name;
            
            div.addEventListener("click", () => {
                this.selectDoctor(doctor);
            });
            
            this.doctorSuggestions.appendChild(div);
        });
    }
    
    /**
     * Select doctor from suggestions
     */
    selectDoctor(doctor) {
        this.selectedDoctor = {
            first_name: doctor.first_name,
            last_name: doctor.last_name,
            full_name: doctor.full_name
        };
        
        this.doctorSearch.value = doctor.full_name;
        this.doctorSuggestions.innerHTML = "";
        this.doctorSuggestions.style.display = "none";
        
        this.doctorInfo.innerHTML = `
            <strong>${doctor.full_name}</strong><br>
            Doctor from pces_users table
        `;
        
        this.checkModalSelection();
    }
    
    /**
     * Handle patient search input
     */
    async onPatientSearch(e) {
        const query = e.target.value.trim();
        
        // Clear previous timeout
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }
        
        if (query.length < 2) {
            this.patientSuggestions.innerHTML = "";
            this.patientSuggestions.style.display = "none";
            return;
        }
        
        // Debounce search
        this.searchTimeout = setTimeout(async () => {
            try {
                const response = await fetch(`/api/search_patients?q=${encodeURIComponent(query)}`);
                const data = await response.json();
                
                if (data.success && data.patients.length > 0) {
                    this.showPatientSuggestions(data.patients);
                } else {
                    this.patientSuggestions.innerHTML = '<div class="no-results">No patients found</div>';
                    this.patientSuggestions.style.display = "block";
                }
            } catch (error) {
                console.error("Error searching patients:", error);
            }
        }, 300);
    }
    
    /**
     * Show patient suggestions
     */
    showPatientSuggestions(patients) {
        this.patientSuggestions.innerHTML = "";
        this.patientSuggestions.style.display = "block";
        
        patients.forEach(patient => {
            const div = document.createElement("div");
            div.className = "suggestion-item";
            div.textContent = patient.full_name;
            div.dataset.patientId = patient.patient_id;
            div.dataset.firstName = patient.first_name;
            div.dataset.lastName = patient.last_name;
            div.dataset.fullName = patient.full_name;
            
            div.addEventListener("click", () => {
                this.selectPatient(patient);
            });
            
            this.patientSuggestions.appendChild(div);
        });
    }
    
    /**
     * Select patient from suggestions
     */
    selectPatient(patient) {
        this.selectedPatient = {
            patient_id: patient.patient_id,
            first_name: patient.first_name,
            last_name: patient.last_name,
            full_name: patient.full_name
        };
        
        this.patientSearch.value = patient.full_name;
        this.patientSuggestions.innerHTML = "";
        this.patientSuggestions.style.display = "none";
        
        this.patientInfo.innerHTML = `
            <strong>${patient.full_name}</strong><br>
            Patient ID: ${patient.patient_id}
        `;
        
        this.checkModalSelection();
    }
    
    /**
     * Open participant selection modal
     */
    openModal() {
        this.modal.style.display = "block";
        this.modalError.textContent = "";
        this.confirmParticipantsBtn.disabled = true;
        this.doctorSearch.value = "";
        this.patientSearch.value = "";
        this.doctorSuggestions.innerHTML = "";
        this.patientSuggestions.innerHTML = "";
        this.doctorInfo.innerHTML = "";
        this.patientInfo.innerHTML = "";
        this.selectedDoctor = null;
        this.selectedPatient = null;
    }
    
    /**
     * Close participant selection modal
     */
    closeModalDialog() {
        this.modal.style.display = "none";
        this.doctorSuggestions.style.display = "none";
        this.patientSuggestions.style.display = "none";
    }
    
    /**
     * Check if both doctor and patient are selected
     */
    checkModalSelection() {
        const doctorSelected = this.selectedDoctor !== null;
        const patientSelected = this.selectedPatient !== null;
        this.confirmParticipantsBtn.disabled = !(doctorSelected && patientSelected);
    }
    
    /**
     * Confirm participant selection
     */
    confirmParticipants() {
        if (!this.selectedDoctor || !this.selectedPatient) {
            this.modalError.textContent = "Please select both doctor and patient";
            return;
        }
        
        // Update display
        this.currentDoctorName.textContent = this.selectedDoctor.full_name;
        this.currentPatientName.textContent = this.selectedPatient.full_name;
        this.participantInfo.style.display = "flex";
        
        // Enable start button
        this.startBtn.disabled = false;
        this.selectParticipantsBtn.textContent = "👥 Change Participants";
        
        // Close modal
        this.closeModalDialog();
        
        console.log("✓ Participants selected:", this.selectedDoctor.full_name, "↔", this.selectedPatient.full_name);
    }
    
    /**
     * Start recording and streaming audio
     */
    async startRecording() {
        try {
            // Get selected languages
            this.doctorLang = this.doctorLangSelect.value;
            this.patientLang = this.patientLangSelect.value;
            
            // Update display
            this.boxDoctorLang.textContent = this.getLangName(this.doctorLang);
            this.boxPatientLang.textContent = this.getLangName(this.patientLang);
            
            // Log language selection
            if (this.doctorLang === this.patientLang) {
                console.log(`✓ Same language mode: ${this.getLangName(this.doctorLang)} (Box 1 only)`);
            } else {
                console.log(`✓ Translation mode: ${this.getLangName(this.doctorLang)} ↔ ${this.getLangName(this.patientLang)}`);
            }
            
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
    async stopRecording() {
        console.log("⛔ Stopping recording...");
        
        // Stop recording
        this.isRecording = false;
        
        // Capture duration before stopping timer
        const elapsed = Date.now() - this.recordingStartTime;
        const seconds = Math.floor(elapsed / 1000);
        const minutes = Math.floor(seconds / 60);
        const secs = seconds % 60;
        this.conversationDuration = `${minutes}m ${secs}s`;
        
        // Stop media stream
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
        }
        
        // Stop timer
        this.stopTimer();
        
        // Freeze UI - disable all controls
        this.freezeConversation();
        
        // Close WebSocket immediately
        if (this.ws) {
            this.ws.close();
        }
        
        // Wait for backend to save files (2 seconds should be enough)
        console.log("⏳ Waiting for backend to save conversation...");
        setTimeout(async () => {
            try {
                // Show summary modal
                await this.showSummaryModal();
            } catch (error) {
                console.error("❌ Error showing summary modal:", error);
                alert(`Failed to open summary dialog: ${error.message}`);
                this.completionBanner.style.display = "none";
                this.clearBtn.disabled = false;
            }
        }, 2000);  // Wait 2 seconds for backend to finish saving
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
            
            // Send initial configuration with participant info
            const config = {
                doctor_lang: this.doctorLang,
                patient_lang: this.patientLang
            };
            
            // Add participant info if selected
            if (this.selectedDoctor) {
                config.doctor_name = this.selectedDoctor.full_name;
            }
            
            if (this.selectedPatient) {
                config.patient_id = this.selectedPatient.patient_id;
                config.patient_name = this.selectedPatient.full_name;
            }
            
            this.ws.send(JSON.stringify(config));
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
                        console.log("📦 Received boxes update:", {
                            original_length: data.boxes.original?.length,
                            doctor_length: data.boxes.doctor?.length,
                            patient_length: data.boxes.patient?.length,
                            original_preview: data.boxes.original?.substring(0, 100)
                        });
                        this.updateBoxes(data.boxes, data.same_language);
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
                    console.log("📦 Received legacy update");
                    this.updateBoxes(data.boxes);
                    this.conversationData.entries.push(...(data.tokens || []));
                } else if (data.type === "saved") {
                    console.log("✓ Conversation saved to files");
                    
                    // Store the conversation text sent from backend
                    if (data.conversation_text) {
                        console.log("📥 Received conversation text from save event:", data.conversation_text.length, "chars");
                        this.conversationData.original = data.conversation_text;
                        this.conversationData.doctor = data.doctor_text || "";
                        this.conversationData.patient = data.patient_text || "";
                        console.log("💾 Stored conversation data for translation");
                    }
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
        
        // CRITICAL: Use smaller buffer (1024) for lower latency and real-time processing
        // Larger buffers cause timeouts and missed speech detection
        const processor = this.audioContext.createScriptProcessor(1024, 1, 1);
        
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
                    console.log(`🔊 Audio: ${audioChunkCount} chunks (${totalBytesSent} bytes, rate: 16000 Hz, buffer: 1024)`);
                }
                
                // Send PCM16 buffer to server IMMEDIATELY (no buffering)
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
     * Split text into lines for better readability
     */
    splitTextIntoLines(text, maxCharsPerLine = 80) {
        if (!text) return "";
        
        // Split by sentences (. ! ?)
        const sentences = text.split(/(?<=[.!?])\s+/);
        
        let lines = [];
        let currentLine = "";
        
        sentences.forEach(sentence => {
            if ((currentLine + sentence).length > maxCharsPerLine && currentLine.length > 0) {
                lines.push(currentLine.trim());
                currentLine = sentence;
            } else {
                currentLine += (currentLine.length > 0 ? " " : "") + sentence;
            }
        });
        
        if (currentLine.length > 0) {
            lines.push(currentLine.trim());
        }
        
        return lines.join("\n");
    }
    
    /**
     * Update all three boxes with latest content
     */
    updateBoxes(boxes, sameLanguage = false) {
        if (boxes) {
            const original = boxes.original || "[No content]";
            const doctor = boxes.doctor || "[No content]";
            const patient = boxes.patient || "[No content]";
            
            // Format content with speaker highlighting
            const originalHTML = this.formatContentWithSpeakers(original, "original");
            const doctorHTML = this.formatContentWithSpeakers(doctor, "doctor");
            const patientHTML = this.formatContentWithSpeakers(patient, "patient");
            
            // Update content with HTML formatting
            this.boxOriginal.innerHTML = originalHTML;
            this.boxDoctor.innerHTML = doctorHTML;
            this.boxPatient.innerHTML = patientHTML;
            
            // Hide boxes 2 & 3 when both languages are the same
            const doctorContainer = document.getElementById("box-doctor-container");
            const patientContainer = document.getElementById("box-patient-container");
            
            const sameLanguage = this.doctorLang === this.patientLang;
            
            if (sameLanguage) {
                // Same language: only show Box #1
                doctorContainer.classList.add("hidden-box");
                patientContainer.classList.add("hidden-box");
            } else {
                // Different languages: show all boxes for translation
                doctorContainer.classList.remove("hidden-box");
                patientContainer.classList.remove("hidden-box");
            }
            
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
     * Update box visibility based on language selection
     */
    updateBoxVisibility() {
        const doctorContainer = document.getElementById("box-doctor-container");
        const patientContainer = document.getElementById("box-patient-container");
        
        const sameLanguage = this.doctorLang === this.patientLang;
        
        if (sameLanguage) {
            // Same language: only show Box #1
            doctorContainer.classList.add("hidden-box");
            patientContainer.classList.add("hidden-box");
        } else {
            // Different languages: show all boxes for translation
            doctorContainer.classList.remove("hidden-box");
            patientContainer.classList.remove("hidden-box");
        }
    }
    
    /**
     * Format content with speaker highlighting
     */
    formatContentWithSpeakers(text, boxType) {
        if (!text || text === "[No content]") {
            return `<p class="placeholder">${text}</p>`;
        }
        
        // Split by [Doctor] or [Patient] tags and format each line
        let html = text
            .split('\n')
            .map(line => {
                if (!line.trim()) return '';
                
                // Detect speaker from the line
                if (line.includes('[Doctor]:')) {
                    // Replace the tag with colored span and add styling
                    return `<div class="speaker-doctor">${line.replace('[Doctor]:', '<strong>👨‍⚕️ Doctor:</strong>')}</div>`;
                } else if (line.includes('[Patient]:')) {
                    // Replace the tag with colored span and add styling
                    return `<div class="speaker-patient">${line.replace('[Patient]:', '<strong>👤 Patient:</strong>')}</div>`;
                } else {
                    // Plain text line (continuation)
                    return `<div>${line}</div>`;
                }
            })
            .join('');
        
        return html || '<p class="placeholder">[Waiting for content...]</p>';
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
    
    /**
     * Freeze conversation UI after Stop is clicked
     */
    freezeConversation() {
        // Disable controls
        this.startBtn.disabled = true;
        this.stopBtn.disabled = true;
        this.selectParticipantsBtn.disabled = true;
        this.doctorLangSelect.disabled = true;
        this.patientLangSelect.disabled = true;
        
        // Update status
        this.statusText.textContent = "Processing...";
        this.statusText.classList.remove("recording");
        
        // Show completion banner temporarily
        this.completionBanner.style.display = "block";
        this.bannerText.textContent = "✅ Conversation completed. Opening summary...";
        
        this.conversationCompleted = true;
        console.log("🔒 Conversation frozen");
    }
    
    /**
     * Process post-recording: Call backend for transcript processing
     */
    async processPostRecording() {
        try {
            this.bannerText.textContent = "Processing transcript and generating summary...";
            
            // Prepare conversation data from current boxes
            const conversationPayload = {
                transcript: this.conversationData.original,
                doctor_name: this.selectedDoctor?.full_name || "Doctor",
                patient_name: this.selectedPatient?.full_name || "Patient",
                patient_id: this.selectedPatient?.patient_id || null,
                doctor_lang: this.doctorLang,
                patient_lang: this.patientLang,
                duration: this.conversationDuration,
                session_date: new Date().toISOString()
            };
            
            console.log("📤 Sending to backend for processing...", conversationPayload);
            
            // Call backend endpoint
            const response = await fetch("/api/transcribe_doctor_patient_conversation", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(conversationPayload)
            });
            
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || "Backend processing failed");
            }
            
            // Store backend response
            this.postRecordingData = data.conversation_data;
            
            // Update views with processed data
            this.constructPostRecordingViews();
            
            // Display summary and conclusion
            this.displaySummaryAndConclusion();
            
            // Show PDF generation section
            this.pdfSection.style.display = "block";
            
            // Update banner
            this.bannerText.textContent = "✅ Medical documentation ready. You can now generate PDFs.";
            this.statusText.textContent = "✅ Completed";
            
            // Enable clear button
            this.clearBtn.disabled = false;
            
            console.log("✅ Post-recording processing complete");
            
        } catch (error) {
            console.error("❌ Post-recording processing error:", error);
            this.showErrorModal(
                "Processing Error",
                `Failed to process conversation: ${error.message}`,
                true,
                () => this.processPostRecording()
            );
        }
    }
    
    /**
     * Construct post-recording views from backend data
     */
    constructPostRecordingViews() {
        const data = this.postRecordingData;
        
        if (!data || !data.transcript) {
            console.warn("No transcript data available");
            return;
        }
        
        // Build Original Conversation with timestamps
        let originalHTML = "";
        data.transcript.forEach((entry, index) => {
            const speaker = entry.role === "Doctor" ? "👨‍⚕️ Doctor" : "👤 Patient";
            const speakerClass = entry.role === "Doctor" ? "speaker-doctor" : "speaker-patient";
            const timestamp = entry.start ? `<span class="timestamp">[${entry.start}]</span>` : "";
            originalHTML += `<div class="${speakerClass}">${timestamp} <strong>${speaker}:</strong> ${entry.text}</div>`;
        });
        this.boxOriginal.innerHTML = originalHTML || '<p class="placeholder">No transcript available</p>';
        
        // Build Doctor View (English only, full transcript)
        let doctorHTML = "";
        data.transcript.forEach((entry) => {
            const speaker = entry.role === "Doctor" ? "👨‍⚕️ Doctor" : "👤 Patient";
            const speakerClass = entry.role === "Doctor" ? "speaker-doctor" : "speaker-patient";
            // Doctor view is always in English, using the text as-is
            doctorHTML += `<div class="${speakerClass}"><strong>${speaker}:</strong> ${entry.text}</div>`;
        });
        this.boxDoctor.innerHTML = doctorHTML || '<p class="placeholder">No content</p>';
        
        // Build Patient View (Patient's selected language)
        let patientHTML = "";
        data.transcript.forEach((entry) => {
            const speaker = entry.role === "Doctor" ? "👨‍⚕️ Doctor" : "👤 Patient";
            const speakerClass = entry.role === "Doctor" ? "speaker-doctor" : "speaker-patient";
            // Use translated text if available and different language
            const displayText = data.translated && this.doctorLang !== this.patientLang ? entry.text : entry.text;
            patientHTML += `<div class="${speakerClass}"><strong>${speaker}:</strong> ${displayText}</div>`;
        });
        this.boxPatient.innerHTML = patientHTML || '<p class="placeholder">No content</p>';
        
        console.log("📋 Post-recording views constructed");
    }
    
    /**
     * Display summary and conclusion panels
     */
    displaySummaryAndConclusion() {
        const data = this.postRecordingData;
        
        if (!data) return;
        
        // Display clinical summary
        if (data.summary) {
            this.clinicalSummaryContent.innerHTML = `<p>${data.summary.replace(/\n/g, '<br>')}</p>`;
        } else {
            this.clinicalSummaryContent.innerHTML = '<p class="placeholder">Summary not available</p>';
        }
        
        // Display conclusion
        if (data.conclusion) {
            this.conclusionContent.innerHTML = `<p>${data.conclusion.replace(/\n/g, '<br>')}</p>`;
        } else {
            this.conclusionContent.innerHTML = '<p class="placeholder">Conclusion not available</p>';
        }
        
        // Show summary section
        this.medicalSummarySection.style.display = "block";
        
        console.log("📊 Summary and conclusion displayed");
    }
    
    /**
     * Toggle summary panel collapse/expand
     */
    toggleSummaryPanel(header) {
        const content = header.nextElementSibling;
        const toggleBtn = header.querySelector(".toggle-btn");
        
        if (content.style.display === "none") {
            content.style.display = "block";
            toggleBtn.textContent = "▼";
        } else {
            content.style.display = "none";
            toggleBtn.textContent = "▶";
        }
    }
    
    /**
     * Generate and upload PDF
     */
    async generatePDF(pdfType) {
        try {
            // Validate metadata
            if (!this.validateMetadata()) {
                return;
            }
            
            // Disable button and show status
            const button = pdfType === "conversation" ? this.pdfConversationBtn :
                          pdfType === "patient_summary" ? this.pdfPatientSummaryBtn :
                          this.pdfResearchBtn;
            
            button.disabled = true;
            this.pdfStatus.textContent = `Generating ${pdfType} PDF...`;
            this.pdfStatus.className = "pdf-status processing";
            
            // Prepare metadata
            const metadata = {
                doctor_name: this.selectedDoctor?.full_name || "Doctor",
                patient_name: this.selectedPatient?.full_name || "Patient",
                patient_id: this.selectedPatient?.patient_id || null,
                session_date: new Date().toISOString(),
                duration: this.conversationDuration,
                language: this.postRecordingData?.language || this.patientLang,
                translated: this.postRecordingData?.translated || false
            };
            
            // Prepare payload based on PDF type
            const payload = {
                pdf_type: pdfType,
                metadata: metadata
            };
            
            if (pdfType === "conversation") {
                payload.transcript = this.postRecordingData?.transcript || [];
                payload.raw_transcript = this.postRecordingData?.raw_transcript || this.conversationData.original;
            } else if (pdfType === "patient_summary") {
                payload.summary = this.postRecordingData?.summary || "";
                payload.conclusion = this.postRecordingData?.conclusion || "";
                payload.transcript = this.postRecordingData?.transcript || [];
            } else if (pdfType === "research") {
                payload.summary = this.postRecordingData?.summary || "";
                payload.conclusion = this.postRecordingData?.conclusion || "";
                payload.patient_problem = this.postRecordingData?.summary || "Medical consultation";
            }
            
            // Call backend to generate and upload PDF
            const response = await fetch("/api/generate_pdf", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });
            
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || "PDF generation failed");
            }
            
            // Show success with URL (Azure blob or local fallback)
            const pdfUrl = data.pdf_url || data.blob_url;
            const isAzure = data.azure_available !== false && data.blob_url;
            this.pdfStatus.textContent = isAzure
                ? `✅ PDF uploaded to Azure: ${pdfUrl}`
                : `✅ PDF ready — ${data.message || "downloading locally"}`;
            this.pdfStatus.className = "pdf-status success";

            // Open/download the PDF
            if (pdfUrl) {
                window.open(pdfUrl, "_blank");
            }
            
            // Re-enable button after delay
            setTimeout(() => {
                button.disabled = false;
                this.pdfStatus.textContent = "";
            }, 5000);
            
            console.log(`✅ ${pdfType} PDF generated:`, data.pdf_url || data.blob_url);
            
        } catch (error) {
            console.error(`❌ PDF generation error (${pdfType}):`, error);
            this.pdfStatus.textContent = `❌ Error: ${error.message}`;
            this.pdfStatus.className = "pdf-status error";
            
            // Re-enable button
            setTimeout(() => {
                if (pdfType === "conversation") this.pdfConversationBtn.disabled = false;
                else if (pdfType === "patient_summary") this.pdfPatientSummaryBtn.disabled = false;
                else this.pdfResearchBtn.disabled = false;
            }, 3000);
        }
    }
    
    /**
     * Show summary modal after recording stops
     */
    async showSummaryModal() {
        console.log("=".repeat(80));
        console.log("📋📋📋 SUMMARY MODAL OPENING - START 📋📋📋");
        console.log("=".repeat(80));
        
        console.log("📊 Current conversationData state:");
        console.log("   - original length:", this.conversationData.original?.length);
        console.log("   - original content:", this.conversationData.original);
        console.log("   - doctor length:", this.conversationData.doctor?.length);
        console.log("   - patient length:", this.conversationData.patient?.length);
        
        // DEBUG: Check what's in the box-original DOM element
        console.log("=".repeat(80));
        console.log("🔍 Checking box-original DOM element:");
        console.log("=".repeat(80));
        if (this.boxOriginal) {
            console.log("   ✅ Element exists:", !!this.boxOriginal);
            console.log("   📏 innerHTML length:", this.boxOriginal.innerHTML?.length);
            console.log("   📏 textContent length:", this.boxOriginal.textContent?.length);
            console.log("   📝 textContent:");
            console.log(this.boxOriginal.textContent);
            console.log("   🎨 innerHTML preview:");
            console.log(this.boxOriginal.innerHTML?.substring(0, 500));
        } else {
            console.error("   ❌ boxOriginal element is NULL!");
        }
        console.log("=".repeat(80));
        
        try {
            // Check if modal elements exist
            if (!this.summaryModal) {
                throw new Error("Summary modal element not found");
            }
            
            // Populate participant info
            if (this.summaryDoctorName) {
                this.summaryDoctorName.textContent = this.selectedDoctor?.full_name || "Doctor";
            }
            if (this.summaryPatientName) {
                this.summaryPatientName.textContent = this.selectedPatient?.full_name || "Patient";
            }
            
            const now = new Date();
            if (this.summaryDate) {
                this.summaryDate.textContent = now.toLocaleString();
            }
            
            if (this.summaryLanguage) {
                this.summaryLanguage.textContent = this.getLangName(this.doctorLang);
            }
            if (this.summarySegments) {
                // Count actual segments by parsing the conversation text
                const segments = this.parseConversationSegments();
                this.summarySegments.textContent = segments.length;
            }
            
            // Populate transcript editor with loading state FIRST
            const needsTranslation = this.doctorLang !== 'en' || this.patientLang !== 'en';
            if (this.transcriptEditor) {
                if (needsTranslation) {
                    // Will be populated after translation
                    this.transcriptEditor.value = "Translating to English...";
                } else {
                    this.transcriptEditor.value = this.getTranscriptText();
                }
            }
            
            // Populate conversation segments
            if (this.conversationSegments) {
                if (needsTranslation) {
                    // Show loading state
                    this.conversationSegments.innerHTML = '<div style="padding: 20px; text-align: center; color: #3b82f6;"><div class="spinner"></div> Translating to English...</div>';
                    
                    // Translate segments to English (this will also update transcript editor)
                    await this.translateAndPopulateSegments();
                } else {
                    this.populateConversationSegments();
                }
            }
            
            // Show sections immediately in the modal
            if (this.medicalSummaryModalSection) {
                this.medicalSummaryModalSection.style.display = "block";
            }
            if (this.conclusionModalSection) {
                this.conclusionModalSection.style.display = "block";
            }
            if (this.savePdfBtn) {
                this.savePdfBtn.disabled = true;
            }
            
            // Hide banner since we're showing modal
            if (this.completionBanner) {
                this.completionBanner.style.display = "none";
            }
            
            // Show modal
            this.summaryModal.style.display = "block";
            
            console.log("✅ Summary modal opened successfully");
            
        } catch (error) {
            console.error("❌ Error in showSummaryModal:", error);
            console.error("Modal elements check:", {
                summaryModal: !!this.summaryModal,
                summaryDoctorName: !!this.summaryDoctorName,
                transcriptEditor: !!this.transcriptEditor
            });
            throw error;
        }
    }
    
    /**
     * Close summary modal
     */
    closeSummaryModal() {
        this.summaryModal.style.display = "none";
    }
    
    /**
     * Translate and populate segments to English
     */
    async translateAndPopulateSegments() {
        try {
            // Read directly from the displayed box
            const transcriptText = this.getTranscriptText();
            
            console.log("📝 Transcript text to translate:");
            console.log("   Length:", transcriptText?.length);
            console.log("   Preview:", transcriptText?.substring(0, 300));
            
            if (!transcriptText || transcriptText.trim() === "" || transcriptText === "[No content]" || transcriptText.length < 10) {
                throw new Error("No conversation content available to translate");
            }
            
            console.log("🌐 Translating conversation to English...");
            
            // Call backend to translate
            const response = await fetch("/api/translate_to_english", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    text: transcriptText,
                    source_language: this.doctorLang !== 'en' ? this.doctorLang : this.patientLang
                })
            });
            
            const data = await response.json();
            
            console.log("📥 Translation response:", data);
            
            if (!data.success) {
                throw new Error(data.error || "Translation failed");
            }
            
            // Store translated text
            this.translatedTranscript = data.translated_text;
            
            console.log("✅ Translated text length:", this.translatedTranscript?.length);
            console.log("📄 Translated preview:", this.translatedTranscript?.substring(0, 200));
            
            // Update transcript editor with English translation
            if (this.transcriptEditor) {
                this.transcriptEditor.value = this.translatedTranscript;
            }
            
            // Parse and display English segments
            this.populateTranslatedSegments(this.translatedTranscript);
            
            console.log("✅ Translation complete");
            
        } catch (error) {
            console.error("❌ Translation error:", error);
            this.conversationSegments.innerHTML = `<div style="padding: 20px; text-align: center; color: #ef4444;">Translation failed: ${error.message}<br><button onclick="location.reload()" class="btn btn-sm" style="margin-top: 10px;">Reload</button></div>`;
            
            // Show error in transcript editor too
            if (this.transcriptEditor) {
                this.transcriptEditor.value = `Translation Error: ${error.message}`;
            }
        }
    }
    
    /**
     * Populate segments from translated English text
     */
    populateTranslatedSegments(translatedText) {
        console.log("🔧 populateTranslatedSegments called");
        console.log("📄 Full translated text:", translatedText);
        console.log("📏 Translated text length:", translatedText?.length);
        
        this.conversationSegments.innerHTML = "";
        
        // Parse the translated text for segments
        const lines = translatedText.split('\n');
        console.log("📋 Split into", lines.length, "lines");
        console.log("📋 Lines:", lines);
        
        const segments = [];
        
        let currentSpeaker = null;
        let currentText = "";
        
        lines.forEach((line, idx) => {
            console.log(`  Line ${idx}:`, line);
            if (line.startsWith('[Doctor]:') || line.toLowerCase().startsWith('doctor:')) {
                console.log(`    ✓ Found Doctor line`);
                if (currentSpeaker && currentText.trim()) {
                    segments.push({ speaker: currentSpeaker, text: currentText.trim() });
                }
                currentSpeaker = 'Doctor';
                currentText = line.replace(/\[?Doctor\]?:/i, '').trim();
            } else if (line.startsWith('[Patient]:') || line.toLowerCase().startsWith('patient:')) {
                console.log(`    ✓ Found Patient line`);
                if (currentSpeaker && currentText.trim()) {
                    segments.push({ speaker: currentSpeaker, text: currentText.trim() });
                }
                currentSpeaker = 'Patient';
                currentText = line.replace(/\[?Patient\]?:/i, '').trim();
            } else if (line.trim()) {
                console.log(`    → Continuing text`);
                currentText += ' ' + line.trim();
            }
        });
        
        if (currentSpeaker && currentText.trim()) {
            segments.push({ speaker: currentSpeaker, text: currentText.trim() });
        }
        
        console.log("✅ Parsed segments:", segments.length);
        console.log("📊 Segments:", segments);
        
        if (segments.length === 0) {
            console.error("❌ No segments found in translated text");
            this.conversationSegments.innerHTML = '<div style="padding: 20px; text-align: center; color: #64748b;">No segments found in translated text</div>';
            return;
        }
        
        console.log("🎨 Creating segment DOM elements...");
        
        // Display segments
        segments.forEach((entry, index) => {
            console.log(`  Creating segment ${index + 1}:`, entry.speaker, "-", entry.text.substring(0, 50) + "...");
            
            const segmentDiv = document.createElement("div");
            const speakerLower = entry.speaker.toLowerCase();
            segmentDiv.className = `segment-item ${speakerLower}`;
            
            const headerDiv = document.createElement("div");
            headerDiv.className = "segment-header";
            
            const speakerSpan = document.createElement("span");
            speakerSpan.className = `segment-speaker ${speakerLower}`;
            speakerSpan.textContent = entry.speaker;
            
            const translatedBadge = document.createElement("span");
            translatedBadge.className = "segment-confidence";
            translatedBadge.textContent = "(Translated to English)";
            translatedBadge.style.color = "#3b82f6";
            translatedBadge.style.fontWeight = "600";
            
            headerDiv.appendChild(speakerSpan);
            headerDiv.appendChild(translatedBadge);
            
            const textDiv = document.createElement("div");
            textDiv.className = "segment-text";
            textDiv.textContent = entry.text;
            
            segmentDiv.appendChild(headerDiv);
            segmentDiv.appendChild(textDiv);
            
            this.conversationSegments.appendChild(segmentDiv);
            console.log(`  ✅ Appended segment ${index + 1} to DOM`);
        });
        
        console.log("🎉 All segments appended to conversationSegments container");
        console.log("📦 Container element:", this.conversationSegments);
        console.log("👶 Container children count:", this.conversationSegments.children.length);
    }
    
    /**
     * Close summary modal
     */
    closeSummaryModal_old() {
        this.summaryModal.style.display = "none";
    }
    
    /**
     * Parse conversation segments from the appropriate box
     * Always use Box 1 (original) for consistency
     */
    parseConversationSegments() {
        // Always use Box 1 (original) for consistency
        const text = this.conversationData.original || "";
        
        // Parse segments from text with [Doctor]: or [Patient]: format
        const segments = [];
        const lines = text.split('\n');
        
        let currentSpeaker = null;
        let currentText = "";
        
        lines.forEach(line => {
            if (line.startsWith('[Doctor]:')) {
                // Save previous segment
                if (currentSpeaker && currentText.trim()) {
                    segments.push({
                        speaker: currentSpeaker,
                        text: currentText.trim(),
                        start: null,
                        end: null
                    });
                }
                // Start new Doctor segment
                currentSpeaker = 'Doctor';
                currentText = line.replace('[Doctor]:', '').trim();
            } else if (line.startsWith('[Patient]:')) {
                // Save previous segment
                if (currentSpeaker && currentText.trim()) {
                    segments.push({
                        speaker: currentSpeaker,
                        text: currentText.trim(),
                        start: null,
                        end: null
                    });
                }
                // Start new Patient segment
                currentSpeaker = 'Patient';
                currentText = line.replace('[Patient]:', '').trim();
            } else if (line.trim()) {
                // Continue current segment
                currentText += ' ' + line.trim();
            }
        });
        
        // Add final segment
        if (currentSpeaker && currentText.trim()) {
            segments.push({
                speaker: currentSpeaker,
                text: currentText.trim(),
                start: null,
                end: null
            });
        }
        
        return segments;
    }
    
    /**
     * Get transcript text from appropriate box
     */
    getTranscriptText() {
        console.log("🔍 getTranscriptText called");
        
        // Read directly from the DOM element that's displayed on screen
        if (this.boxOriginal && this.boxOriginal.textContent) {
            const text = this.boxOriginal.textContent.trim();
            console.log("   → Reading from box-original DOM element");
            console.log("   → Text length:", text.length);
            console.log("   → Preview:", text.substring(0, 200));
            return text;
        }
        
        // Fallback to conversationData
        console.log("   → Fallback to conversationData");
        console.log("   Doctor lang:", this.doctorLang);
        console.log("   Patient lang:", this.patientLang);
        console.log("   conversationData.original:", this.conversationData.original?.substring(0, 300) + "...");
        console.log("   conversationData.original length:", this.conversationData.original?.length);
        
        const sameLanguage = this.doctorLang === this.patientLang;
        
        if (sameLanguage) {
            console.log("   → Using conversationData.original (same language)");
            return this.conversationData.original || "";
        }
        
        console.log("   → Using conversationData.original (different languages)");
        return this.conversationData.original || "";
    }
    
    /**
     * Populate conversation segments display
     */
    populateConversationSegments() {
        this.conversationSegments.innerHTML = "";
        
        // Get parsed segments
        const segments = this.parseConversationSegments();
        
        if (segments.length === 0) {
            this.conversationSegments.innerHTML = '<div style="padding: 20px; text-align: center; color: #64748b;">No conversation segments found</div>';
            return;
        }
        
        segments.forEach((entry, index) => {
            // Skip entries without speaker or text
            if (!entry.speaker || !entry.text) {
                console.warn("Skipping entry without speaker or text:", entry);
                return;
            }
            
            const segmentDiv = document.createElement("div");
            const speakerLower = (entry.speaker || "unknown").toLowerCase();
            segmentDiv.className = `segment-item ${speakerLower}`;
            
            const headerDiv = document.createElement("div");
            headerDiv.className = "segment-header";
            
            const speakerSpan = document.createElement("span");
            speakerSpan.className = `segment-speaker ${speakerLower}`;
            speakerSpan.textContent = entry.speaker || "Unknown";
            
            headerDiv.appendChild(speakerSpan);
            
            const textDiv = document.createElement("div");
            textDiv.className = "segment-text";
            textDiv.textContent = entry.text;
            
            segmentDiv.appendChild(headerDiv);
            segmentDiv.appendChild(textDiv);
            
            this.conversationSegments.appendChild(segmentDiv);
        });
    }
    
    /**
     * Format transcript for editor
     */
    formatTranscriptForEditor() {
        let transcript = "";
        this.conversationData.entries.forEach(entry => {
            // Skip entries without speaker or text
            if (!entry.speaker || !entry.text) {
                return;
            }
            transcript += `${entry.speaker}: ${entry.text}\n\n`;
        });
        return transcript.trim();
    }
    
    /**
     * Generate medical summary and conclusion
     */
    async generateMedicalSummary() {
        try {
            this.generateSummaryBtn.disabled = true;
            this.generatingIndicator.style.display = "flex";
            
            // Get edited transcript from textarea
            const transcript = this.transcriptEditor.value;
            
            // Prepare payload
            const payload = {
                transcript: transcript,
                doctor_name: this.selectedDoctor?.full_name || "Doctor",
                patient_name: this.selectedPatient?.full_name || "Patient",
                patient_id: this.selectedPatient?.patient_id || null,
                doctor_lang: this.doctorLang,
                patient_lang: this.patientLang,
                duration: this.conversationDuration,
                session_date: new Date().toISOString()
            };
            
            console.log("📤 Generating medical summary...", payload);
            
            // Call backend endpoint
            const response = await fetch("/api/transcribe_doctor_patient_conversation", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });
            
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || "Backend processing failed");
            }
            
            // Store response
            this.postRecordingData = data.conversation_data;
            
            // Populate summary and conclusion editors
            this.summaryEditor.value = data.conversation_data.summary;
            this.conclusionEditor.value = data.conversation_data.conclusion;
            
            // Show sections
            this.medicalSummaryModalSection.style.display = "block";
            this.conclusionModalSection.style.display = "block";
            
            // Enable PDF save button
            this.savePdfBtn.disabled = false;
            
            console.log("✅ Medical summary generated");
            
        } catch (error) {
            console.error("❌ Error generating summary:", error);
            alert(`Failed to generate medical summary: ${error.message}`);
        } finally {
            this.generateSummaryBtn.disabled = false;
            this.generatingIndicator.style.display = "none";
        }
    }
    
    /**
     * Save PDF from modal
     */
    async savePdfFromModal() {
        try {
            this.savePdfBtn.disabled = true;
            this.savePdfBtn.textContent = "💾 Generating PDF...";
            
            // Get edited content
            const transcript = this.transcriptEditor.value;
            const summary = this.summaryEditor.value;
            const conclusion = this.conclusionEditor.value;
            
            // Parse transcript into segments if it contains speaker markers
            const segments = this.parseConversationSegments();
            
            // Prepare PDF payload matching backend PDFPayload model
            const pdfPayload = {
                pdf_type: "conversation",
                raw_transcript: transcript,
                summary: summary || null,
                conclusion: conclusion || null,
                metadata: {
                    doctor_name: this.selectedDoctor?.full_name || "Doctor",
                    patient_name: this.selectedPatient?.full_name || "Patient",
                    session_date: new Date().toISOString(),
                    duration: this.conversationDuration,
                    doctor_lang: this.doctorLang,
                    patient_lang: this.patientLang
                }
            };
            
            console.log("📤 Generating PDF...", pdfPayload);
            
            const response = await fetch("/api/generate_pdf", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(pdfPayload)
            });
            
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || "PDF generation failed");
            }
            
            // Use pdf_url (works for both Azure blob URL and local fallback token URL)
            const downloadUrl = data.pdf_url || data.blob_url || data.local_path;
            if (downloadUrl) {
                const a = document.createElement("a");
                a.href = downloadUrl;
                a.download = data.filename || `CONVERSATION-${Date.now()}.pdf`;
                a.target = "_blank";
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            }
            
            console.log("✅ PDF saved and downloaded");
            
            // Close modal
            this.closeSummaryModal();
            
            // Show success message
            alert("PDF generated and downloaded successfully!");
            
        } catch (error) {
            console.error("❌ PDF generation error:", error);
            alert(`Failed to generate PDF: ${error.message}`);
        } finally {
            this.savePdfBtn.disabled = false;
            this.savePdfBtn.textContent = "💾 Save as PDF";
        }
    }
    
    /**
     * Validate metadata before PDF upload
     */
    validateMetadata() {
        const required = [
            { field: "doctor_name", value: this.selectedDoctor?.full_name },
            { field: "patient_name", value: this.selectedPatient?.full_name },
            { field: "session_date", value: new Date().toISOString() },
            { field: "duration", value: this.conversationDuration }
        ];
        
        const missing = required.filter(r => !r.value);
        
        if (missing.length > 0) {
            this.showErrorModal(
                "Missing Metadata",
                `Cannot upload PDF. Missing required fields: ${missing.map(m => m.field).join(", ")}`,
                false
            );
            return false;
        }
        
        return true;
    }
    
    /**
     * Show error modal
     */
    showErrorModal(title, message, showRetry = false, retryCallback = null) {
        this.errorModalTitle.textContent = title;
        this.errorModalMessage.textContent = message;
        
        if (showRetry && retryCallback) {
            this.errorModalRetryBtn.style.display = "inline-block";
            this.errorModalRetryBtn.onclick = () => {
                this.hideErrorModal();
                retryCallback();
            };
        } else {
            this.errorModalRetryBtn.style.display = "none";
        }
        
        this.errorModal.style.display = "block";
    }
    
    /**
     * Hide error modal
     */
    hideErrorModal() {
        this.errorModal.style.display = "none";
    }
}

// Initialize app when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
    console.log("🚀 Initializing Doctor-Patient Translator App");
    window.app = new DoctorPatientApp();
});
