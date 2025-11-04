/**
 * Audio Interview Helper - Client-side TTS/STT using Browser APIs
 * No OpenAI API key needed - uses native browser capabilities
 */

class AudioInterviewHelper {
    constructor() {
        this.synth = window.speechSynthesis;
        this.recognition = null;
        this.isSupported = this.checkSupport();
    }

    checkSupport() {
        const ttsSupported = 'speechSynthesis' in window;
        const sttSupported = 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
        
        if (!ttsSupported || !sttSupported) {
            console.warn('Audio features not fully supported in this browser');
        }
        
        return { tts: ttsSupported, stt: sttSupported };
    }

    /**
     * Generate TTS audio for question (client-side)
     */
    async speakQuestion(questionText, voiceOptions = {}) {
        return new Promise((resolve, reject) => {
            if (!this.isSupported.tts) {
                reject(new Error('TTS not supported in this browser'));
                return;
            }

            // Cancel any ongoing speech
            this.synth.cancel();

            const utterance = new SpeechSynthesisUtterance(questionText);
            
            // Set voice options
            utterance.rate = voiceOptions.rate || 1.0;
            utterance.pitch = voiceOptions.pitch || 1.0;
            utterance.volume = voiceOptions.volume || 1.0;

            // Try to select a specific voice if available
            if (voiceOptions.voiceName) {
                const voices = this.synth.getVoices();
                const voice = voices.find(v => v.name.includes(voiceOptions.voiceName));
                if (voice) utterance.voice = voice;
            }

            utterance.onend = () => resolve();
            utterance.onerror = (error) => reject(error);

            this.synth.speak(utterance);
        });
    }

    /**
     * Stop current speech
     */
    stopSpeaking() {
        this.synth.cancel();
    }

    /**
     * Record audio and get transcription (client-side STT)
     */
    async transcribeAudio(audioBlob, language = 'en-US') {
        return new Promise((resolve, reject) => {
            if (!this.isSupported.stt) {
                // Fallback: return placeholder
                resolve({
                    text: "[STT not supported - please provide text manually]",
                    confidence: 0.0
                });
                return;
            }

            // For now, return audio URL for client to transcribe
            // Full STT implementation requires Web Speech API setup
            const audioUrl = URL.createObjectURL(audioBlob);
            
            resolve({
                audioUrl: audioUrl,
                message: "Audio recorded. Use Web Speech API or manual transcription."
            });
        });
    }

    /**
     * Start real-time voice recording with live transcription
     */
    startRecording(onTranscript, onError, language = 'en-US') {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        
        if (!SpeechRecognition) {
            onError(new Error('Speech recognition not supported'));
            return null;
        }

        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = language;

        recognition.onresult = (event) => {
            let interimTranscript = '';
            let finalTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript + ' ';
                } else {
                    interimTranscript += transcript;
                }
            }

            if (onTranscript) {
                onTranscript({
                    interim: interimTranscript,
                    final: finalTranscript.trim()
                });
            }
        };

        recognition.onerror = (error) => {
            if (onError) onError(error);
        };

        recognition.start();
        this.recognition = recognition;
        
        return recognition;
    }

    /**
     * Stop current recording
     */
    stopRecording() {
        if (this.recognition) {
            this.recognition.stop();
            this.recognition = null;
        }
    }

    /**
     * Get available TTS voices
     */
    getAvailableVoices() {
        if (!this.isSupported.tts) return [];

        let voices = this.synth.getVoices();
        
        // If voices not loaded yet, wait
        if (voices.length === 0) {
            this.synth.onvoiceschanged = () => {
                voices = this.synth.getVoices();
            };
        }

        return voices.map(v => ({
            name: v.name,
            lang: v.lang,
            default: v.default
        }));
    }
}

// Usage Example
if (typeof window !== 'undefined') {
    window.AudioInterviewHelper = AudioInterviewHelper;
    
    // Example usage:
    /*
    const audioHelper = new AudioInterviewHelper();
    
    // Generate TTS for a question
    audioHelper.speakQuestion("Tell me about a challenging project you worked on.")
        .then(() => console.log('Question read'))
        .catch(err => console.error('TTS error:', err));
    
    // Start recording with live transcription
    const recognition = audioHelper.startRecording(
        (result) => console.log('Transcript:', result.final || result.interim),
        (error) => console.error('Recording error:', error)
    );
    
    // Stop recording
    setTimeout(() => audioHelper.stopRecording(), 5000);
    */
}
