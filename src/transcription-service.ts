interface TranscriptionSettings {
	transcriptionService: 'web-speech-api' | 'whisper-api';
	whisperApiKey: string;
	language: string;
	includeTimestamps: boolean;
}

export class TranscriptionService {
	private settings: TranscriptionSettings;
	private recognition: any = null;
	private transcript: string = '';
	private isListening: boolean = false;
	private onTranscriptUpdate?: (transcript: string) => void;
	private onError?: (error: string) => void;

	constructor(settings: TranscriptionSettings) {
		this.settings = settings;
	}

	async startRealTimeTranscription(
		onUpdate: (transcript: string) => void,
		onError: (error: string) => void
	): Promise<void> {
		this.onTranscriptUpdate = onUpdate;
		this.onError = onError;

		if (this.settings.transcriptionService === 'web-speech-api') {
			await this.startWebSpeechAPI();
		} else {
			// Whisper APIはリアルタイム転写非対応なので、後処理で行う
			throw new Error('Whisper APIはリアルタイム転写に対応していません。録音後にトランスクリプションを実行します。');
		}
	}

	private async startWebSpeechAPI(): Promise<void> {
		// Web Speech APIをチェック
		const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
		
		if (!SpeechRecognition) {
			throw new Error('このブラウザはWeb Speech APIに対応していません。Chromeをご使用ください。');
		}

		this.recognition = new SpeechRecognition();
		this.recognition.continuous = true;
		this.recognition.interimResults = true;
		this.recognition.lang = this.settings.language;

		this.transcript = '';

		this.recognition.onresult = (event: any) => {
			let interimTranscript = '';
			let finalTranscript = '';

			for (let i = event.resultIndex; i < event.results.length; i++) {
				const transcriptPiece = event.results[i][0].transcript;
				if (event.results[i].isFinal) {
					finalTranscript += transcriptPiece + ' ';
				} else {
					interimTranscript += transcriptPiece;
				}
			}

			if (finalTranscript) {
				const timestamp = this.settings.includeTimestamps ? 
					`[${this.getCurrentTimestamp()}] ` : '';
				this.transcript += timestamp + finalTranscript.trim() + '\n\n';
				
				if (this.onTranscriptUpdate) {
					this.onTranscriptUpdate(this.transcript + (interimTranscript ? `*${interimTranscript}*` : ''));
				}
			} else if (interimTranscript && this.onTranscriptUpdate) {
				this.onTranscriptUpdate(this.transcript + `*${interimTranscript}*`);
			}
		};

		this.recognition.onerror = (event: any) => {
			console.error('Speech recognition error:', event.error);
			if (this.onError) {
				this.onError(`音声認識エラー: ${event.error}`);
			}
		};

		this.recognition.onend = () => {
			if (this.isListening) {
				// 自動的に再開（連続認識）
				try {
					this.recognition.start();
				} catch (e) {
					console.error('Failed to restart recognition:', e);
				}
			}
		};

		this.isListening = true;
		this.recognition.start();
	}

	stopRealTimeTranscription(): string {
		if (this.recognition) {
			this.isListening = false;
			this.recognition.stop();
			this.recognition = null;
		}
		return this.transcript;
	}

	async transcribeAudioFile(audioBlob: Blob): Promise<string> {
		if (this.settings.transcriptionService === 'whisper-api') {
			return await this.transcribeWithWhisper(audioBlob);
		} else {
			// Web Speech APIの場合、リアルタイム転写で既に取得済み
			return this.transcript;
		}
	}

	private async transcribeWithWhisper(audioBlob: Blob): Promise<string> {
		if (!this.settings.whisperApiKey) {
			throw new Error('OpenAI APIキーが設定されていません。');
		}

		const formData = new FormData();
		formData.append('file', audioBlob, 'recording.webm');
		formData.append('model', 'whisper-1');
		formData.append('language', this.settings.language.split('-')[0]); // 'ja-JP' -> 'ja'

		try {
			const response = await fetch('https://api.openai.com/v1/audio/transcriptions', {
				method: 'POST',
				headers: {
					'Authorization': `Bearer ${this.settings.whisperApiKey}`
				},
				body: formData
			});

			if (!response.ok) {
				const error = await response.json();
				throw new Error(`Whisper API エラー: ${error.error?.message || response.statusText}`);
			}

			const result = await response.json();
			return result.text;
		} catch (error) {
			console.error('Whisper API error:', error);
			throw error;
		}
	}

	private getCurrentTimestamp(): string {
		const now = new Date();
		const hours = String(now.getHours()).padStart(2, '0');
		const minutes = String(now.getMinutes()).padStart(2, '0');
		const seconds = String(now.getSeconds()).padStart(2, '0');
		return `${hours}:${minutes}:${seconds}`;
	}

	getTranscript(): string {
		return this.transcript;
	}
}
