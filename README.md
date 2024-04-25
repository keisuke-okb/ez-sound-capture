# ez-sound-capture
EZ Sound Capture is a simple GUI program using [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) that allows you to record audio from your selected recording device or loopback audio output device.
**This program is designed to work even on PCs that do not have a stereo mixer installed!**

![image](https://github.com/keisuke-okb/ez-sound-capture/assets/70097451/95b55e50-904e-46dd-a1c6-e0dffbe65c49)
ArtWork created by Stable Diffusion 3

## Main features
- Record audio from a recording device or loopback audio output device (Anything you hear!)
- Monitoring audio input level (log scale)
- Backup recorded data (as numpy array)
- Auto silence removal
- Save as MP3 (**FFmpeg required**)
- Normalize (**FFmpeg required**)

![image](https://github.com/keisuke-okb/ez-sound-capture/assets/70097451/88067a26-e986-4164-8a16-fdec51e3b890)

TODO: Add a feature to output `.wav`  from backup npz files

## Known issue
- Continuity of multiple chunks recorded is lost (occurs within soundcard module)
```
soundcard\mediafoundation.py:772: SoundcardRuntimeWarning: data discontinuity in recording
  warnings.warn("data discontinuity in recording", SoundcardRuntimeWarning)
```

# Getting Started

## Prepare FFmpeg (optional) 

To use FFmpeg required features, please install ffmpeg or set path/to/ffmpeg.exe to PATH.

## 1. Create python environment
```powershell
cd ez-sound-capture
pip install -r requirements.txt
```

## 2. Edit settings.json
```json
{
    "gui":{
        "lang": "en" // App language you want use (en and ja included)
    },
    "recording":{
        "sample_rate": 44100,
        "backup_interval": 60, // Backup interval (seconds)
        "silence_threshold": 0.05 
    }
}
```

## 3. Launch app
`python ez-sound-capture.py`

## How to Use this app

1. **Select Input Source**: The program lists all available microphones, including loopback devices. Select the one you want to use for recording.

2. **Set Recording Options**: You can choose to save your recording as an MP3, normalize the audio, or cut silence. Check the corresponding boxes to enable these options.

3. **Monitor Audio Levels**: The program provides real-time monitoring of audio levels. This can help you ensure that your audio is being captured at the right volume.

4. **Start/Stop Recording**: Click the 'Start recording' button (⏺️) to begin recording. During recording, the button changes to a 'Stop' button (⏹️). Click it again to stop the recording. The program also provides a 'Pause' button (⏸️) to pause and resume the recording.

5. **Save Your Recording**: Once you stop the recording, the program will automatically save audio file to `./recordings/<recording_datetime>/output.wav`. If you chose to save as MP3, the program will also save mp3 file to the same directory.
