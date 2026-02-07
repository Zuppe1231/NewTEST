#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
セットアップチェックスクリプト
必要な依存関係と環境をチェックします
"""

import sys
import platform
import subprocess


def print_section(title):
    """セクションタイトルを表示"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def check_python_version():
    """Pythonバージョンのチェック"""
    print_section("Pythonバージョン")
    
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    print(f"Python {version_str}")
    
    if version.major == 3 and version.minor >= 8:
        print("✓ Pythonバージョンは要件を満たしています（3.8以上）")
        return True
    else:
        print("✗ Python 3.8以上が必要です")
        return False


def check_system_info():
    """システム情報の表示"""
    print_section("システム情報")
    
    print(f"OS: {platform.system()} {platform.release()}")
    print(f"アーキテクチャ: {platform.machine()}")
    print(f"プロセッサ: {platform.processor()}")


def check_package(package_name, import_name=None):
    """パッケージがインストールされているかチェック"""
    if import_name is None:
        import_name = package_name
    
    try:
        __import__(import_name)
        print(f"✓ {package_name} がインストールされています")
        
        # バージョン情報を取得
        try:
            module = __import__(import_name)
            if hasattr(module, '__version__'):
                print(f"  バージョン: {module.__version__}")
        except:
            pass
        
        return True
    except ImportError:
        print(f"✗ {package_name} がインストールされていません")
        return False


def check_dependencies():
    """必要な依存パッケージのチェック"""
    print_section("依存パッケージ")
    
    packages = [
        ("numpy", "numpy"),
        ("sounddevice", "sounddevice"),
        ("whisper", "whisper"),
        ("torch", "torch"),
        ("torchaudio", "torchaudio"),
    ]
    
    results = []
    for package_name, import_name in packages:
        results.append(check_package(package_name, import_name))
    
    return all(results)


def check_audio_devices():
    """音声デバイスのチェック"""
    print_section("音声デバイス")
    
    try:
        import sounddevice as sd
        
        print("\n利用可能な音声デバイス:")
        devices = sd.query_devices()
        
        for i, device in enumerate(devices):
            print(f"\n{i}: {device['name']}")
            print(f"   入力チャンネル: {device['max_input_channels']}")
            print(f"   出力チャンネル: {device['max_output_channels']}")
        
        # デフォルトデバイス
        try:
            default_input = sd.query_devices(kind='input')
            default_output = sd.query_devices(kind='output')
            print(f"\nデフォルト入力: {default_input['name']}")
            print(f"デフォルト出力: {default_output['name']}")
        except:
            print("\n警告: デフォルトデバイスの取得に失敗しました")
        
        return True
    except ImportError:
        print("✗ sounddeviceがインストールされていないため、デバイスをチェックできません")
        return False
    except Exception as e:
        print(f"✗ 音声デバイスのチェック中にエラーが発生しました: {e}")
        return False


def check_disk_space():
    """ディスク容量のチェック"""
    print_section("ディスク容量")
    
    try:
        import shutil
        
        total, used, free = shutil.disk_usage(".")
        
        total_gb = total / (1024**3)
        used_gb = used / (1024**3)
        free_gb = free / (1024**3)
        
        print(f"総容量: {total_gb:.2f} GB")
        print(f"使用済み: {used_gb:.2f} GB")
        print(f"空き容量: {free_gb:.2f} GB")
        
        if free_gb < 5:
            print("✗ 警告: 空き容量が5GB未満です")
            return False
        else:
            print("✓ 十分な空き容量があります")
            return True
    except Exception as e:
        print(f"ディスク容量のチェックに失敗しました: {e}")
        return False


def check_cuda():
    """CUDA（GPU）のサポートをチェック"""
    print_section("CUDA/GPUサポート")
    
    try:
        import torch
        
        if torch.cuda.is_available():
            print(f"✓ CUDA が利用可能です")
            print(f"  CUDA バージョン: {torch.version.cuda}")
            print(f"  利用可能なGPU数: {torch.cuda.device_count()}")
            
            for i in range(torch.cuda.device_count()):
                print(f"  GPU {i}: {torch.cuda.get_device_name(i)}")
            
            return True
        else:
            print("✗ CUDA は利用できません（CPUモードで動作します）")
            print("  注: GPUがなくても動作しますが、処理速度は遅くなります")
            return False
    except ImportError:
        print("✗ PyTorchがインストールされていません")
        return False
    except Exception as e:
        print(f"CUDAチェック中にエラーが発生しました: {e}")
        return False


def test_basic_recording():
    """基本的な録音機能のテスト"""
    print_section("基本機能テスト")
    
    try:
        import sounddevice as sd
        import numpy as np
        
        print("3秒間の録音テストを実行します...")
        print("マイクに向かって何か話してください...")
        
        duration = 3
        sample_rate = 16000
        
        recording = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype='int16'
        )
        sd.wait()
        
        # 音声レベルをチェック
        max_amplitude = np.abs(recording).max()
        
        if max_amplitude > 100:
            print(f"✓ 録音成功！（最大振幅: {max_amplitude}）")
            print("  マイクが正常に動作しています")
            return True
        else:
            print(f"✗ 録音はできましたが、音声が検出されませんでした（最大振幅: {max_amplitude}）")
            print("  マイクの接続とボリュームを確認してください")
            return False
    except ImportError:
        print("✗ 必要なパッケージがインストールされていません")
        return False
    except Exception as e:
        print(f"✗ 録音テスト中にエラーが発生しました: {e}")
        return False


def main():
    """メイン関数"""
    print("=" * 60)
    print("  WEB会議録音プログラム - セットアップチェック")
    print("=" * 60)
    
    results = {}
    
    # 各種チェック
    results['python_version'] = check_python_version()
    check_system_info()
    results['dependencies'] = check_dependencies()
    results['audio_devices'] = check_audio_devices()
    results['disk_space'] = check_disk_space()
    results['cuda'] = check_cuda()
    
    # 録音テストは任意
    print_section("録音テスト（オプション）")
    response = input("録音テストを実行しますか？ (y/N): ").strip().lower()
    if response == 'y':
        results['recording_test'] = test_basic_recording()
    
    # 総合結果
    print_section("総合結果")
    
    required_checks = ['python_version', 'dependencies']
    all_required_passed = all(results.get(check, False) for check in required_checks)
    
    if all_required_passed:
        print("\n✓ すべての必須チェックに合格しました！")
        print("  プログラムを使用できます。")
        
        if not results.get('audio_devices', False):
            print("\n⚠ 警告: 音声デバイスに問題がある可能性があります")
        
        if not results.get('cuda', False):
            print("\n⚠ 情報: GPU（CUDA）は利用できませんが、CPUで動作します")
    else:
        print("\n✗ いくつかの必須チェックに失敗しました")
        print("  以下のコマンドを実行して依存パッケージをインストールしてください:")
        print("  pip install -r requirements.txt")
    
    print("\n" + "=" * 60)
    print("セットアップチェックが完了しました")
    print("=" * 60)
    
    return 0 if all_required_passed else 1


if __name__ == "__main__":
    sys.exit(main())
