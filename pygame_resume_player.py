import os
import glob
import threading
import time
import ipywidgets as widgets
from IPython.display import display

# pygameを使った一時停止対応のプレーヤー
import pygame

class WAVPlayer:
    def __init__(self, folder_path="outputs"):
        """
        WAVファイルプレーヤーの初期化
        
        Parameters:
        -----------
        folder_path : str
            WAVファイルを含むフォルダのパス
        """
        # 環境変数設定（オーディオドライバ指定）
        os.environ['SDL_AUDIODRIVER'] = 'disk'  # diskドライバーは音を出さないがイベントは発生する
        
        # pygameの初期化
        pygame.init()
        pygame.mixer.init()
        
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
        self.volume = 0.7  # 音量 (0.0〜1.0)
        self.current_file = ""
        self.current_position = 0  # 現在の再生位置（秒）
        self.pause_time = None  # 一時停止した時刻
        
        # 曲の長さを格納する辞書
        self.durations = self._get_wav_durations()
        
        # 終了イベントの設定
        self.MUSIC_END = pygame.USEREVENT + 1
        pygame.mixer.music.set_endevent(self.MUSIC_END)
        
        # GUIの作成
        self._create_gui()
        
        # 監視スレッド
        self.monitor_thread = None
        self.should_stop_monitor = False
        self.start_monitor()
    
    def _get_wav_durations(self):
        """WAVファイルの長さを取得"""
        durations = {}
        for wav_file in self.file_list:
            try:
                with open(wav_file, 'rb') as f:
                    import wave
                    with wave.open(f) as w:
                        frames = w.getnframes()
                        rate = w.getframerate()
                        duration = frames / float(rate)  # 秒単位
                        durations[wav_file] = duration
            except Exception as e:
                print(f"ファイル {wav_file} の長さを取得できませんでした: {e}")
                durations[wav_file] = 0
        return durations
    
    def _create_gui(self):
        """GUIコンポーネントの作成と配置"""
        # ファイル選択ドロップダウン
        file_options = [(os.path.basename(f), i) for i, f in enumerate(self.file_list)]
        self.file_dropdown = widgets.Dropdown(
            options=file_options,
            description='ファイル:',
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='90%')
        )
        self.file_dropdown.observe(self._on_file_select, names='value')
        
        # 再生コントロールボタン
        button_layout = widgets.Layout(width='auto')
        
        self.play_button = widgets.Button(
            description='再生',
            layout=button_layout,
            button_style='primary'
        )
        self.pause_button = widgets.Button(
            description='一時停止',
            layout=button_layout
        )
        self.stop_button = widgets.Button(
            description='停止',
            layout=button_layout
        )
        self.prev_button = widgets.Button(
            description='前へ',
            layout=button_layout
        )
        self.next_button = widgets.Button(
            description='次へ',
            layout=button_layout
        )
        
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
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='90%')
        )
        self.volume_slider.observe(self._on_volume_change, names='value')
        
        # 自動再生切り替え
        self.autoplay_checkbox = widgets.Checkbox(
            value=True,
            description='自動的に次の曲を再生',
            indent=False
        )
        
        # 現在再生中のファイル表示
        self.current_file_label = widgets.HTML(
            value='<b>再生ファイル:</b> なし'
        )
        
        # 再生プログレスバー
        self.progress_bar = widgets.FloatProgress(
            value=0,
            min=0,
            max=100,
            description='進行状況:',
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='90%')
        )
        
        # 再生時間表示
        self.time_label = widgets.Label(
            value='0:00 / 0:00',
            layout=widgets.Layout(width='120px')
        )
        
        # プログレスバーと時間を横並びに
        progress_box = widgets.HBox([
            self.progress_bar,
            self.time_label
        ])
        
        # コントロールボタンの配置
        controls = widgets.HBox([
            self.play_button, 
            self.pause_button,
            self.stop_button, 
            self.prev_button, 
            self.next_button
        ])
        
        # 全体コンテナ
        container = widgets.VBox([
            self.file_dropdown,
            controls,
            self.volume_slider,
            self.autoplay_checkbox,
            self.current_file_label,
            progress_box
        ])
        
        display(container)
    
    def start_monitor(self):
        """監視スレッドを開始"""
        if self.monitor_thread is None or not self.monitor_thread.is_alive():
            self.should_stop_monitor = False
            self.monitor_thread = threading.Thread(target=self._monitor_playback)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
    
    def _monitor_playback(self):
        """再生状態を監視"""
        start_time = None
        
        while not self.should_stop_monitor:
            # イベントの確認
            for event in pygame.event.get():
                if event.type == self.MUSIC_END and self.is_playing and not self.is_paused:
                    # 曲が終了したら次の曲へ
                    if self.autoplay_checkbox.value:
                        self._on_next(None)
                    else:
                        self._on_stop(None)
            
            # 再生中状態の更新
            if self.is_playing and not self.is_paused:
                if start_time is None:
                    start_time = time.time() - self.current_position
                
                # 現在の再生位置を計算
                current_time = time.time() - start_time
                self.current_position = current_time
                
                # 現在のファイルの長さを取得
                current_file = self.file_list[self.current_index]
                total_duration = self.durations.get(current_file, 0)
                
                # プログレスバーと時間表示の更新
                if total_duration > 0:
                    # プログレスバーの更新
                    progress = min(100, (current_time / total_duration) * 100)
                    self.progress_bar.value = progress
                    
                    # 時間表示の更新
                    minutes_current = int(current_time // 60)
                    seconds_current = int(current_time % 60)
                    
                    minutes_total = int(total_duration // 60)
                    seconds_total = int(total_duration % 60)
                    
                    self.time_label.value = f"{minutes_current}:{seconds_current:02d} / {minutes_total}:{seconds_total:02d}"
                    
                    # 再生時間が終了時間を超えたら次の曲へ
                    if current_time >= total_duration and self.autoplay_checkbox.value:
                        self._on_next(None)
                        start_time = None
            elif self.is_paused:
                # 一時停止中は何もしない
                pass
            else:
                # 再生停止中は開始時間をリセット
                start_time = None
            
            time.sleep(0.1)
    
    def _on_file_select(self, change):
        """ファイル選択ドロップダウンの変更イベントハンドラ"""
        if change['new'] is not None:
            new_index = change['new']
            if new_index != self.current_index:
                self.current_index = new_index
                if self.is_playing:
                    self._play_current()
    
    def _on_play(self, b):
        """再生ボタンのイベントハンドラ"""
        if not self.is_playing:
            # 新規再生
            self._play_current()
        elif self.is_paused:
            # 一時停止からの再開
            self.is_paused = False
            # 一時停止時間を記録して、再生位置を保持
            if self.pause_time:
                pause_duration = time.time() - self.pause_time
                self.current_position += pause_duration
            self._play_current(self.current_position)
    
    def _on_pause(self, b):
        """一時停止ボタンのイベントハンドラ"""
        if self.is_playing and not self.is_paused:
            # 再生を停止し、一時停止状態に
            pygame.mixer.music.stop()  # 実際に停止
            self.is_paused = True
            self.pause_time = time.time()  # 一時停止した時間を記録
    
    def _on_stop(self, b):
        """停止ボタンのイベントハンドラ"""
        if self.is_playing:
            pygame.mixer.music.stop()
            self.is_playing = False
            self.is_paused = False
            self.current_position = 0
            self.pause_time = None
            
            # 表示をリセット
            self.current_file_label.value = '<b>再生ファイル:</b> なし'
            self.progress_bar.value = 0
            self.time_label.value = "0:00 / 0:00"
    
    def _on_prev(self, b):
        """前へボタンのイベントハンドラ"""
        if len(self.file_list) > 0:
            # 前のトラックへ
            self.current_index = (self.current_index - 1) % len(self.file_list)
            if self.is_playing:
                self._play_current()
            else:
                self.file_dropdown.value = self.current_index
    
    def _on_next(self, b):
        """次へボタンのイベントハンドラ"""
        if len(self.file_list) > 0:
            # 次のトラックへ
            self.current_index = (self.current_index + 1) % len(self.file_list)
            if self.is_playing:
                self._play_current()
            else:
                self.file_dropdown.value = self.current_index
    
    def _on_volume_change(self, change):
        """音量スライダーの変更イベントハンドラ"""
        self.volume = change['new']
        pygame.mixer.music.set_volume(self.volume)
    
    def _play_current(self, position=0):
        """現在選択されているファイルを再生"""
        if 0 <= self.current_index < len(self.file_list):
            # 現在の再生を停止
            pygame.mixer.music.stop()
            
            # 選択されたファイルをロード
            current_file = self.file_list[self.current_index]
            pygame.mixer.music.load(current_file)
            
            # 音量設定
            pygame.mixer.music.set_volume(self.volume)
            
            # 再生開始
            pygame.mixer.music.play()
            
            # 状態更新
            self.is_playing = True
            self.is_paused = False
            self.current_position = position
            self.current_file = os.path.basename(current_file)
            self.current_file_label.value = f'<b>再生ファイル:</b> {self.current_file}'
            
            # 実際の音声出力（paplayを使用）
            self._play_with_external_player(current_file)
    
    def _play_with_external_player(self, file_path):
        """実際の音声出力（外部プレーヤー使用）"""
        try:
            # paplayが使える場合はそれを使用
            paplay_paths = [
                "/opt/kernel/bin/paplay",
                "/usr/bin/paplay"
            ]
            
            paplay_path = None
            for path in paplay_paths:
                if os.path.exists(path):
                    paplay_path = path
                    break
            
            if paplay_path:
                # 以前の再生プロセスを停止
                self._stop_external_player()
                
                # 新しいプロセスで再生
                self.current_process = subprocess.Popen(
                    [paplay_path, file_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
        except Exception as e:
            # エラーは無視（pygameのイベントだけで連続再生を実現）
            pass
    
    def _stop_external_player(self):
        """外部プレーヤープロセスを停止"""
        if hasattr(self, 'current_process') and self.current_process:
            try:
                self.current_process.terminate()
                self.current_process = None
            except:
                pass
    
    def cleanup(self):
        """リソースの解放"""
        # 監視スレッドを停止
        self.should_stop_monitor = True
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)
            
        # 再生停止
        pygame.mixer.music.stop()
        
        # 外部プレーヤーも停止
        self._stop_external_player()
        
        # pygameをクリーンアップ
        pygame.mixer.quit()
        pygame.quit()

# 使用例
# player = WAVPlayer("outputs")
# プレーヤーを使い終わったら cleanup() を呼び出すことを推奨
# player.cleanup()