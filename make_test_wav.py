import wave
import struct
import math

sample_rate = 44100
duration = 2  # secondes
frequency = 440.0  # Hz (note LA)

filename = "test.wav"

with wave.open(filename, 'w') as wav_file:
    wav_file.setnchannels(2)
    wav_file.setsampwidth(2)
    wav_file.setframerate(sample_rate)

    for i in range(int(duration * sample_rate)):
        value = int(32767.0 * math.sin(2.0 * math.pi * frequency * i / sample_rate))
        data = struct.pack('<hh', value, value)  # stéréo
        wav_file.writeframesraw(data)

print(f"Fichier {filename} généré.")
