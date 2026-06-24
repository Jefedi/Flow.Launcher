# Notes — plugin Flow Launcher

Capture rapide d'une pensée, façon **Raycast Notes** : note un truc sans quitter ce que
tu fais, retrouve-le, copie-le.

- ActionKeyword : `note` (modifiable dans les réglages)
- `note <texte>` → le 1er résultat **enregistre** la note (Entrée) ; en dessous, tes
  notes existantes qui correspondent (recherche en direct)
- `note` (vide) → liste toutes tes notes (épinglées en haut, puis les plus récentes)
- **Entrée** sur une note → copie son texte
- **Maj+Entrée** (menu contextuel) → Copier · Épingler/Désépingler · Supprimer

> Plugin isolé dans `plugins-custom/Notes/` — **aucune modif du core C#**.

## Stockage
Les notes sont enregistrées en local dans :

```
%APPDATA%\FlowLauncher\Notes\notes.json
```

Ce dossier est **hors** du dossier du plugin : tes notes survivent à un redéploiement
ou une mise à jour du plugin. Format JSON lisible (1 note = id, texte, date, épinglé).

## Déploiement pour test (Windows)

```powershell
cd plugins-custom\Notes
pip install -r requirements.txt -t .\lib
Copy-Item -Recurse -Force . "$env:APPDATA\FlowLauncher\Plugins\Notes"
```

Puis dans Flow : **`Reload Plugin Data`** (ou redémarre Flow). Essaie :

```
note acheter du lait
note            (liste)
note lait       (recherche)
```

> Aucune dépendance tierce hormis la lib `flowlauncher` (RPC) ; le stockage est en
> bibliothèque standard.
