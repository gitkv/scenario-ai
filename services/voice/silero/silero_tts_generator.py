import os
import re
import torch
import wave
import timeit
import logging
from datetime import datetime, timedelta
from num2words import num2words
from ..translit import Translit

class Stats:
    def __init__(self, preprocessed_text_len: int):
        self.start_time = int(datetime.now().timestamp())
        self.preprocessed_text_len = preprocessed_text_len
        self.preprocessed_text_len: int
        self.processed_text_len: int = 0
        self.done_percent: float = 0
        self.start_time: int
        self.warmup_seconds: int = 0
        self.run_time: str = "0:00:00"
        self.run_time_est: str = "0:00:00"
        self.wave_data_current: int = 0
        self.wave_data_total: int = 0
        self.wave_mib: int = 0
        self.wave_mib_est: int = 0
        self.tts_time: str = "0:00:00"
        self.tts_time_est: str = "0:00:00"
        self.tts_time_current: str = "0:00:00"
        self.line_number: int = 0

        self.sample_rate = 48000
        self.torch_device = 'auto'
        self.torch_num_threads = 6
        self.line_length_limits = {
            'aidar': 870,
            'baya': 860,
            'eugene': 1000,
            'kseniya': 870,
            'xenia': 957,
            'random': 355,
        }
        self.wave_file_size_limit = 512 * 1024 * 1024

        self.wave_channels = 1
        self.wave_header_size = 44
        self.wave_sample_width = int(16 / 8)

    def update(self, line: str, next_chunk_size: int):
        self.line_number += 1
        self.wave_data_total += next_chunk_size
        self.wave_data_current += next_chunk_size
        self.processed_text_len += len(line)
        # Percentage calculation
        self.done_percent = round(self.processed_text_len * 100 / self.preprocessed_text_len, 1)
        # Wave size estimation
        self.wave_mib = int((self.wave_data_total / 1024 / 1024))
        self.wave_mib_est = int(
            (self.wave_data_total / 1024 / 1024 * self.preprocessed_text_len / self.processed_text_len))

        # Don't count first two lines time as pytorch-cuda warmup is very slow
        if (self.line_number == 3):
            self.warmup_seconds: int = int(datetime.now().timestamp()) - self.start_time
            logging.debug(F"Warmup took {str(timedelta(seconds=self.warmup_seconds))} seconds")

        # Run time estimation
        current_time: int = int(datetime.now().timestamp())
        run_time_s: int = current_time - self.start_time - self.warmup_seconds
        run_time_est_s: int = int(run_time_s * self.preprocessed_text_len / self.processed_text_len)
        self.run_time = str(timedelta(seconds=run_time_s))
        self.run_time_est = str(timedelta(seconds=run_time_est_s))

        # TTS time estimation
        tts_time_s: int = int((self.wave_data_total / self.wave_channels / self.wave_sample_width / self.sample_rate))
        tts_time_est_s: int = int((tts_time_s * self.preprocessed_text_len / self.processed_text_len))
        self.tts_time = str(timedelta(seconds=tts_time_s))
        self.tts_time_est = str(timedelta(seconds=tts_time_est_s))
        tts_time_current_s: int = int((self.wave_data_current / self.wave_channels / self.wave_sample_width / self.sample_rate))
        self.tts_time_current = str(timedelta(seconds=tts_time_current_s))

    def next_file(self):
        self.wave_data_current = 0

class SileroTTSGenerator:
    def __init__(self):
        self.model_id = 'v3_1_ru'
        self.language = 'ru'
        self.put_accent = True
        self.put_yo = True
        self.sample_rate = 48000
        self.torch_device = 'auto'
        self.torch_num_threads = 2
        self.line_length_limits = {
            'aidar': 870,
            'baya': 860,
            'eugene': 1000,
            'kseniya': 870,
            'xenia': 957,
            'random': 355,
        }
        self.wave_file_size_limit = 512 * 1024 * 1024
        self.wave_channels = 1
        self.wave_header_size = 44
        self.wave_sample_width = int(16 / 8)
        self.download_models_config()
        self.tts_model = self.init_model(self.torch_device, self.torch_num_threads)
        self.translit = Translit()

    def init_model(self, device, threads_count):
        logging.info("Initializing model")
        t0 = timeit.default_timer()

        torch._C._jit_set_profiling_mode(False)

        if not torch.cuda.is_available() and device == "auto":
            device = 'cpu'
        if torch.cuda.is_available() and device == "auto" or device == "cuda":
            torch_dev = torch.device("cuda", 0)
            gpus_count = torch.cuda.device_count()
            logging.info("Using {} GPU(s)...".format(gpus_count))
        else:
            torch_dev = torch.device(device)
        torch.set_num_threads(threads_count)
        tts_model, tts_sample_text = torch.hub.load(repo_or_dir='snakers4/silero-models', model='silero_tts', language=self.language, speaker=self.model_id)
        logging.info("Setup takes {:.2f}".format(timeit.default_timer() - t0))

        logging.info("Loading model")
        t1 = timeit.default_timer()
        tts_model.to(torch_dev)
        logging.info("Model to device takes {:.2f}".format(timeit.default_timer() - t1))

        if torch.cuda.is_available() and device == "auto" or device == "cuda":
            logging.info("Synchronizing CUDA")
            t2 = timeit.default_timer()
            torch.cuda.synchronize()
            logging.info("Cuda Sync takes {:.2f}".format(timeit.default_timer() - t2))
        logging.info("Model is loaded")
        return tts_model
    
    def transliterate_to_russian(self, text):
        return self.translit.transliterate(text)

    @staticmethod
    def spell_digits(line) -> str:
        digits = re.findall(r'\d+', line)
        digits = sorted(digits, key=len, reverse=True)
        for digit in digits:
            line = line.replace(digit, num2words(int(digit), lang='ru'))
        return line
    
    def find_split_position(self, line: str, old_position: int, char: str, limit: int) -> int:
        positions: list = self.find_char_positions(line, char)
        new_position: int = self.find_max_char_position(positions, limit)
        position: int = max(new_position, old_position)
        return position
    
    def find_max_char_position(self, positions: list, limit: int) -> int:
        max_position: int = 0
        for pos in positions:
            if pos < limit:
                max_position = pos
            else:
                break
        return max_position

    def find_char_positions(self, string: str, char: str) -> list:
        pos: list = []  # list to store positions for each 'char' in 'string'
        for n in range(len(string)):
            if string[n] == char:
                pos.append(n)
        return pos

    def preprocess_text(self, lines, length_limit):
        logging.info(f"Preprocessing text with line length limit={length_limit}")

        if length_limit > 3:
            length_limit = length_limit - 2
        else:
            logging.error(f"ERROR: line length limit must be >= 3, got {length_limit}")
            exit(1)

        preprocessed_text_len = 0
        preprocessed_lines = []
        for line in lines:
            line = line.strip()
            if line == '\n' or line == '':
                continue

            line = self.transliterate_to_russian(line)

            line = line.replace("…", "...")
            line = line.replace("*", " звёздочка ")
            line = re.sub(r'(\d+)[\.|,](\d+)', r'\1 и \2', line)
            line = line.replace("%", " процентов ")
            line = line.replace(" г.", " году")
            line = line.replace(" гг.", " годах")
            line = re.sub("д.\s*н.\s*э.", " до нашей эры", line)
            line = re.sub("н.\s*э.", " нашей эры", line)
            line = self.spell_digits(line)

            while len(line) > 0:
                if len(line) < length_limit:
                    line = line + "\n"
                    preprocessed_lines.append(line)
                    preprocessed_text_len += len(line)
                    break

                split_position = 0
                split_position = self.find_split_position(line, split_position, ".", length_limit)
                split_position = self.find_split_position(line, split_position, "!", length_limit)
                split_position = self.find_split_position(line, split_position, "?", length_limit)

                if split_position == 0:
                    split_position = self.find_split_position(line, split_position, " ", length_limit)

                if split_position == 0:
                    split_position = length_limit

                part = line[0:split_position + 1] + "\n"
                preprocessed_lines.append(part)
                preprocessed_text_len += len(part)
                line = line[split_position + 1:]

        return preprocessed_lines, preprocessed_text_len
    
    def init_wave_file(self, name: str, channels: int, sample_width: int, rate: int):
        os.makedirs(os.path.dirname(name), exist_ok=True)  # Create the directory if it doesn't exist
        logging.info(f'Initialising wave file {name} with {channels} channels {sample_width} sample width {rate} sample rate')
        wf = wave.open(name, 'wb')
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        return wf


    def write_wave_chunk(self, wf, audio, audio_size, wave_data_limit, wave_file_number, stats):
        next_chunk_size = int(audio.size()[0] * self.wave_sample_width)
        if audio_size + next_chunk_size > wave_data_limit:
            logging.info(f"Wave written {audio_size} limit={wave_data_limit} - creating new wave!")
            wf.close()
            stats.next_file()
            wave_file_number += 1
            audio_size = self.wave_header_size + next_chunk_size
            wf = self.init_wave_file(f"{output_filename}_{speaker}_{wave_file_number}.wav", self.wave_channels, self.wave_sample_width, self.sample_rate)
        else:
            audio_size += next_chunk_size
            wf.writeframes((audio * 32767).numpy().astype('int16'))
        return wf, audio_size, wave_file_number


    def process_tts(self, tts_model, lines, output_filename, wave_data_limit, preprocessed_text_len, speaker):
        logging.info("Starting TTS")
        s = Stats(preprocessed_text_len)
        current_line = 0
        audio_size = self.wave_header_size
        wave_file_number = 0
        next_chunk_size = 0
        wf = self.init_wave_file(output_filename, self.wave_channels, self.wave_sample_width, self.sample_rate)
        
        for line in lines:
            if line == '\n' or line == '':
                continue
            
            logging.debug(f"{current_line}/{len(lines)} {s.run_time}/{s.run_time_est} "
                  f"{s.processed_text_len}/{s.preprocessed_text_len} chars "
                  f"{s.wave_mib}/{s.wave_mib_est} MiB {s.tts_time}/{s.tts_time_est} TTS "
                  f"{s.tts_time_current}@part{wave_file_number} {s.done_percent}% : {line}"
            )
            
            try:
                audio = tts_model.apply_tts(text=line, speaker=speaker, sample_rate=self.sample_rate,  put_accent=self.put_accent, put_yo=self.put_yo)
                next_chunk_size = int(audio.size()[0] * self.wave_sample_width)
                wf, audio_size, wave_file_number = self.write_wave_chunk(wf, audio, audio_size,
                                                                         wave_data_limit, wave_file_number, s)
            except ValueError:
                logging.error("TTS failed!")
                next_chunk_size = 0
            
            current_line += 1
            s.update(line, next_chunk_size)


    def generate_audio_file(self, text, selected_speaker, output_filename):
        logging.info("Start generating audio file")
        origin_lines = [text]
        line_length_limit = self.line_length_limits[selected_speaker]
        preprocessed_lines, preprocessed_text_len = self.preprocess_text(origin_lines, line_length_limit)
        self.process_tts(self.tts_model, preprocessed_lines, output_filename, self.wave_file_size_limit, preprocessed_text_len, speaker=selected_speaker)


    def download_models_config(self):
        models_config_path = 'latest_silero_models.yml'
        if not os.path.exists(models_config_path):
            torch.hub.download_url_to_file('https://raw.githubusercontent.com/snakers4/silero-models/master/models.yml', models_config_path, progress=False)
        else:
            logging.info("Models config already exists, skipping download.")
