export class AudioRecorder {
	private mediaRecorder: MediaRecorder | null = null;
	private audioChunks: Blob[] = [];
	private stream: MediaStream | null = null;
	private isRecording: boolean = false;

	async startRecording(): Promise<void> {
		try {
			// システムオーディオまたはマイクからの入力を取得
			this.stream = await navigator.mediaDevices.getUserMedia({
				audio: {
					echoCancellation: true,
					noiseSuppression: true,
					sampleRate: 44100
				}
			});

			// MediaRecorderを初期化
			const options = { mimeType: this.getSupportedMimeType() };
			this.mediaRecorder = new MediaRecorder(this.stream, options);
			this.audioChunks = [];

			this.mediaRecorder.ondataavailable = (event) => {
				if (event.data.size > 0) {
					this.audioChunks.push(event.data);
				}
			};

			this.mediaRecorder.start(1000); // 1秒ごとにデータを収集
			this.isRecording = true;
		} catch (error) {
			console.error('Failed to start recording:', error);
			throw new Error('マイクへのアクセスが拒否されました。ブラウザの設定を確認してください。');
		}
	}

	async stopRecording(): Promise<Blob> {
		return new Promise((resolve, reject) => {
			if (!this.mediaRecorder || !this.isRecording) {
				reject(new Error('録音が開始されていません'));
				return;
			}

			this.mediaRecorder.onstop = () => {
				const audioBlob = new Blob(this.audioChunks, { type: this.getSupportedMimeType() });
				this.cleanup();
				resolve(audioBlob);
			};

			this.mediaRecorder.stop();
			this.isRecording = false;
		});
	}

	getRecordingState(): boolean {
		return this.isRecording;
	}

	cleanup(): void {
		if (this.stream) {
			this.stream.getTracks().forEach(track => track.stop());
			this.stream = null;
		}
		this.mediaRecorder = null;
		this.audioChunks = [];
		this.isRecording = false;
	}

	private getSupportedMimeType(): string {
		const types = [
			'audio/webm',
			'audio/webm;codecs=opus',
			'audio/ogg;codecs=opus',
			'audio/mp4',
			'audio/wav'
		];

		for (const type of types) {
			if (MediaRecorder.isTypeSupported(type)) {
				return type;
			}
		}

		return 'audio/webm'; // デフォルト
	}

	getAudioBlob(): Blob {
		return new Blob(this.audioChunks, { type: this.getSupportedMimeType() });
	}
}
