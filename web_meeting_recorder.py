#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WEB会議録音・文字起こしプログラム
Windows PCでWEB会議の音声を録音し、トランスクリプトをマークダウンファイルで作成します。
"""

import os
import wave
import datetime
import argparse
from pathlib import Path
import sounddevice as sd
import numpy as np
import whisper
from typing import Optional


class WebMeetingRecorder:
    """WEB会議録音・文字起こしクラス"""
    
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 2,
        output_dir: str = "recordings",
        whisper_model: str = "base"
    ):
        """
        初期化
        
        Args:
            sample_rate: サンプリングレート（Hz）
            channels: チャンネル数（1=モノラル, 2=ステレオ）
            output_dir: 出力ディレクトリ
            whisper_model: Whisperモデル（tiny, base, small, medium, large）
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.whisper_model_name = whisper_model
        self.whisper_model = None
        self.recording = []
        self.is_recording = False
        
    def _load_whisper_model(self):
        """Whisperモデルの遅延ロード"""
        if self.whisper_model is None:
            print(f"Whisperモデル '{self.whisper_model_name}' を読み込み中...")
            self.whisper_model = whisper.load_model(self.whisper_model_name)
            print("モデルの読み込みが完了しました。")
    
    def list_audio_devices(self):
        """利用可能な音声デバイスを一覧表示"""
        print("\n=== 利用可能な音声デバイス ===")
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            print(f"{i}: {device['name']}")
            print(f"   入力チャンネル: {device['max_input_channels']}")
            print(f"   出力チャンネル: {device['max_output_channels']}")
            print(f"   デフォルトサンプリングレート: {device['default_samplerate']}")
            print()
        
        # デフォルトデバイス情報
        default_input = sd.query_devices(kind='input')
        default_output = sd.query_devices(kind='output')
        print(f"デフォルト入力デバイス: {default_input['name']}")
        print(f"デフォルト出力デバイス: {default_output['name']}")
        print()
    
    def record_audio(
        self,
        duration: Optional[int] = None,
        device: Optional[int] = None
    ) -> str:
        """
        音声を録音
        
        Args:
            duration: 録音時間（秒）。Noneの場合はEnterキーで停止
            device: 使用するデバイスID（Noneの場合はデフォルト）
        
        Returns:
            録音ファイルのパス
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_filename = self.output_dir / f"meeting_{timestamp}.wav"
        
        print(f"\n録音を開始します...")
        print(f"サンプリングレート: {self.sample_rate} Hz")
        print(f"チャンネル数: {self.channels}")
        
        if device is not None:
            device_info = sd.query_devices(device)
            print(f"使用デバイス: {device_info['name']}")
        
        if duration:
            print(f"録音時間: {duration}秒")
            print("録音中...")
            
            # 指定時間録音
            recording = sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=self.channels,
                device=device,
                dtype='int16'
            )
            sd.wait()
        else:
            print("Enterキーを押すと録音を停止します...")
            
            # 手動停止まで録音
            self.recording = []
            self.is_recording = True
            
            def callback(indata, frames, time, status):
                if status:
                    print(f"ステータス: {status}")
                if self.is_recording:
                    self.recording.append(indata.copy())
            
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                device=device,
                callback=callback,
                dtype='int16'
            ):
                input("録音中... Enterキーで停止\n")
                self.is_recording = False
            
            recording = np.concatenate(self.recording, axis=0)
        
        # WAVファイルとして保存
        print(f"\n録音を保存中: {audio_filename}")
        with wave.open(str(audio_filename), 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(recording.tobytes())
        
        print(f"録音完了: {audio_filename}")
        return str(audio_filename)
    
    def transcribe_audio(
        self,
        audio_file: str,
        language: str = "ja"
    ) -> dict:
        """
        音声ファイルを文字起こし
        
        Args:
            audio_file: 音声ファイルのパス
            language: 言語コード（ja=日本語, en=英語など）
        
        Returns:
            文字起こし結果の辞書
        """
        self._load_whisper_model()
        
        print(f"\n文字起こしを開始します: {audio_file}")
        print(f"言語: {language}")
        print("処理中... (音声の長さによって時間がかかる場合があります)")
        
        # Whisperで文字起こし
        result = self.whisper_model.transcribe(
            audio_file,
            language=language,
            verbose=False
        )
        
        print("文字起こしが完了しました。")
        return result
    
    def save_transcript_markdown(
        self,
        transcript_result: dict,
        audio_file: str,
        output_file: Optional[str] = None
    ) -> str:
        """
        トランスクリプトをマークダウンファイルとして保存
        
        Args:
            transcript_result: 文字起こし結果
            audio_file: 元の音声ファイル名
            output_file: 出力ファイル名（Noneの場合は自動生成）
        
        Returns:
            保存したマークダウンファイルのパス
        """
        if output_file is None:
            # 音声ファイル名からマークダウンファイル名を生成
            audio_path = Path(audio_file)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.output_dir / f"transcript_{timestamp}.md"
        else:
            output_file = Path(output_file)
        
        print(f"\nマークダウンファイルを作成中: {output_file}")
        
        # マークダウン形式で出力
        with open(output_file, 'w', encoding='utf-8') as f:
            # ヘッダー
            f.write("# WEB会議トランスクリプト\n\n")
            f.write(f"**作成日時**: {datetime.datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n\n")
            f.write(f"**音声ファイル**: `{Path(audio_file).name}`\n\n")
            
            # 全文
            f.write("## 全文\n\n")
            f.write(transcript_result['text'].strip() + "\n\n")
            
            # セグメント（タイムスタンプ付き）
            f.write("## タイムスタンプ付き詳細\n\n")
            
            if 'segments' in transcript_result:
                for segment in transcript_result['segments']:
                    start_time = self._format_timestamp(segment['start'])
                    end_time = self._format_timestamp(segment['end'])
                    text = segment['text'].strip()
                    
                    f.write(f"### [{start_time} - {end_time}]\n\n")
                    f.write(f"{text}\n\n")
            
            # メタデータ
            f.write("---\n\n")
            f.write("## メタデータ\n\n")
            f.write(f"- **言語**: {transcript_result.get('language', 'unknown')}\n")
            
            if 'segments' in transcript_result:
                total_duration = transcript_result['segments'][-1]['end']
                f.write(f"- **総時間**: {self._format_timestamp(total_duration)}\n")
                f.write(f"- **セグメント数**: {len(transcript_result['segments'])}\n")
        
        print(f"マークダウンファイルを保存しました: {output_file}")
        return str(output_file)
    
    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """秒数をタイムスタンプ形式に変換（HH:MM:SS）"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
    
    def record_and_transcribe(
        self,
        duration: Optional[int] = None,
        device: Optional[int] = None,
        language: str = "ja"
    ) -> tuple[str, str]:
        """
        録音と文字起こしを一括実行
        
        Args:
            duration: 録音時間（秒）
            device: 使用するデバイスID
            language: 言語コード
        
        Returns:
            (音声ファイルパス, マークダウンファイルパス)
        """
        # 録音
        audio_file = self.record_audio(duration=duration, device=device)
        
        # 文字起こし
        transcript = self.transcribe_audio(audio_file, language=language)
        
        # マークダウン保存
        markdown_file = self.save_transcript_markdown(transcript, audio_file)
        
        return audio_file, markdown_file


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="WEB会議録音・文字起こしプログラム"
    )
    parser.add_argument(
        '--list-devices',
        action='store_true',
        help="利用可能な音声デバイスを一覧表示"
    )
    parser.add_argument(
        '--duration',
        type=int,
        default=None,
        help="録音時間（秒）。指定しない場合はEnterキーで停止"
    )
    parser.add_argument(
        '--device',
        type=int,
        default=None,
        help="使用する音声デバイスID"
    )
    parser.add_argument(
        '--language',
        type=str,
        default='ja',
        help="音声の言語コード（デフォルト: ja）"
    )
    parser.add_argument(
        '--model',
        type=str,
        default='base',
        choices=['tiny', 'base', 'small', 'medium', 'large'],
        help="Whisperモデルのサイズ（デフォルト: base）"
    )
    parser.add_argument(
        '--sample-rate',
        type=int,
        default=16000,
        help="サンプリングレート（Hz、デフォルト: 16000）"
    )
    parser.add_argument(
        '--channels',
        type=int,
        default=2,
        choices=[1, 2],
        help="チャンネル数（1=モノラル, 2=ステレオ、デフォルト: 2）"
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='recordings',
        help="出力ディレクトリ（デフォルト: recordings）"
    )
    parser.add_argument(
        '--audio-file',
        type=str,
        default=None,
        help="既存の音声ファイルを文字起こし（録音をスキップ）"
    )
    
    args = parser.parse_args()
    
    # レコーダーインスタンス作成
    recorder = WebMeetingRecorder(
        sample_rate=args.sample_rate,
        channels=args.channels,
        output_dir=args.output_dir,
        whisper_model=args.model
    )
    
    # デバイス一覧表示
    if args.list_devices:
        recorder.list_audio_devices()
        return
    
    print("=" * 60)
    print("WEB会議録音・文字起こしプログラム")
    print("=" * 60)
    
    # 既存ファイルの文字起こし
    if args.audio_file:
        if not os.path.exists(args.audio_file):
            print(f"エラー: ファイルが見つかりません: {args.audio_file}")
            return
        
        transcript = recorder.transcribe_audio(args.audio_file, language=args.language)
        markdown_file = recorder.save_transcript_markdown(transcript, args.audio_file)
        
        print("\n" + "=" * 60)
        print("処理が完了しました！")
        print(f"トランスクリプト: {markdown_file}")
        print("=" * 60)
    else:
        # 録音と文字起こし
        audio_file, markdown_file = recorder.record_and_transcribe(
            duration=args.duration,
            device=args.device,
            language=args.language
        )
        
        print("\n" + "=" * 60)
        print("すべての処理が完了しました！")
        print(f"録音ファイル: {audio_file}")
        print(f"トランスクリプト: {markdown_file}")
        print("=" * 60)


if __name__ == "__main__":
    main()
