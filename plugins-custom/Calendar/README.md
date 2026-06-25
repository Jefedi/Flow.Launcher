# Calendar — plugin Flow Launcher

Un aperçu rapide de ton agenda, sans quitter Flow. Ne rate plus une visio : le prochain
rendez-vous est à un Entrée.

- ActionKeyword : `cal` (modifiable dans les réglages)
- `cal` → tes prochains événements (chronologique, « en cours » / « dans X min » mis en avant)
- `cal <texte>` → filtre par titre ou lieu
- **Entrée** → **rejoint la visio** si un lien (Meet/Zoom/Teams…) est détecté, sinon copie les détails
- **Maj+Entrée** (menu) → Rejoindre la visio · Copier les détails · Ouvrir le lieu

> Plugin isolé dans `plugins-custom/Calendar/` — **aucune modif du core C#**.

## Configuration : URL ICS (pas d'OAuth)
Le plugin lit une **URL ICS** (abonnement iCal) — aucune connexion Google/Microsoft requise.

- **Google Agenda** : Paramètres → *(ton agenda)* → « Intégrer l'agenda » →
  **Adresse secrète au format iCal**.
- **Outlook / Microsoft 365** : Paramètres → Calendrier → Calendriers partagés →
  Publier un calendrier → format **ICS**.

Colle l'URL dans `Settings → Plugins → Calendar → URL(s) ICS`. Plusieurs agendas ?
Sépare les URLs par une virgule. Règle l'horizon (jours) si besoin.

> Les récurrences (réunions hebdo, etc.) sont **développées** correctement. Les taux…
> pardon, les événements sont mis en cache 5 min pour ne pas re-télécharger à chaque touche.

## Déploiement pour test (Windows)

```powershell
cd plugins-custom\Calendar
pip install -r requirements.txt -t .\lib
Copy-Item -Recurse -Force . "$env:APPDATA\FlowLauncher\Plugins\Calendar"
```

Puis **redémarre Flow Launcher** (nouveau plugin → redémarrage requis). Configure l'URL
ICS, puis tape `cal`.

## Dépendances
- `flowlauncher` (RPC)
- `recurring-ical-events` (+ `icalendar`, `python-dateutil`, `tzdata`) — parsing ICS et
  développement des récurrences. Installées dans `lib/`.
