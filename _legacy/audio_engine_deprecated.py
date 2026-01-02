import wave
import alsaaudio
from pydub import AudioSegment


class AudioEngine:
    def __init__(self, device: str = "default"):
        self.device = device
        self.output = None

    def _open_pcm(self, channels: int, rate: int, fmt, periodsize: int = 1024):
        # Ouverture ALSA sans utiliser les set* dépréciés
        self.output = alsaaudio.PCM(
            type=alsaaudio.PCM_PLAYBACK,
            mode=alsaaudio.PCM_NORMAL,
            device=self.device,
            channels=channels,
            rate=rate,
            format=fmt,
            periodsize=periodsize,
        )

    def play_wav(self, filename: str):
        with wave.open(filename, "rb") as wav:
            channels = wav.getnchannels()
            rate = wav.getframerate()
            width = wav.getsampwidth()  # en octets
            framesize = 1024

            format_map = {
                1: alsaaudio.PCM_FORMAT_U8,
                2: alsaaudio.PCM_FORMAT_S16_LE,
                3: alsaaudio.PCM_FORMAT_S24_LE,
                4: alsaaudio.PCM_FORMAT_S32_LE,
            }
            if width not in format_map:
                raise ValueError(f"Unsupported sample width: {width}")

            self._open_pcm(channels=channels, rate=rate, fmt=format_map[width], periodsize=framesize)

            print(f"Lecture : {filename} ({channels} ch, {rate} Hz, {width*8} bits)")

            data = wav.readframes(framesize)
            while data:
                self.output.write(data)
                data = wav.readframes(framesize)

    def play_any_file(self, filename: str):
        print(f"Décodage du fichier audio : {filename}")

        audio = AudioSegment.from_file(filename)

        channels = audio.channels
        rate = audio.frame_rate
        width = audio.sample_width  # en octets

        print(f"Format détecté : {channels} ch, {rate} Hz, {width*8} bits")

        format_map = {
            1: alsaaudio.PCM_FORMAT_U8,
            2: alsaaudio.PCM_FORMAT_S16_LE,
            3: alsaaudio.PCM_FORMAT_S24_LE,
            4: alsaaudio.PCM_FORMAT_S32_LE,
        }
        if width not in format_map:
            raise ValueError(f"Unsupported sample width: {width}")

        self._open_pcm(channels=channels, rate=rate, fmt=format_map[width], periodsize=1024)

        raw_data = audio.raw_data
        chunk_size = 1024 * width * channels  # frames * bytes/frame

        for i in range(0, len(raw_data), chunk_size):
            chunk = raw_data[i : i + chunk_size]
            self.output.write(chunk)