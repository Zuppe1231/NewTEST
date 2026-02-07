#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WEB会議録音プログラムの使用例
"""

from web_meeting_recorder import WebMeetingRecorder


def example_1_simple_recording():
    """例1: シンプルな録音と文字起こし"""
    print("=== 例1: シンプルな録音と文字起こし ===\n")
    
    recorder = WebMeetingRecorder()
    
    # 録音と文字起こしを一括実行
    audio_file, transcript_file = recorder.record_and_transcribe(
        duration=10,  # 10秒間録音
        language="ja"
    )
    
    print(f"\n完了！")
    print(f"音声ファイル: {audio_file}")
    print(f"トランスクリプト: {transcript_file}")


def example_2_custom_settings():
    """例2: カスタム設定で録音"""
    print("=== 例2: カスタム設定で録音 ===\n")
    
    recorder = WebMeetingRecorder(
        sample_rate=44100,      # 高音質
        channels=2,             # ステレオ
        output_dir="my_meetings",
        whisper_model="small"   # より高精度なモデル
    )
    
    # デバイス一覧を表示
    recorder.list_audio_devices()
    
    # 特定のデバイスで録音（デバイスIDは環境によって異なります）
    # audio_file, transcript_file = recorder.record_and_transcribe(
    #     device=1,
    #     language="ja"
    # )


def example_3_transcribe_existing_file():
    """例3: 既存の音声ファイルを文字起こし"""
    print("=== 例3: 既存の音声ファイルを文字起こし ===\n")
    
    recorder = WebMeetingRecorder(whisper_model="base")
    
    # 既存のファイルを文字起こし
    audio_file = "recordings/meeting_20260207_120000.wav"
    
    try:
        transcript = recorder.transcribe_audio(audio_file, language="ja")
        markdown_file = recorder.save_transcript_markdown(transcript, audio_file)
        
        print(f"トランスクリプトを保存しました: {markdown_file}")
    except FileNotFoundError:
        print(f"ファイルが見つかりません: {audio_file}")
        print("まず録音を行ってください。")


def example_4_manual_control():
    """例4: 手動制御（録音と文字起こしを分けて実行）"""
    print("=== 例4: 手動制御 ===\n")
    
    recorder = WebMeetingRecorder()
    
    # ステップ1: 録音のみ
    print("ステップ1: 録音")
    audio_file = recorder.record_audio(duration=5)
    
    # ステップ2: 文字起こしのみ
    print("\nステップ2: 文字起こし")
    transcript = recorder.transcribe_audio(audio_file, language="ja")
    
    # ステップ3: マークダウン保存
    print("\nステップ3: マークダウン保存")
    markdown_file = recorder.save_transcript_markdown(transcript, audio_file)
    
    print(f"\n完了！トランスクリプト: {markdown_file}")


def example_5_english_meeting():
    """例5: 英語の会議"""
    print("=== 例5: 英語の会議 ===\n")
    
    recorder = WebMeetingRecorder(whisper_model="base")
    
    audio_file, transcript_file = recorder.record_and_transcribe(
        duration=10,
        language="en"  # 英語
    )
    
    print(f"\n完了！トランスクリプト: {transcript_file}")


if __name__ == "__main__":
    print("WEB会議録音プログラム - 使用例\n")
    print("実行したい例を選択してください:\n")
    print("1. シンプルな録音と文字起こし（10秒）")
    print("2. カスタム設定とデバイス一覧")
    print("3. 既存ファイルの文字起こし")
    print("4. 手動制御（ステップバイステップ）")
    print("5. 英語の会議")
    print()
    
    try:
        choice = input("番号を入力してください (1-5): ")
        print()
        
        if choice == "1":
            example_1_simple_recording()
        elif choice == "2":
            example_2_custom_settings()
        elif choice == "3":
            example_3_transcribe_existing_file()
        elif choice == "4":
            example_4_manual_control()
        elif choice == "5":
            example_5_english_meeting()
        else:
            print("無効な選択です。1-5の番号を入力してください。")
    except KeyboardInterrupt:
        print("\n\n処理を中断しました。")
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
