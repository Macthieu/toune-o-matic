# 🎛️ Toune-o-matic

**Toune-o-matic** est un **progiciel audio avancé** conçu pour le **Raspberry Pi**, combinant les fonctionnalités de **Volumio Premium**, de **Logitech Media Server**, et des capacités de gestion matérielle fines comme sur un système hi-fi de studio. Il agit comme le **cerveau central d’un meuble audio haute-fidélité** intégrant **sources analogiques**, **DACs**, **amplis**, **scripts personnalisés** et plus encore.

---

![Python version](https://img.shields.io/badge/python-3.11-blue.svg)
![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi-lightgrey.svg)
![License](https://img.shields.io/github/license/Macthieu/toune-o-matic.svg)
![Build](https://img.shields.io/badge/build-passing-brightgreen.svg)
![Made with ❤️](https://img.shields.io/badge/made%20with-%E2%9D%A4-red)

---

## 🗂️ Table des matières

- [🎧 Fonctionnalités](#-fonctionnalités)
- [🔧 Installation](#-installation)
- [🚀 Usage](#-usage)
- [📁 Configuration](#-configuration)
- [🎯 Objectif](#-objectif)
- [🌍 English version](#-english-version)

---

## 🎧 Fonctionnalités

- 📁 **Gestion de bibliothèques massives** (plusieurs To de FLAC, MP3, etc.)
- 🎶 **Lecture audio haute qualité** : FLAC, WAV, MP3, DSD, etc.
- 🔀 **Routage audio personnalisé** vers amplis ou enceintes
- 🎚️ **Contrôle précis** : volume, EQ, balance, crossfade, mute
- 🔌 **Support natif** des DACs / ADCs (USB, I2S, RCA)
- 🖲️ **Contrôle GPIO** : boutons, encodeurs rotatifs, télécommandes
- 🖥️ **Interface prévue** pour CLI, écran tactile ou navigateur
- 🌐 **API locale REST** : intégration domotique ou contrôle distant
- 📡 **Multi-zone / multi-DAC** (inspiré de Volumio Premium)
- 📻 **Radio Internet & services de streaming** (optionnels)
- 💾 **Indexation rapide** des fichiers avec tags ID3, jaquettes, paroles
- 🔊 **Serveur DLNA / UPnP**, compatible avec d’autres lecteurs

---

## 🔧 Installation

```bash
git clone https://github.com/Macthieu/toune-o-matic.git
cd toune-o-matic
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 🚀 Usage

Lecture simple d’un fichier :

```bash
python run.py play test.mp3
```

Configuration dans `config/settings.yaml` :

```yaml
audio_device: "hw:1,0"
```

---

## 🎯 Objectif

Offrir une plateforme **open-source**, **100 % locale**, **modulaire** et **audiophile**, conçue pour :

- remplacer les serveurs audio commerciaux (Volumio, Roon, LMS…)
- s’adapter à **n’importe quel meuble stéréo personnalisé**
- **intégrer des sources analogiques**, contrôles physiques, etc.

📌 Idéal pour les passionnés de son, makers, audiophiles, rétro-bricoleurs et bidouilleurs.

---

## 🌍 English version

**Toune-o-matic** is an advanced **audio control software suite** for **Raspberry Pi**, aiming to replicate and improve upon the features of Volumio Premium and Logitech Media Server — with deeper hardware control.

It acts as the **central brain of a hi-fi stereo cabinet**, connecting analog gear (DACs, preamps, amps, ADCs), and offering local playback, GPIO control, REST API, and smart routing features.

### Features:

- High-resolution playback: FLAC, WAV, MP3, DSD
- Massive library handling
- Custom audio routing and DSP chain
- GPIO button + rotary encoder control
- REST API for remote or smart home control
- Multi-DAC / multi-zone support
- Optional integration of streaming services
- DLNA / UPnP output
- Fully local and modular

---

## ✅ Status

🚧 Project is under **active development**. Contributions, suggestions, bug reports, and ideas are welcome!

---

## 📄 License

MIT – libre pour tous usages personnels ou professionnels.