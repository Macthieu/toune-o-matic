import numpy as np
from scipy.io.wavfile import write

samplerate = 44100  # 44.1 kHz
duration = 2.0      # 2 secondes
frequency = 440.0   # Tonalité A4 (La 440 Hz)

t = np.linspace(0., duration, int(samplerate * duration))
amplitude = np.iinfo(np.int16).max
data = amplitude * np.sin(2 * np.pi * frequency * t)

# Génère un son stéréo : 2 canaux identiques
data_stereo = np.column_stack((data, data))

write("test.wav", samplerate, data_stereo.astype(np.int16))
