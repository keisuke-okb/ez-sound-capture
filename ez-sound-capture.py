import os
import time
import json
import soundcard as sc
import soundfile as sf
import tkinter as tk
import customtkinter as ctk
import threading
import numpy as np

from types import SimpleNamespace
from datetime import datetime
from pydub import AudioSegment
from pydub.effects import normalize

global monitoring, recording, pause, realtime_levels, input_souce_id, data, backup_dir

def dict_to_namespace(data):
    if isinstance(data, dict):
        for key, value in data.items():
            data[key] = dict_to_namespace(value)
        return SimpleNamespace(**data)
    else:
        return data

SETTINGS = dict_to_namespace(json.load(open("settings.json", "r", encoding="utf-8")))
LANG = dict_to_namespace(json.load(open(f"{SETTINGS.gui.lang}.json", "r", encoding="utf-8")))
recording = False
pause = False
data = None

realtime_levels = np.array([0.0, 0.0])


def convert_seconds(seconds):
    seconds = int(seconds)
    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def backup_data_every(interval, backup_dir):
    global recording, data
    t = 0
    while recording:
        time.sleep(1)
        t += 1
        if interval == t:
            # Save the data to a npy file with the current date and time in the file name
            # np.save(f"./{backup_dir}/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.npy", data)
            np.savez_compressed(f"./{backup_dir}/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.npz", data)
            t = 0


def monitoring_mic(sc_id):
    global realtime_levels, monitoring
    with sc.get_microphone(id=sc_id, include_loopback=True).recorder(samplerate=SETTINGS.recording.sample_rate) as mic:
        while monitoring:
            # realtime_levels = np.mean(mic.record(numframes=SETTINGS.recording.sample_rate // 30), axis=0)
            # realtime_levels = mic.record(numframes=SETTINGS.recording.sample_rate // 30)[0]
            realtime_levels = np.max(mic.record(), axis=0)


def record_from_mic(recording_ftame):
    global data, input_souce_id, pause, is_silence_cut
    data = None
    with sc.get_microphone(id=input_souce_id, include_loopback=True).recorder(samplerate=SETTINGS.recording.sample_rate) as mic:
        while recording:
            _data = mic.record(numframes=SETTINGS.recording.sample_rate)
            if not pause:
                if data is None:
                    data = _data
                else:
                    if is_silence_cut.get():
                        if not np.all(np.abs(_data) < SETTINGS.recording.silence_threshold):
                            data = np.concatenate((data, _data))
                    else:
                        data = np.concatenate((data, _data))
                
                sec = data.shape[0] / SETTINGS.recording.sample_rate
                str_l = "[REC " if int(sec) % 2 == 0 else "[    "
                str_r = "]"
                t = convert_seconds(sec)
                recording_ftame.label_time.configure(text=str_l + t + str_r, text_color="#ff3333")

            
            else:
                recording_ftame.label_time.configure(text=LANG.labels.RecordingFrame.text_pause, text_color="#888888")

        else:
            # Finished recording
            recording_ftame.label_time.configure(text="00:00:00", text_color="#ffffff")


def update_levels(monitor_frame):
    global monitoring, realtime_levels
    def boost(v):
        return np.log2(np.abs(v) + 1)
    
    while True:
        # print(realtime_levels)
        lvs = boost(boost(realtime_levels))
        r_ch = 0 if len(realtime_levels) == 1 else 1
        monitor_frame.progress_l.set(lvs[0])
        monitor_frame.progress_r.set(lvs[r_ch])
        time.sleep(1 / 30)


class EzSoundCaptureApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.title("EZ Sound Capture")
        self.fonts = (LANG.fonts.font, LANG.fonts.font_size)
        self.resizable(False, False)
        self.init_gui()
    
    def init_gui(self):
        self.setting_frame = SettingFrame(self, header_name=LANG.labels.SettingFrame.header_name)
        self.setting_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.monitor_frame = MonitorFrame(self, header_name=LANG.labels.MonitorFrame.header_name)
        self.monitor_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.recording_frame = RecordingFrame(self, header_name=LANG.labels.RecordingFrame.header_name)
        self.recording_frame.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        thread = threading.Thread(target=update_levels, args=(self.monitor_frame,), daemon=True)
        thread.start()

class SettingFrame(ctk.CTkFrame):
    def __init__(self, *args, header_name=LANG.labels.SettingFrame.header_name, **kwargs):
        super().__init__(*args, **kwargs)
        self.fonts = (LANG.fonts.font, LANG.fonts.font_size)
        self.header_name = header_name
        self.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.init_vars()
        self.init_gui()
    
    def init_vars(self):
        self.input_source = tk.StringVar()
        self.int_mp3 = tk.IntVar(value=1)
        self.int_normalize = tk.IntVar(value=1)
        self.int_cut = tk.IntVar(value=1)

    def init_gui(self):
        # input_source
        self.label_input_source = ctk.CTkLabel(self, text=LANG.labels.SettingFrame.label_input_source, font=self.fonts)
        self.label_input_source.grid(row=0, column=0, padx=5, pady=5)
        microphones = sc.all_microphones(include_loopback=True)
        self.microphones_dict = {f"{str(mic).replace('<', '').split(' ')[0]} {mic.name}": mic for mic in microphones}
        self.input_source_combo = ctk.CTkComboBox(master=self, width=300, font=self.fonts, values=self.microphones_dict.keys(), state="readonly", command=self.set_input_source, variable=self.input_source)
        self.input_source_combo.grid(row=0, column=1, padx=5, pady=5, columnspan=3)
        self.set_default_microphone()

        global is_silence_cut, is_mp3, is_normalize
        is_silence_cut = tk.IntVar(value=1)
        is_mp3 = tk.IntVar(value=1)
        is_normalize = tk.IntVar(value=1)
        self.label_option = ctk.CTkLabel(self, text=LANG.labels.SettingFrame.label_option, font=self.fonts)
        self.label_option.grid(row=1, column=0, padx=5, pady=5)
        self.checkbox_cut = ctk.CTkCheckBox(self, text=LANG.labels.SettingFrame.label_cut, font=self.fonts, variable=is_silence_cut, onvalue=1, offvalue=0)
        self.checkbox_cut.grid(row=1, column=1, padx=5, pady=5)
        self.checkbox_mp3 = ctk.CTkCheckBox(self, text=LANG.labels.SettingFrame.label_mp3, font=self.fonts, variable=is_mp3, onvalue=1, offvalue=0)
        self.checkbox_mp3.grid(row=1, column=2, padx=5, pady=5)
        self.checkbox_normalize = ctk.CTkCheckBox(self, text=LANG.labels.SettingFrame.label_normalize, font=self.fonts, variable=is_normalize, onvalue=1, offvalue=0)
        self.checkbox_normalize.grid(row=1, column=3, padx=5, pady=5)

    def set_default_microphone(self):
        mic = sc.get_microphone(id=sc.default_speaker().id, include_loopback=True)
        key = f"{str(mic).replace('<', '').split(' ')[0]} {mic.name}"
        self.set_input_source(key)
        global input_souce_id
        input_souce_id = mic.id

    def set_input_source(self, key):
        global monitoring
        monitoring = False
        time.sleep(0.5)
        mic = self.microphones_dict[key]
        self.input_source.set(key)
        global input_souce_id
        input_souce_id = mic.id
        # print(mic.id)
        monitoring = True
        thread = threading.Thread(target=monitoring_mic, args=(mic.id,), daemon=True)
        thread.start()


class MonitorFrame(ctk.CTkFrame):
    def __init__(self, *args, header_name=LANG.labels.MonitorFrame.header_name, **kwargs):
        super().__init__(*args, **kwargs)
        self.fonts = (LANG.fonts.font, LANG.fonts.font_size)
        self.header_name = header_name
        self.init_vars()
        self.init_gui()

    def init_vars(self):
        pass

    def init_gui(self):
        self.label_level = ctk.CTkLabel(self, text=LANG.labels.MonitorFrame.label_level, font=self.fonts)
        self.label_level.grid(row=0, column=0, padx=5, pady=5, rowspan=2)
        self.progress_l = ctk.CTkProgressBar(self, width=300, progress_color="#55ff33")
        self.progress_l.grid(row=0, column=1, padx=5, pady=1)
        self.progress_r = ctk.CTkProgressBar(self, width=300, progress_color="#55ff33")
        self.progress_r.grid(row=1, column=1, padx=5, pady=1)

class RecordingFrame(ctk.CTkFrame):
    def __init__(self, *args, header_name=LANG.labels.RecordingFrame.header_name, **kwargs):
        super().__init__(*args, **kwargs)
        self.fonts = (LANG.fonts.font, LANG.fonts.font_size)
        self.fonts_big = (LANG.fonts.font, LANG.fonts.font_size_big)
        self.fonts_big_mono = (LANG.fonts.font_mono, LANG.fonts.font_size_big)
        self.header_name = header_name
        self.grid_columnconfigure((0, 1, 2), weight=1)
        self.init_vars()
        self.init_gui()

    def init_vars(self):
        pass

    def init_gui(self):
        self.recording_button = ctk.CTkButton(
            master=self, width=50, height=50, font=self.fonts_big, border_width=0,
            text=LANG.labels.RecordingFrame.label_recording, command=self.start_recording, fg_color="#bb0000", hover_color="#ee0000")
        self.recording_button.grid(row=0, column=0, padx=5, pady=5)
        self.label_time = ctk.CTkLabel(self, text="00:00:00", width=200, font=self.fonts_big_mono)
        self.label_time.grid(row=0, column=1, padx=5, pady=5)
        self.recording_pause_button = ctk.CTkButton(
            master=self, width=50, height=50, font=self.fonts_big, border_width=0,
            text=LANG.labels.RecordingFrame.label_recording_pause, command=self.pause_recording, fg_color="#222222", hover_color="#555555")
        self.recording_pause_button.grid(row=0, column=2, padx=5, pady=5)
        # threading.Thread(target=update_time, args=(self,), daemon=True).start()

    def start_recording(self):
        global input_souce_id, recording, data, backup_dir, pause
        if not recording:
            recording = True
            self.recording_button.configure(text=LANG.labels.RecordingFrame.label_stop)
            backup_dir = f"./recordings/{datetime.now().strftime('%Y%m%d_%H%M%S')}/"
            os.makedirs(backup_dir, exist_ok=True)
            # Start the thread to backup data every BACKUP_INTERVAL seconds
            threading.Thread(target=backup_data_every, args=(SETTINGS.recording.backup_interval, backup_dir), daemon=True).start()
            threading.Thread(target=record_from_mic, args=(self,), daemon=True).start()
        
        else:
            if pause:
                pause = False
                self.recording_button.configure(text=LANG.labels.RecordingFrame.label_stop)
                return
            
            else:
                recording = False
                self.recording_button.configure(text=LANG.labels.RecordingFrame.label_recording)
                # data = np.concatenate(data, axis=0)
                sf.write(file=backup_dir + "output.wav", data=data, samplerate=SETTINGS.recording.sample_rate)
                
                try:
                    global is_silence_cut, is_mp3, is_normalize
                    if is_normalize.get():
                        audio = AudioSegment.from_wav(backup_dir + "output.wav")
                        normalized_audio = normalize(audio)
                        normalized_audio.export(backup_dir + "output.wav", format='wav')
                    
                    if is_mp3.get():
                        audio = AudioSegment.from_wav(backup_dir + "output.wav")
                        audio.export(backup_dir + "output.mp3", format='mp3', bitrate='320k')
                    
                except Exception as e:
                    print(e)
                    pass

    def pause_recording(self):
        global input_souce_id, recording, data, backup_dir, pause
        if not recording:
            pause = False
            return

        if recording:
            if pause:
                pause = False
                self.recording_button.configure(text=LANG.labels.RecordingFrame.label_stop)
            else:
                pause = True
                self.recording_button.configure(text=LANG.labels.RecordingFrame.label_recording)


def main():
    global monitoring
    global close
    monitoring = True
    app = EzSoundCaptureApp()
    app.mainloop()
    monitoring = False
    exit()

if __name__ == "__main__":
    main()
