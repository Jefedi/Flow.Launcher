# Calculate Anything — plugin Flow Launcher

Un calculateur façon **Raycast** : tape une expression en langage proche du naturel,
obtiens le résultat, copie-le d'un Entrée. Gère **maths, devises, crypto, dates et
fuseaux horaires**.

- ActionKeyword : `=` (modifiable dans les réglages)
- `= <expression>` → détecte le type (devise → date → math) et affiche le résultat
- **Entrée** = copie le résultat dans le presse-papier
- **Menu contextuel** (Maj+Entrée) : actions de copie selon le type (montant, taux, libellé…)

> Plugin isolé dans `plugins-custom/CalculateAnything/` — **aucune modif du core C#**.

## Ce qu'il comprend

### Maths & expressions
| Catégorie | Exemples |
|---|---|
| Arithmétique | `2+2`, `(2+3)*4`, `10/3`, `-5 + 3` |
| Puissances | `2^10`, `2**8`, `3 squared`, `2 cubed`, `2 to the power of 8` |
| Langage naturel | `2 plus 2`, `10 times 5`, `100 divided by 4`, `5 x 3` |
| Pourcentages | `15% of 80`, `80 + 15%`, `200 - 10%`, `50%` |
| Fonctions | `sqrt(2)`, `abs(-5)`, `log(100)`, `ln(e)`, `log2(8)`, `min(1,2,3)`, `gcd(12,18)` |
| Trigonométrie | `sin(90)`, `cos(0)` (unité d'angle configurable : radians/degrés) |
| Constantes / autres | `pi`, `e`, `tau`, `5!`, `10 mod 3`, `0xFF`, `0b1010` |

### Devises & crypto
| Exemple | Effet |
|---|---|
| `10 usd in eur` | conversion fiat → fiat |
| `0.5 btc in usd` | crypto → fiat |
| `2 eth in btc` | crypto → crypto |
| `$100 in eur` | symbole monétaire accepté (`$ € £ ¥ ₿`) |
| `100 usd` | converti vers ta **devise par défaut** (réglage) |

Taux en direct via **Frankfurter** (BCE, fiat) et **CoinGecko** (crypto) — APIs gratuites
**sans clé**. Les taux sont mis en cache sur disque (fiat 1 h, crypto 5 min) pour rester
rapides et ménager les APIs. ~30 devises fiat et ~30 cryptos majeures.

### Dates & fuseaux horaires
| Exemple | Effet |
|---|---|
| `now`, `today` | date et heure locales |
| `now in tokyo`, `london time` | heure dans un fuseau (villes, IANA, `utc+2`) |
| `in 3 weeks`, `3 days from now`, `2 months ago` | date relative |
| `days until 2026-12-25`, `days since 2020-01-01` | nombre de jours |
| `days between 2026-01-01 and 2026-12-31` | écart entre deux dates |
| `2026-12-25 + 10 days` | arithmétique sur une date |

Mots-clés en **français et anglais** (`dans 2 mois`, `il y a 1 an`, `demain`…).

## Réglages (Flow → Settings → Plugins → Calculate Anything)
- **Angle unit** — `radians` (défaut) ou `degrees` pour `sin/cos/tan`
- **Thousands separator** — grouper les grands résultats math (`1,234,567`)
- **Default currency** — devise cible quand elle n'est pas précisée (défaut `EUR`)

## Sécurité & confidentialité
- Le moteur math **n'utilise pas `eval`** : analyse `ast` + liste blanche stricte
  (imports, appels arbitraires, accès attributs, exposants/factorielles démesurés refusés).
- Les conversions de devises envoient **uniquement les codes et le montant** (jamais ton
  texte) à Frankfurter/CoinGecko. Les dates/fuseaux sont calculés **hors-ligne**.

## Déploiement pour test (Windows)

```powershell
cd plugins-custom\CalculateAnything
pip install -r requirements.txt -t .\lib
Copy-Item -Recurse -Force . "$env:APPDATA\FlowLauncher\Plugins\CalculateAnything"
```

Puis dans Flow : **`Reload Plugin Data`** (ou redémarre Flow). Teste : `= 15% of 80`.

> Le moteur de calcul n'a **aucune** dépendance tierce (stdlib only) ; seule la lib
> `flowlauncher` (RPC) est requise, d'où le `pip install -t .\lib`.
