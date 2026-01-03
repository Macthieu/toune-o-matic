from src.app import create_app

# Création de l'application Web
app = create_app()

if __name__ == "__main__":
    print("🚀 Démarrage de Toune-o-Matic (Mode Développement Mac)...")
    print("👉 Ouvrez votre navigateur sur : http://localhost:5001")
    # Changement de port: 5000 -> 5001 pour éviter le conflit AirPlay
    app.run(host='0.0.0.0', port=5001, debug=True)
