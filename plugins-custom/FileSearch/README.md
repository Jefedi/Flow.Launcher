# File Search — plugin Flow Launcher

Recherche de fichiers **instantanée** sur tout ton système, à la
[Everything](https://www.voidtools.com/). Le plugin interroge l'index Everything via son
outil officiel `es.exe` — donc la même vitesse (millisecondes) sur des millions de fichiers.

- **Global, sans mot-clé** (ActionKeyword `*`) : tape directement ton terme dans Flow,
  les fichiers correspondants apparaissent (façon Everything). Configurable dans les réglages.
- `<terme>` → fichiers/dossiers correspondants, instantanément (à partir de 3 caractères)
- **Entrée** → ouvre le fichier (app par défaut) ou le dossier
- **Maj+Entrée** (menu) → Ouvrir · Ouvrir le dossier contenant · Ouvrir avec… · Ouvrir un
  terminal ici · Exécuter en administrateur (exécutables) · Copier le chemin · Copier le
  dossier parent · Copier le nom · Copier le nom sans extension
- Syntaxe **Everything** supportée : `*.pdf`, `ext:docx`, `rapport`, `C:\Users\ facture`, etc.

> Plugin isolé dans `plugins-custom/FileSearch/` — **aucune modif du core C#**.

## Prérequis
1. **Everything** (voidtools) installé **et lancé** : https://www.voidtools.com/
   (l'icône doit être dans la zone de notification ; le service maintient l'index).
2. **es.exe** (l'outil ligne de commande d'Everything) dans `tools\es.exe`.
   - Télécharge-le ici : https://www.voidtools.com/downloads/ (section *Command-line Interface*),
     dézippe, et place `es.exe` dans le dossier `tools\` du plugin.
   - Ou indique son chemin dans `Settings → Plugins → File Search → Chemin de es.exe`.
   - Le plugin auto-détecte aussi `es.exe` s'il est dans le PATH ou dans `C:\Program Files\Everything\`.

> `es.exe` n'est **pas** versionné dans le repo (binaire tiers, voir `.gitignore`).

## Déploiement pour test (Windows)

```powershell
cd plugins-custom\FileSearch
pip install -r requirements.txt -t .\lib
# place es.exe dans .\tools\ (voir ci-dessus)
Copy-Item -Recurse -Force . "$env:APPDATA\FlowLauncher\Plugins\FileSearch"
```

Puis **redémarre Flow Launcher** (nouveau plugin → redémarrage requis). Essaie :
`f *.pdf`, `f rapport`, `f ext:xlsx`.

## Réglages
- **Chemin de es.exe** — vide = auto-détection
- **Nombre de résultats** — défaut 30
