import { App, Modal, Notice } from 'obsidian';
import { AudioRecorder } from './audio-recorder';
import { TranscriptionService } from './transcription-service';

export class RecordingModal extends Modal {
	private audioRecorder: AudioRecorder;
	private transcriptionService: TranscriptionService;
	private settings: any;
	private onComplete: (transcript: string) => void;
	private isRecording: boolean = false;
	private transcriptDiv: HTMLDivElement;
	private statusDiv: HTMLDivElement;
	private recordButton: HTMLButtonElement;
	private stopButton: HTMLButtonElement;
	private elapsedTimeDiv: HTMLDivElement;
	private startTime: number = 0;
	private timerInterval: number | null = null;

	constructor(
		app: App,
		audioRecorder: AudioRecorder,
		transcriptionService: TranscriptionService,
		settings: any,
		onComplete: (transcript: string) => void
	) {
		super(app);
		this.audioRecorder = audioRecorder;
		this.transcriptionService = transcriptionService;
		this.settings = settings;
		this.onComplete = onComplete;
	}

	onOpen() {
		const { contentEl } = this;
		contentEl.empty();

		contentEl.createEl('h2', { text: '会議トランスクリプション' });

		// ステータス表示
		this.statusDiv = contentEl.createDiv({ cls: 'transcription-status' });
		this.statusDiv.setText('準備完了');

		// 経過時間表示
		this.elapsedTimeDiv = contentEl.createDiv({ cls: 'elapsed-time' });
		this.elapsedTimeDiv.setText('経過時間: 00:00:00');

		// ボタンコンテナ
		const buttonContainer = contentEl.createDiv({ cls: 'button-container' });
		
		this.recordButton = buttonContainer.createEl('button', {
			text: '録音開始',
			cls: 'mod-cta'
		});
		this.recordButton.onclick = () => this.startRecording();

		this.stopButton = buttonContainer.createEl('button', {
			text: '録音停止',
			cls: 'mod-warning'
		});
		this.stopButton.disabled = true;
		this.stopButton.onclick = () => this.stopRecording();

		// トランスクリプト表示エリア
		contentEl.createEl('h3', { text: 'リアルタイムトランスクリプト' });
		this.transcriptDiv = contentEl.createDiv({ cls: 'transcript-display' });
		this.transcriptDiv.style.cssText = `
			border: 1px solid var(--background-modifier-border);
			padding: 10px;
			min-height: 200px;
			max-height: 400px;
			overflow-y: auto;
			white-space: pre-wrap;
			font-family: var(--font-monospace);
			background-color: var(--background-primary-alt);
		`;

		// スタイルを追加
		this.addStyles();
	}

	private addStyles() {
		const style = document.createElement('style');
		style.textContent = `
			.transcription-status {
				padding: 10px;
				margin: 10px 0;
				border-radius: 5px;
				text-align: center;
				font-weight: bold;
			}
			.status-ready {
				background-color: var(--interactive-accent);
				color: white;
			}
			.status-recording {
				background-color: var(--text-error);
				color: white;
			}
			.status-processing {
				background-color: var(--text-warning);
				color: white;
			}
			.elapsed-time {
				text-align: center;
				font-size: 1.2em;
				margin: 10px 0;
				font-weight: bold;
			}
			.button-container {
				display: flex;
				gap: 10px;
				justify-content: center;
				margin: 20px 0;
			}
			.button-container button {
				padding: 10px 20px;
				font-size: 1em;
			}
		`;
		document.head.appendChild(style);
	}

	private async startRecording() {
		try {
			this.isRecording = true;
			this.recordButton.disabled = true;
			this.stopButton.disabled = false;
			
			this.statusDiv.setText('録音中...');
			this.statusDiv.className = 'transcription-status status-recording';

			// タイマー開始
			this.startTime = Date.now();
			this.timerInterval = window.setInterval(() => {
				this.updateElapsedTime();
			}, 1000);

			// 録音開始
			await this.audioRecorder.startRecording();

			// リアルタイム転写開始（Web Speech APIの場合のみ）
			if (this.settings.transcriptionService === 'web-speech-api') {
				await this.transcriptionService.startRealTimeTranscription(
					(transcript) => {
						this.transcriptDiv.textContent = transcript;
						// 自動スクロール
						this.transcriptDiv.scrollTop = this.transcriptDiv.scrollHeight;
					},
					(error) => {
						new Notice('音声認識エラー: ' + error);
					}
				);
			} else {
				this.transcriptDiv.textContent = '※ Whisper APIを使用する場合、トランスクリプトは録音停止後に生成されます。';
			}

			new Notice('録音を開始しました');
		} catch (error) {
			new Notice('録音の開始に失敗しました: ' + error.message);
			this.resetUI();
		}
	}

	private async stopRecording() {
		try {
			this.statusDiv.setText('処理中...');
			this.statusDiv.className = 'transcription-status status-processing';
			
			this.stopButton.disabled = true;

			if (this.timerInterval) {
				clearInterval(this.timerInterval);
				this.timerInterval = null;
			}

			// リアルタイム転写停止
			let transcript = '';
			if (this.settings.transcriptionService === 'web-speech-api') {
				transcript = this.transcriptionService.stopRealTimeTranscription();
			}

			// 録音停止
			const audioBlob = await this.audioRecorder.stopRecording();

			// Whisper APIの場合はここで転写
			if (this.settings.transcriptionService === 'whisper-api') {
				this.transcriptDiv.textContent = 'Whisper APIで音声を転写中...';
				transcript = await this.transcriptionService.transcribeAudioFile(audioBlob);
				this.transcriptDiv.textContent = transcript;
			}

			new Notice('録音を停止しました');

			// トランスクリプトを保存
			await this.onComplete(transcript);

			this.close();
		} catch (error) {
			new Notice('録音の停止に失敗しました: ' + error.message);
			console.error(error);
			this.resetUI();
		}
	}

	private updateElapsedTime() {
		const elapsed = Date.now() - this.startTime;
		const seconds = Math.floor((elapsed / 1000) % 60);
		const minutes = Math.floor((elapsed / 60000) % 60);
		const hours = Math.floor(elapsed / 3600000);

		const timeStr = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
		this.elapsedTimeDiv.setText('経過時間: ' + timeStr);
	}

	private resetUI() {
		this.isRecording = false;
		this.recordButton.disabled = false;
		this.stopButton.disabled = true;
		this.statusDiv.setText('準備完了');
		this.statusDiv.className = 'transcription-status status-ready';
		
		if (this.timerInterval) {
			clearInterval(this.timerInterval);
			this.timerInterval = null;
		}
	}

	onClose() {
		const { contentEl } = this;
		contentEl.empty();
		
		if (this.timerInterval) {
			clearInterval(this.timerInterval);
		}
		
		if (this.isRecording) {
			this.audioRecorder.cleanup();
			this.transcriptionService.stopRealTimeTranscription();
		}
	}
}
