import os
import pygame
import glob
import threading
import time
import ipywidgets as widgets
from IPython.display import display, clear_output
import numpy as np
from scipy.io import wavfile

class WAVPlayer:
    def __init__(self, folder_path="outputs"):
        """
        WAVファイルプレーヤーの初期化
        
        Parameters:
        -----------
        folder_path : str
            WAVファイルを含むフォルダのパス
        """
        # フォルダ内のwavファイルを取得
        self.folder_path = folder_path
        self.file_list = sorted(glob.glob(os.path.join(folder_path, "*.wav")))
        if not self.file_list:
            print(f"フォルダ{folder_path}にWAVファイルが見つかりません")
            return
        
        # 再生関連の変数初期化
        self.current_index = 0
        self.is_playing = False
        self.is_paused = False
        self.volume = 0.7  # デフォルト音量
        self.current_file = ""
        
        # pygameの初期化
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
        pygame.init()
        pygame.mixer.music.set_volume(self.volume)
        
        # 曲が終了したときの処理のためのイベント設定
        self.MUSIC_END = pygame.USEREVENT + 1
        pygame.mixer.music.set_endevent(self.MUSIC_END)
        
        # GUIの作成
        self._create_gui()
        
        # 監視スレッド
        self.monitor_thread = None
        self.start_monitor()
    
    def _create_gui(self):
        """GUIコンポーネントの作成と配置"""
        # ファイル選択ドロップダウン
        file_options = [(os.path.basename(f), i) for i, f in enumerate(self.file_list)]
        self.file_dropdown = widgets.Dropdown(
            options=file_options,
            description='ファイル:',
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='80%')
        )
        self.file_dropdown.observe(self._on_file_select, names='value')
        
        # 再生コントロールボタン
        self.play_button = widgets.Button(description='再生', icon='play')
        self.pause_button = widgets.Button(description='一時停止', icon='pause')
        self.stop_button = widgets.Button(description='停止', icon='stop')
        self.prev_button = widgets.Button(description='前へ', icon='step-backward')
        self.next_button = widgets.Button(description='次へ', icon='step-forward')
        
        self.play_button.on_click(self._on_play)
        self.pause_button.on_click(self._on_pause)
        self.stop_button.on_click(self._on_stop)
        self.prev_button.on_click(self._on_prev)
        self.next_button.on_click(self._on_next)
        
        # 音量コントロール
        self.volume_slider = widgets.FloatSlider(
            value=self.volume,
            min=0,
            max=1.0,
            step=0.05,
            description='音量:',
            continuous_update=True,
            style={'description_width': 'initial'}
        )
        self.volume_slider.observe(self._on_volume_change, names='value')
        
        # 現在再生中のファイル表示
        self.current_file_label = widgets.HTML(value="<b>再生ファイル:</b> なし")
        
        # 再生プログレスバー
        self.progress_bar = widgets.FloatProgress(
            value=0,
            min=0,
            max=100,
            description='進行状況:',
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='80%')
        )
        
        # ウィジェットをまとめる
        controls = widgets.HBox([
            self.play_button, 
            self.pause_button, 
            self.stop_button, 
            self.prev_button, 
            self.next_button
        ])
        
        # ウィジェットの配置
        self.gui = widgets.VBox([
            widgets.HTML(value="<h3>WAVオーディオプレーヤー</h3>"),
            self.file_dropdown,
            controls,
            self.volume_slider,
            self.current_file_label,
            self.progress_bar
        ])
        
        display(self.gui)
    
    def start_monitor(self):
        """音楽の再生状態を監視するスレッドを開始"""
        if self.monitor_thread is None or not self.monitor_thread.is_alive():
            self.monitor_thread = threading.Thread(target=self._monitor_playback)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
    
    def _monitor_playback(self):
        """再生状態を監視し、曲の終了やプログレスバーの更新を処理"""
        while True:
            time.sleep(0.1)
            
            # イベントの確認
            for event in pygame.event.get():
                if event.type == self.MUSIC_END:
                    # 曲が終了したら次の曲へ
                    if self.is_playing and not self.is_paused:
                        self._on_next(None)
            
            # プログレスバーの更新（再生中の場合）
            if self.is_playing and not self.is_paused:
                # 現在の再生位置を取得（ミリ秒）
                current_pos = pygame.mixer.music.get_pos()
                if current_pos > 0:
                    # ファイルの総時間を取得
                    try:
                        rate, data = wavfile.read(self.file_list[self.current_index])
                        if len(data.shape) > 1:  # ステレオの場合
                            duration = len(data) / rate * 1000  # ミリ秒に変換
                        else:  # モノラルの場合
                            duration = len(data) / rate * 1000
                        
                        progress = min(100, (current_pos / duration) * 100)
                        self.progress_bar.value = progress
                    except Exception as e:
                        # エラーがあっても処理を続行
                        pass
    
    def _on_file_select(self, change):
        """ファイル選択ドロップダウンの変更イベントハンドラ"""
        if change['new'] is not None:
            self.current_index = change['new']
            if self.is_playing:
                self._play_current()
    
    def _on_play(self, b):
        """再生ボタンのイベントハンドラ"""
        if not self.is_playing:
            self._play_current()
        elif self.is_paused:
            pygame.mixer.music.unpause()
            self.is_paused = False
    
    def _on_pause(self, b):
        """一時停止ボタンのイベントハンドラ"""
        if self.is_playing and not self.is_paused:
            pygame.mixer.music.pause()
            self.is_paused = True
    
    def _on_stop(self, b):
        """停止ボタンのイベントハンドラ"""
        if self.is_playing:
            pygame.mixer.music.stop()
            self.is_playing = False
            self.is_paused = False
            self.current_file_label.value = "<b>再生ファイル:</b> なし"
            self.progress_bar.value = 0
    
    def _on_prev(self, b):
        """前へボタンのイベントハンドラ"""
        if len(self.file_list) > 0:
            self.current_index = (self.current_index - 1) % len(self.file_list)
            if self.is_playing:
                self._play_current()
            else:
                self.file_dropdown.value = self.current_index
    
    def _on_next(self, b):
        """次へボタンのイベントハンドラ"""
        if len(self.file_list) > 0:
            self.current_index = (self.current_index + 1) % len(self.file_list)
            if self.is_playing:
                self._play_current()
            else:
                self.file_dropdown.value = self.current_index
    
    def _on_volume_change(self, change):
        """音量スライダーの変更イベントハンドラ"""
        self.volume = change['new']
        pygame.mixer.music.set_volume(self.volume)
    
    def _play_current(self):
        """現在選択されているファイルを再生する"""
        if 0 <= self.current_index < len(self.file_list):
            current_file = self.file_list[self.current_index]
            
            # 通常の再生
            try:
                pygame.mixer.music.load(current_file)
                pygame.mixer.music.play()
                
                # 再生状態とファイル名表示を更新
                self.is_playing = True
                self.is_paused = False
                self.current_file = os.path.basename(current_file)
                self.current_file_label.value = f"<b>再生ファイル:</b> {self.current_file}"
            except Exception as e:
                print(f"ファイルの再生中にエラーが発生しました: {e}")
                return
            
            # プログレスバーをリセット
            self.progress_bar.value = 0
            
            # ドロップダウンメニューを同期
            self.file_dropdown.value = self.current_index
    
    def cleanup(self):
        """リソースの解放"""
        # pygameのリソースを解放
        pygame.mixer.quit()
        pygame.quit()

# 使用例
player = WAVPlayer("outputs")
# プレーヤーを使い終わったら cleanup() を呼び出すことを推奨
# player.cleanup()