class WhisperApp {
    constructor() {
        this.whisper = null;
        this.currentAudioBlob = null;
        this.init();
    }

    init() {
        // Initialize with placeholder API key - user needs to set their own
        this.whisper = new WhisperModule('your-openai-api-key-here');
        
        this.recordBtn = document.getElementById('recordBtn');
        this.transcribeBtn = document.getElementById('transcribeBtn');
        this.status = document.getElementById('status');
        this.result = document.getElementById('transcriptionResult');

        this.recordBtn.addEventListener('click', () => this.toggleRecording());
        this.transcribeBtn.addEventListener('click', () => this.transcribeAudio());
    }

    async toggleRecording() {
        if (!this.whisper.isRecording) {
            const result = await this.whisper.startRecording();
            if (result.success) {
                this.recordBtn.textContent = 'Stop Recording';
                this.recordBtn.style.background = '#27ae60';
                this.status.textContent = '🔴 Recording... Click stop when done';
                this.status.className = 'status recording';
                this.transcribeBtn.disabled = true;
            } else {
                this.status.textContent = `Error: ${result.error}`;
            }
        } else {
            const result = await this.whisper.stopRecording();
            if (result.success) {
                this.currentAudioBlob = result.audioBlob;
                this.recordBtn.textContent = 'Start Recording';
                this.recordBtn.style.background = '#e74c3c';
                this.status.textContent = '✅ Recording complete. Ready to transcribe.';
                this.status.className = 'status ready';
                this.transcribeBtn.disabled = false;
            }
        }
    }

    async transcribeAudio() {
        if (!this.currentAudioBlob) return;
        
        this.status.textContent = '⏳ Transcribing audio...';
        this.transcribeBtn.disabled = true;
        
        const result = await this.whisper.transcribe(this.currentAudioBlob);
        
        if (result.success) {
            this.result.textContent = result.text;
            this.status.textContent = '✅ Transcription complete!';
        } else {
            this.result.textContent = `Error: ${result.error}`;
            this.status.textContent = '❌ Transcription failed.';
        }
        
        this.transcribeBtn.disabled = false;
    }
}

// Initialize app when page loads
document.addEventListener('DOMContentLoaded', () => {
    new WhisperApp();
});