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

## Jobs Fab (envoi depuis KiCad)

Le bouton **Fab** de [kicad_library_manager](https://github.com/clecle253/kicad_library_manager) dépose un fichier
`<carte>_<date>.fabjob.json` dans un dossier partagé. Dans l'onglet KiCad du plugin :

1. Choisir ce dossier dans « Jobs Fab » (il est mémorisé). Le plugin le surveille et annonce dans le log
   chaque nouveau job.
2. « Charger le dernier job » remplit le tableau de validation. Seules les pièces marquées `machine`
   (face dessus, données PnP vérifiées, hauteur connue) ont l'action `Import` ; les autres sont listées
   « à la main » et ignorées. Les fiducials du job sont listés dans le log mais **pas** créés automatiquement.
3. « Generate Board » crée le board, les Packages (nom d'empreinte du job) et les Parts (avec leur hauteur),
   puis range le job dans `processed/` (ou `failed/` s'il est illisible).

Un job est refusé en entier (et rangé dans `failed/`) s'il contient deux fois la même référence ou s'il est illisible. Le plugin revérifie lui-même que chaque pièce `machine` est complète (vérifiée, hauteur, bande, buse, face dessus) et rétrograde en « à la main » sinon, même si le fichier a été modifié à la main. Quand un job est chargé, le tableau est en lecture seule : l'import vient du job, pas des cellules.

Le format du job est décrit dans `docs/fab_job_format.md` du dépôt kicad_library_manager. La lecture est
dans `LumenPnP/core/fab_job.py` (Python pur, compatible Jython 2.7, testé avec `python -m pytest`).
