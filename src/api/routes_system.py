import subprocess
import re
import logging
from flask import Blueprint, jsonify, request

logger = logging.getLogger("SystemAPI")
bp = Blueprint("system", __name__, url_prefix="/api/system")

@bp.route("/outputs")
def get_outputs():
    try:
        res = subprocess.run(["aplay", "-l"], capture_output=True, text=True)
        cards = []
        for line in res.stdout.splitlines():
            if line.startswith("card"):
                m = re.match(r'card (\d+): (.*?) \[.*', line)
                if m: cards.append({"id": int(m.group(1)), "name": m.group(2)})
        
        # AJOUT MANUEL DE L'OPTION BLUETOOTH
        cards.append({"id": 999, "name": "🎧 Bluetooth (BlueALSA)"})
        
        return jsonify({"ok": True, "outputs": cards})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@bp.route("/output", methods=["POST"])
def set_output():
    data = request.json or {}
    card_id = data.get("id")
    if card_id is None: return jsonify({"ok": False}), 400

    try:
        if card_id == 999:
            # CONFIGURATION SPÉCIALE BLUETOOTH
            # On utilise le plugin 'bluealsa'
            opt = '--player alsa:device=bluetooth_speaker:mixer=software'
        else:
            # CONFIGURATION STANDARD DAC
            opt = f'--player alsa:device=plughw:{card_id},0:mixer=hardware:mixer_control=Digital:buffer_time=200'

        cmd_sed = ["sudo", "/usr/bin/sed", "-i", f's/SNAPCLIENT_OPTS=.*/SNAPCLIENT_OPTS="{opt}"/g', "/etc/default/snapclient"]
        subprocess.run(cmd_sed, check=True)
        subprocess.run(["sudo", "systemctl", "restart", "snapclient"], check=True)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500