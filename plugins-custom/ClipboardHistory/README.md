# Clipboard History — plugin Flow Launcher

Fini le ping-pong du presse-papiers : parcours ton **historique presse-papiers Windows**
depuis Flow, retrouve ce que tu as copié, et remets-le d'un Entrée.

- ActionKeyword : `clip` (modifiable dans les réglages)
- `clip` → liste les entrées récentes (les plus récentes en haut)
- `clip <texte>` → filtre l'historique
- **Entrée** → remet l'entrée dans le presse-papiers (prête à coller avec Ctrl+V)
- **Maj+Entrée** (menu) → Copier · Supprimer cette entrée · Vider tout l'historique

> Plugin isolé dans `plugins-custom/ClipboardHistory/` — **aucune modif du core C#**.

## Important : activer l'historique Windows
Ce plugin lit l'historique **natif** de Windows (celui de `Win+V`). Il doit être activé :

**Paramètres → Système → Presse-papiers → Historique du Presse-papiers** (ON)
ou appuie sur **Win+V** une fois et active-le.

Si désactivé, le plugin te l'indique au lieu de planter. Rien n'est stocké ni journalisé
par le plugin : l'historique est celui de l'OS, lu en direct (pas de démon en arrière-plan).

## Déploiement pour test (Windows)

```powershell
cd plugins-custom\ClipboardHistory
pip install -r requirements.txt -t .\lib
Copy-Item -Recurse -Force . "$env:APPDATA\FlowLauncher\Plugins\ClipboardHistory"
```

Puis **redémarre Flow Launcher** (nouveau plugin → redémarrage requis, pas juste Reload).
Essaie : `clip`, puis `clip <mot>`.

## Dépendances
- `flowlauncher` (RPC)
- `winsdk` (bindings WinRT pour lire l'historique du presse-papiers) — installé dans `lib/`.
