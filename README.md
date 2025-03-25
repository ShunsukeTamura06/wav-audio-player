# WAV Audio Player

Jupyter Notebook用のインタラクティブなWAVファイルプレーヤーです。このプレーヤーを使用すると、指定したフォルダ内のWAVファイルを簡単に再生、一時停止、停止できます。

## 特徴

- フォルダ内のWAVファイルを自動検出
- 再生、一時停止、停止、前へ、次への操作
- 音量調整
- 再生進行状況の表示
- ファイル選択ドロップダウン
- 現在再生中のファイル名表示

## 必要条件

以下のPythonパッケージが必要です：

- Python 3.6以上
- pygame
- ipywidgets
- numpy
- scipy
- Jupyter Notebook または JupyterLab

## インストール方法

1. このリポジトリをクローンまたはダウンロードします。
```bash
git clone https://github.com/ShunsukeTamura06/wav-audio-player.git
```

2. 必要なパッケージをインストールします。
```bash
pip install pygame ipywidgets numpy scipy jupyter
```

3. Jupyter環境で使用する場合、ipywidgetsの拡張機能を有効にします。
```bash
jupyter nbextension enable --py widgetsnbextension
```

## 使い方

1. Jupyter NotebookまたはJupyterLabでノートブックを作成します。
2. 以下のようにしてWAVPlayerをインポートして初期化します。

```python
from wav_player import WAVPlayer

# WAVファイルが格納されているフォルダを指定
player = WAVPlayer("outputs")
```

3. GUIが表示され、指定したフォルダ内のWAVファイルを再生できるようになります。
4. 使い終わったら、リソースを解放するために以下を実行することを推奨します。

```python
player.cleanup()
```

## 使用例

```python
# WAVPlayerのインポート
from wav_player import WAVPlayer

# プレーヤーの初期化（WAVファイルが含まれるフォルダを指定）
player = WAVPlayer("音声ファイルのフォルダ")

# プレーヤーが自動的に表示され、操作できるようになります
# ...

# 使い終わったらリソースを解放
player.cleanup()
```

## 機能の詳細

- **ファイル選択**: ドロップダウンメニューから再生するWAVファイルを選択できます
- **再生コントロール**: 再生、一時停止、停止ボタンで音声ファイルの再生を制御できます
- **ナビゲーション**: 「前へ」と「次へ」ボタンでプレイリスト内を移動できます
- **音量調整**: スライダーで音量を0〜100%の間で調整できます
- **進行状況**: プログレスバーで現在の再生位置を確認できます

## 注意点

- WAVファイルのみ対応しています
- Jupyter環境で動作します（標準のPythonスクリプトでは動作しません）
- pygameとipywidgetsを使用しているため、これらのライブラリが必要です

## ライセンス

MITライセンス
