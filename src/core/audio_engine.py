import wave
import alsaaudio
from pydub import AudioSegment
import io

class AudioEngine:
    def __init__(self, device='hw:1,0'):
        self.device = device
        self.output = None

    def play_wav(self, filename):
        with wave.open(filename, 'rb') as wav:
            channels = wav.getnchannels()
            rate = wav.getframerate()
            width = wav.getsampwidth()
            framesize = 1024

            # Map des formats
            format_map = {
                1: alsaaudio.PCM_FORMAT_U8,
                2: alsaaudio.PCM_FORMAT_S16_LE,
                3: alsaaudio.PCM_FORMAT_S24_LE,
                4: alsaaudio.PCM_FORMAT_S32_LE
            }

            if width not in format_map:
                raise ValueError(f"Unsupported sample width: {width}")

            # Initialiser la sortie
            self.output = alsaaudio.PCM(
                type=alsaaudio.PCM_PLAYBACK,
                mode=alsaaudio.PCM_NORMAL,
                device=self.device
            )

            self.output.setchannels(channels)
            self.output.setrate(rate)
            self.output.setformat(format_map[width])
            self.output.setperiodsize(framesize)

            print(f"Lecture : {filename} ({channels} ch, {rate} Hz, {width*8} bits)")

            data = wav.readframes(framesize)
            while data:
                self.output.write(data)
                data = wav.readframes(framesize)

    def play_any_file(self, filename):
        print(f"Décodage du fichier audio : {filename}")

        # Charger le fichier avec pydub (via ffmpeg)
        audio = AudioSegment.from_file(filename)

        channels = audio.channels
        rate = audio.frame_rate
        width = audio.sample_width  # en octets

        print(f"Format détecté : {channels} ch, {rate} Hz, {width*8} bits")

        format_map = {
            1: alsaaudio.PCM_FORMAT_U8,
            2: alsaaudio.PCM_FORMAT_S16_LE,
            3: alsaaudio.PCM_FORMAT_S24_LE,
            4: alsaaudio.PCM_FORMAT_S32_LE
        }

        if width not in format_map:
            raise ValueError(f"Unsupported sample width: {width}")

        # Configurer la sortie ALSA
        self.output = alsaaudio.PCM(
            type=alsaaudio.PCM_PLAYBACK,
            mode=alsaaudio.PCM_NORMAL,
            device=self.device
        )

        self.output.setchannels(channels)
        self.output.setrate(rate)
        self.output.setformat(format_map[width])

        # Convertir en bytes bruts (PCM)
        raw_data = audio.raw_data

        chunk_size = 1024 * width * channels
        for i in range(0, len(raw_data), chunk_size):
            chunk = raw_data[i:i+chunk_size]
            self.output.write(chunk)
