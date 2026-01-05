# Plugin de Calibration de Feeders pour OpenPnP

Ce projet contient un script Python pour OpenPnP permettant de recalibrer automatiquement la position de tous les feeders (spécifiquement pensé pour les feeders Photon de LumenPnP).

> [!CAUTION]
> **PROJET EN COURS DE DÉVELOPPEMENT (WIP) - À UTILISER À VOS RISQUES ET PÉRILS**
>
> Ce projet est actuellement **dédié à ma configuration spécifique**. Il n'est pas encore généralisé et contient des valeurs en dur ou des comportements adaptés à ma machine.
>
> L'outil est amené à évoluer grandement pour devenir généraliste, autonome et sans configuration manuelle à l'avenir.
>
> **Licence** : Vous êtes libre de copier, modifier et distribuer ce code gratuitement et à volonté. C'est de l'Open Source. Cependant, aucune garantie n'est fournie quant à son fonctionnement sur votre machine.

## Installation

1.  Assurez-vous qu'OpenPnP est installé et configuré.
2.  Copiez le fichier `recalibrate_feeders.py` dans le dossier de scripts de votre configuration OpenPnP.
    *   Chemin typique : `[Dossier de configuration OpenPnP]/.openpnp/scripts/`
    *   Accessible via : `File` -> `Show Configuration Folder`.

## Configuration (IMPORTANT)

Avant de lancer le script, vous devez vérifier deux choses dans le fichier `recalibrate_feeders.py` (ouvrez-le avec un éditeur de texte) :

1.  **Fiducial Part** : 
    *   Le script cherche une "Pièce" (Part) nommée par défaut `"Fiducial-1mm"`. 
    *   **Vous devez créer cette pièce dans l'onglet "Parts" d'OpenPnP** si elle n'existe pas.
    *   Assurez-vous que les réglages de Vision pour cette pièce fonctionnent (testez avec le bouton "Vision" dans l'onglet Parts).

2.  **Filtre de Nom** :
    *   Le script ne calibre que les feeders contenant le mot `"Photon"` dans leur nom.
    *   Vous pouvez changer la variable `FEEDER_NAME_FILTER` au début du script si vos feeders s'appellent autrement.

## Utilisation

1.  Démarrez OpenPnP et activez la machine (Power On).
2.  Dans le menu principal, allez dans `Scripts`.
    *   (Si nécessaire, faites `Scripts` -> `Refresh Scripts`).
3.  Cliquez sur `recalibrate_feeders` pour lancer le processus.
4.  Surveillez la console (Log) d'OpenPnP pour voir la progression.

## Fonctionnement

Le script va :
1.  Lister tous les feeders dont le nom contient "Photon".
2.  Pour chaque feeder :
    *   Déplacer la caméra à la position enregistrée.
    *   Utiliser la fonction `machine.getVision().locate()` avec la pièce "Fiducial-1mm".
    *   Si le fiducial est trouvé, mettre à jour les coordonnées X et Y du feeder avec la nouvelle position précise.
    *   Le Z est conservé tel quel.
