import os
import glob
import threading
import time
import ipywidgets as widgets
from IPython.display import display

class WAVPlayer:
    def __init__(self, folder_path="outputs"):
        """
        WAVファイルプレーヤーの初期化
        
        Parameters:
        -----------
        folder_path : str
            WAVファイルを含むフォルダのパス
        """
        # python-vlcをインポート
        try:
            import vlc
            self.vlc = vlc
            print("python-vlcをインポートしました")
        except ImportError:
            print("python-vlcをインストールしてください: pip install python-vlc")
            return
        
        # VLCインスタンスを作成
        self.instance = self.vlc.Instance('--no-xlib')
        # プレーヤーを作成
        self.player = self.instance.media_player_new()
        
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
        self.volume = 70  # VLCの音量は0-100
        self.current_file = ""
        self.current_media = None
        
        # メディアリストの作成
        self.media_list = self.instance.media_list_new()
        for wav_file in self.file_list:
            media = self.instance.media_new(wav_file)
            self.media_list.add_media(media)
        
        # メディアリストプレーヤーの設定
        self.list_player = self.instance.media_list_player_new()
        self.list_player.set_media_list(self.media_list)
        self.list_player.set_media_player(self.player)
        
        # 音量設定
        self.player.audio_set_volume(self.volume)
        
        # イベントマネージャの設定
        self.event_manager = self.player.event_manager()
        self.event_manager.event_attach(self.vlc.EventType.MediaPlayerEndReached, self.on_end_reached)
        
        # GUIの作成
        self._create_gui()
        
        # 監視スレッド
        self.monitor_thread = None
        self.should_stop_monitor = False
        self.start_monitor()
    
    def on_end_reached(self, event):
        """再生終了時のイベントハンドラ"""
        if self.autoplay_checkbox.value:
            # 自動再生が有効なら次のトラックへ
            # 注: このイベントは別スレッドで発生するため、スレッドセーフな実装が必要
            threading.Thread(target=self._on_next, args=(None,)).start()
    
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
        self.volume_slider = widgets.IntSlider(
            value=self.volume,
            min=0,
            max=100,
            step=5,
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
        while not self.should_stop_monitor:
            if self.is_playing:
                # 再生中のみプログレスバーと時間表示を更新
                try:
                    # 一時停止中でも位置情報は更新
                    position = self.player.get_position()
                    length = self.player.get_length() / 1000  # ミリ秒から秒に変換
                    
                    if length > 0:
                        # プログレスバーの更新（0-100%）
                        self.progress_bar.value = position * 100
                        
                        # 現在の時間と総時間を計算
                        current_time = position * length
                        
                        # 時間表示の更新
                        minutes_current = int(current_time // 60)
                        seconds_current = int(current_time % 60)
                        
                        minutes_total = int(length // 60)
                        seconds_total = int(length % 60)
                        
                        self.time_label.value = f"{minutes_current}:{seconds_current:02d} / {minutes_total}:{seconds_total:02d}"
                except Exception as e:
                    # エラーがあっても続行
                    pass
            
            time.sleep(0.1)  # スレッドのスリープ
    
    def _on_file_select(self, change):
        """ファイル選択ドロップダウンの変更イベントハンドラ"""
        if change['new'] is not None:
            # インデックスを設定
            new_index = change['new']
            if new_index != self.current_index:
                self.current_index = new_index
                
                # 再生中なら選択したファイルを再生
                if self.is_playing:
                    self.list_player.play_item_at_index(self.current_index)
                    # ファイル名表示を更新
                    self.current_file = os.path.basename(self.file_list[self.current_index])
                    self.current_file_label.value = f'<b>再生ファイル:</b> {self.current_file}'
    
    def _on_play(self, b):
        """再生ボタンのイベントハンドラ"""
        if not self.is_playing:
            # 新規再生
            self.list_player.play_item_at_index(self.current_index)
            self.is_playing = True
            self.is_paused = False
            
            # ファイル名表示を更新
            self.current_file = os.path.basename(self.file_list[self.current_index])
            self.current_file_label.value = f'<b>再生ファイル:</b> {self.current_file}'
        elif self.is_paused:
            # 一時停止からの再開
            self.player.set_pause(False)  # パラメータ0は再開を意味する
            self.is_paused = False
    
    def _on_pause(self, b):
        """一時停止ボタンのイベントハンドラ"""
        if self.is_playing and not self.is_paused:
            self.player.set_pause(True)  # パラメータ1は一時停止を意味する
            self.is_paused = True
    
    def _on_stop(self, b):
        """停止ボタンのイベントハンドラ"""
        if self.is_playing:
            self.player.stop()
            self.is_playing = False
            self.is_paused = False
            
            # 表示をリセット
            self.current_file_label.value = '<b>再生ファイル:</b> なし'
            self.progress_bar.value = 0
            self.time_label.value = "0:00 / 0:00"
    
    def _on_prev(self, b):
        """前へボタンのイベントハンドラ"""
        if len(self.file_list) > 0:
            # 前のトラックへ
            prev_index = (self.current_index - 1) % len(self.file_list)
            
            if self.is_playing:
                self.list_player.play_item_at_index(prev_index)
                self.current_index = prev_index
                
                # ファイル名表示を更新
                self.current_file = os.path.basename(self.file_list[self.current_index])
                self.current_file_label.value = f'<b>再生ファイル:</b> {self.current_file}'
            else:
                # 再生中でなければドロップダウンだけ更新
                self.current_index = prev_index
                self.file_dropdown.value = self.current_index
    
    def _on_next(self, b):
        """次へボタンのイベントハンドラ"""
        if len(self.file_list) > 0:
            # 次のトラックへ
            next_index = (self.current_index + 1) % len(self.file_list)
            
            if self.is_playing:
                self.list_player.play_item_at_index(next_index)
                self.current_index = next_index
                
                # ファイル名表示を更新
                self.current_file = os.path.basename(self.file_list[self.current_index])
                self.current_file_label.value = f'<b>再生ファイル:</b> {self.current_file}'
            else:
                # 再生中でなければドロップダウンだけ更新
                self.current_index = next_index
                self.file_dropdown.value = self.current_index
    
    def _on_volume_change(self, change):
        """音量スライダーの変更イベントハンドラ"""
        self.volume = change['new']
        self.player.audio_set_volume(self.volume)
    
    def cleanup(self):
        """リソースの解放"""
        # 監視スレッドを停止
        self.should_stop_monitor = True
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)
            
        # 再生停止
        if hasattr(self, 'player'):
            self.player.stop()
            
        # イベントマネージャのクリーンアップ
        if hasattr(self, 'event_manager'):
            self.event_manager.event_detach(self.vlc.EventType.MediaPlayerEndReached)
            
        # VLCインスタンスのリリース
        if hasattr(self, 'instance'):
            self.instance.release()

# 使用例
# player = WAVPlayer("outputs")
# プレーヤーを使い終わったら cleanup() を呼び出すことを推奨
# player.cleanup()