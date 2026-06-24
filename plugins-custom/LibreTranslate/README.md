# LibreTranslate — plugin Flow Launcher

Traduit du texte à la volée via **ton instance LibreTranslate self-hosted**, directement
depuis la barre de Flow Launcher.

- ActionKeyword : `tr` (modifiable dans les réglages du plugin)
- `tr <texte>` → traduit `<texte>` vers la langue cible
- **Title** = la traduction · **SubTitle** = langue détectée → langue cible
- **Entrée** = copie la traduction dans le presse-papier
- **Menu contextuel** (Shift+Entrée) = copie le texte original

> Ce plugin est isolé dans `plugins-custom/LibreTranslate/` pour ne **pas** toucher au
> core C# de Flow Launcher et garder le fork mergeable avec l'upstream.

---

## Prérequis

1. **Flow Launcher** installé (Windows).
2. **Python configuré dans Flow Launcher** :
   `Settings → General → Python` doit pointer vers un `python.exe` (Python 3.x).
   Sans ça, Flow ne peut pas lancer les plugins Python.
3. Une **instance LibreTranslate** accessible (par défaut `https://translate.jefe.al`).

---

## Déploiement pour test (Windows)

Les plugins manuellement copiés ne passent **pas** par l'installeur de Flow, donc la
dépendance Python (`flowlauncher`) doit être installée à la main dans un dossier `lib/`
à côté de `main.py`.

### 1. Installer la dépendance dans `./lib`

Depuis le dossier du plugin :

```powershell
cd plugins-custom\LibreTranslate
pip install -r requirements.txt -t .\lib
```

> Les appels HTTP utilisent la lib standard (`urllib`), donc **aucune** dépendance
> `requests`/`httpx` n'est nécessaire — seul `flowlauncher` est requis.

### 2. Copier le dossier dans Flow Launcher

Copie **tout le dossier `LibreTranslate`** (avec `lib/` dedans) dans :

```
%APPDATA%\FlowLauncher\Plugins\
```

En PowerShell :

```powershell
Copy-Item -Recurse -Force .\plugins-custom\LibreTranslate "$env:APPDATA\FlowLauncher\Plugins\LibreTranslate"
```

Tu dois obtenir :

```
%APPDATA%\FlowLauncher\Plugins\LibreTranslate\
├── main.py
├── libretranslate.py
├── plugin.json
├── SettingsTemplate.yaml
├── requirements.txt
├── Images\icon.png
└── lib\            (flowlauncher installé ici)
```

### 3. Recharger les plugins

Dans Flow Launcher, tape :

```
Reload Plugin Data
```

(ou redémarre Flow Launcher). Le plugin **LibreTranslate** apparaît alors dans
`Settings → Plugins`.

### 4. Configurer (optionnel)

`Settings → Plugins → LibreTranslate` :

- **Instance URL** — défaut `https://translate.jefe.al` (le `/` final est ignoré)
- **Target language** — `fr`, `en`, `es`, `de`, `it`, `pt` (défaut `fr`)
- **API key** — laisse vide si ton instance n'en demande pas

### 5. Utiliser

```
tr hello world
```

→ affiche la traduction. Entrée pour copier. Shift+Entrée pour le menu contextuel
(copier le texte original).

---

## Dépannage

- **Rien ne s'affiche / le plugin ne charge pas** → vérifie que Python est bien configuré
  dans Flow (`Settings → General → Python`) et que `lib\flowlauncher` existe.
- **« Erreur de traduction »** → le SubTitle donne le détail (réseau, timeout 5s, HTTP, etc.).
  Vérifie l'URL de l'instance et son accessibilité.
- Après chaque modif de fichier : relance **Reload Plugin Data**.

---

## Contrat API utilisé

`POST {instance_url}/translate` · `Content-Type: application/json`

```json
{ "q": "<texte>", "source": "auto", "target": "<target_lang>",
  "format": "text", "api_key": "<seulement si renseigné>" }
```

Réponse attendue :

```json
{ "translatedText": "...", "detectedLanguage": { "language": "..", "confidence": 0.9 } }
```
