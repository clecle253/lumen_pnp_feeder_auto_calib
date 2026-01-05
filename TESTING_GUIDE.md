# Guide de Test du Plugin LumenPnP

## Étape 1 : Copier le plugin dans OpenPnP

Le plugin doit être placé dans le répertoire des scripts d'OpenPnP.

**Localisation par défaut :**
- Windows : `C:\Users\<username>\.openpnp2\scripts\`
- Linux : `~/.openpnp2/scripts/`
- Mac : `~/Library/Application Support/OpenPnP/scripts/`

**Fichiers à copier :**
```
.openpnp2/scripts/
├── LumenPnP/              (tout le dossier)
│   ├── __init__.py
│   ├── README.md
│   ├── gui/
│   │   ├── __init__.py
│   │   └── main_window.py
│   └── core/
│       └── __init__.py
└── LumenPnP_Plugin.py     (fichier de lancement)
```

## Étape 2 : Lancer le plugin depuis OpenPnP

1. Ouvrir OpenPnP
2. Menu `Scripts` → `Open Scripts Directory` (pour vérifier l'emplacement)
3. Menu `Scripts` → `LumenPnP_Plugin.py` → `Run`
4. Une nouvelle fenêtre devrait s'ouvrir avec l'interface du plugin

## Étape 3 : Tester les fonctionnalités

### Tab "Feeder Calibration"
- La liste des feeders devrait se remplir automatiquement
- Tester le bouton "Scan Feeders"
- Les logs devraient s'afficher en bas

### Dépannage

**Problème : "No module named 'tkinter'"**
- C'est normal, le plugin utilisera Swing à la place
- Vérifier que le message "Tkinter not available, using Swing" apparaît

**Problème : La fenêtre ne s'ouvre pas**
- Vérifier les logs OpenPnP (onglet Log)
- Vérifier que le fichier est bien dans le bon répertoire

**Problème : Erreur d'import**
- Vérifier que tous les fichiers `__init__.py` sont présents
- Vérifier la structure des dossiers

## Commande rapide pour copier (PowerShell)

```powershell
# Trouver le répertoire scripts d'OpenPnP
$openpnpScripts = "$env:USERPROFILE\.openpnp2\scripts"

# Créer le répertoire si nécessaire
New-Item -ItemType Directory -Path $openpnpScripts -Force

# Copier le plugin
Copy-Item -Path "c:\Users\cleme\Desktop\open pnp plugin\LumenPnP" -Destination $openpnpScripts -Recurse -Force
Copy-Item -Path "c:\Users\cleme\Desktop\open pnp plugin\LumenPnP_Plugin.py" -Destination $openpnpScripts -Force

Write-Host "Plugin copié avec succès dans $openpnpScripts"
```

## Prochaines étapes

Une fois le plugin testé et fonctionnel :
1. Intégrer la logique de calibration
2. Ajouter la gestion des erreurs
3. Implémenter les autres fonctionnalités (KiCad, Fast Travel)
