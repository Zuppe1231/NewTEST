import { App, Plugin, PluginSettingTab, Setting, Notice, TFile, Modal } from 'obsidian';
import { AudioRecorder } from './src/audio-recorder';
import { TranscriptionService } from './src/transcription-service';
import { RecordingModal } from './src/recording-modal';

interface MeetingTranscriberSettings {
	saveFolder: string;
	autoSave: boolean;
	includeTimestamps: boolean;
	transcriptionService: 'web-speech-api' | 'whisper-api';
	whisperApiKey: string;
	language: string;
	fileNameFormat: string;
}

const DEFAULT_SETTINGS: MeetingTranscriberSettings = {
	saveFolder: 'Meetings',
	autoSave: true,
	includeTimestamps: true,
	transcriptionService: 'web-speech-api',
	whisperApiKey: '',
	language: 'ja-JP',
	fileNameFormat: 'Meeting_{{date}}_{{time}}'
}

export default class MeetingTranscriberPlugin extends Plugin {
	settings: MeetingTranscriberSettings;
	audioRecorder: AudioRecorder;
	transcriptionService: TranscriptionService;

	async onload() {
		await this.loadSettings();

		this.audioRecorder = new AudioRecorder();
		this.transcriptionService = new TranscriptionService(this.settings);

		// リボンアイコンを追加
		this.addRibbonIcon('microphone', 'Meeting Transcriber', (evt: MouseEvent) => {
			this.startRecording();
		});

		// コマンドを追加
		this.addCommand({
			id: 'start-recording',
			name: '会議の録音を開始',
			callback: () => {
				this.startRecording();
			}
		});

		this.addCommand({
			id: 'stop-recording',
			name: '会議の録音を停止',
			callback: () => {
				this.stopRecording();
			}
		});

		// 設定タブを追加
		this.addSettingTab(new MeetingTranscriberSettingTab(this.app, this));
	}

	async startRecording() {
		try {
			const modal = new RecordingModal(
				this.app,
				this.audioRecorder,
				this.transcriptionService,
				this.settings,
				async (transcript: string) => {
					await this.saveTranscript(transcript);
				}
			);
			modal.open();
		} catch (error) {
			new Notice('録音の開始に失敗しました: ' + error.message);
			console.error('Recording error:', error);
		}
	}

	async stopRecording() {
		try {
			await this.audioRecorder.stopRecording();
		} catch (error) {
			new Notice('録音の停止に失敗しました: ' + error.message);
		}
	}

	async saveTranscript(transcript: string) {
		const now = new Date();
		const dateStr = now.toISOString().split('T')[0];
		const timeStr = now.toTimeString().split(' ')[0].replace(/:/g, '-');
		
		let fileName = this.settings.fileNameFormat
			.replace('{{date}}', dateStr)
			.replace('{{time}}', timeStr);
		
		fileName = fileName + '.md';

		// フォルダが存在しない場合は作成
		const folder = this.settings.saveFolder;
		if (folder && !(await this.app.vault.adapter.exists(folder))) {
			await this.app.vault.createFolder(folder);
		}

		const filePath = folder ? `${folder}/${fileName}` : fileName;

		// マークダウンコンテンツを作成
		const content = this.generateMarkdownContent(transcript, now);

		try {
			const file = await this.app.vault.create(filePath, content);
			new Notice(`トランスクリプトを保存しました: ${filePath}`);
			
			// ファイルを開く
			const leaf = this.app.workspace.getLeaf(false);
			await leaf.openFile(file);
		} catch (error) {
			new Notice('ファイルの保存に失敗しました: ' + error.message);
			console.error('Save error:', error);
		}
	}

	generateMarkdownContent(transcript: string, date: Date): string {
		const dateStr = date.toISOString().split('T')[0];
		const timeStr = date.toTimeString().split(' ')[0];
		
		let content = `# 会議トランスクリプト\n\n`;
		content += `**日付**: ${dateStr}\n`;
		content += `**時刻**: ${timeStr}\n\n`;
		content += `---\n\n`;
		content += `## トランスクリプト\n\n`;
		content += transcript;
		content += `\n\n---\n\n`;
		content += `*このトランスクリプトは Meeting Transcriber プラグインによって自動生成されました*\n`;
		
		return content;
	}

	onunload() {
		if (this.audioRecorder) {
			this.audioRecorder.cleanup();
		}
	}

	async loadSettings() {
		this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
	}

	async saveSettings() {
		await this.saveData(this.settings);
	}
}

class MeetingTranscriberSettingTab extends PluginSettingTab {
	plugin: MeetingTranscriberPlugin;

	constructor(app: App, plugin: MeetingTranscriberPlugin) {
		super(app, plugin);
		this.plugin = plugin;
	}

	display(): void {
		const {containerEl} = this;

		containerEl.empty();
		containerEl.createEl('h2', {text: 'Meeting Transcriber 設定'});

		new Setting(containerEl)
			.setName('保存フォルダ')
			.setDesc('トランスクリプトを保存するフォルダ')
			.addText(text => text
				.setPlaceholder('Meetings')
				.setValue(this.plugin.settings.saveFolder)
				.onChange(async (value) => {
					this.plugin.settings.saveFolder = value;
					await this.plugin.saveSettings();
				}));

		new Setting(containerEl)
			.setName('ファイル名フォーマット')
			.setDesc('ファイル名のフォーマット（{{date}}と{{time}}を使用可能）')
			.addText(text => text
				.setPlaceholder('Meeting_{{date}}_{{time}}')
				.setValue(this.plugin.settings.fileNameFormat)
				.onChange(async (value) => {
					this.plugin.settings.fileNameFormat = value;
					await this.plugin.saveSettings();
				}));

		new Setting(containerEl)
			.setName('タイムスタンプを含める')
			.setDesc('トランスクリプトにタイムスタンプを含めるかどうか')
			.addToggle(toggle => toggle
				.setValue(this.plugin.settings.includeTimestamps)
				.onChange(async (value) => {
					this.plugin.settings.includeTimestamps = value;
					await this.plugin.saveSettings();
				}));

		new Setting(containerEl)
			.setName('言語')
			.setDesc('音声認識の言語設定')
			.addDropdown(dropdown => dropdown
				.addOption('ja-JP', '日本語')
				.addOption('en-US', '英語（米国）')
				.addOption('en-GB', '英語（英国）')
				.addOption('zh-CN', '中国語（簡体字）')
				.addOption('ko-KR', '韓国語')
				.setValue(this.plugin.settings.language)
				.onChange(async (value) => {
					this.plugin.settings.language = value;
					await this.plugin.saveSettings();
				}));

		new Setting(containerEl)
			.setName('トランスクリプションサービス')
			.setDesc('使用する音声認識サービス')
			.addDropdown(dropdown => dropdown
				.addOption('web-speech-api', 'Web Speech API（無料、Chrome推奨）')
				.addOption('whisper-api', 'OpenAI Whisper API（有料、高精度）')
				.setValue(this.plugin.settings.transcriptionService)
				.onChange(async (value: any) => {
					this.plugin.settings.transcriptionService = value;
					await this.plugin.saveSettings();
					this.display(); // 再表示してAPIキー入力欄を表示/非表示
				}));

		if (this.plugin.settings.transcriptionService === 'whisper-api') {
			new Setting(containerEl)
				.setName('OpenAI APIキー')
				.setDesc('Whisper APIを使用するためのAPIキー')
				.addText(text => text
					.setPlaceholder('sk-...')
					.setValue(this.plugin.settings.whisperApiKey)
					.onChange(async (value) => {
						this.plugin.settings.whisperApiKey = value;
						await this.plugin.saveSettings();
					}));
		}
	}
}
