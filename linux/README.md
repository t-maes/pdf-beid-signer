# Signateur, Trieur et Lecteur PDF eID Belge (v1.0.2)

Une application épurée, performante et moderne (Light / Dark Mode) conçue pour la gestion, le tri et la signature cryptographique de documents PDF à l'aide de la carte d'identité électronique (eID) belge.

Développé par **Thierry Maes** ([info@tmaes.be](mailto:info@tmaes.be)).

---

## 🚀 Fonctionnalités phares

- **Design épuré "Minimaliste" :** Pas de boutons superflus. L'interface se concentre exclusivement sur le document.
- **Centre de Tri Intelligent :** Un bouton vert pour signer via `pyhanko`, un bouton rouge pour écarter/refuser le document vers un dossier de rejet.
- **Purge de Source :** Option mémorisable pour supprimer automatiquement le fichier source après traitement.
- **Ergonomie Implicite :**
  - Navigation par pages : Flèches `Gauche` / `Droite` du clavier.
  - Zoom fluide : Molette de la souris (ou `Ctrl + Molette`).
  - Validation : Touche `Entrée` pour signer instantanément.
- **Thème Sombre Dynamique 🌙 :** Basculement à chaud et mémorisation automatique de votre préférence visuelle d'une session à l'autre.
- **Isolation des Paramètres ⚙️ :** Pop-up de configuration sécurisé avec boutons d'annulation ou de validation stricte.

---

## 🛠️ Dépendances requises

Pour exécuter le script, assurez-vous d'avoir installé les paquets suivants :

```bash
pip install PyMuPDF Pillow pyhanko[beid]
```

*Sur Linux Ubuntu, le pilote eID et la bibliothèque PKCS11 doivent être présents :* `/usr/lib/x86_64-linux-gnu/pkcs11/beidpkcs11.so`

---

## 💻 Comment le lancer ?

### Mode standard
```bash
python3 pdf_signer_gui_v1.py
```

### Création du lanceur de Bureau (Linux .desktop)
Pour lancer l'application d'un simple double-clic sans ouvrir le terminal, créez un fichier `~/Bureau/Signateur_eID.desktop` :

```ini
[Desktop Entry]
Version=1.0
Type=Application
Name=Signateur & Trieur eID
Comment=Centre de tri et signature de PDF par eID Belge
Exec=python3 /home/thierry/pdf_signer_gui_v1.py
Icon=document-sign
Terminal=false
Categories=Office;Utility;
```
*Faites ensuite un clic droit sur le fichier du Bureau -> "Autoriser le lancement".*

---

## 📄 Licence & Support
Développé pour un usage professionnel et collaboratif. Pour toute question ou coup de pouce à l'édition, contactez **info@tmaes.be**.
