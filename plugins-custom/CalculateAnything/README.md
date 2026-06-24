# Calculate Anything — plugin Flow Launcher

Un calculateur façon **Raycast** : tape une expression en langage proche du naturel,
obtiens le résultat, copie-le d'un Entrée. **v1 = maths & expressions** (les devises,
unités, dates/fuseaux viendront ensuite).

- ActionKeyword : `=` (modifiable dans les réglages)
- `= <expression>` → calcule et affiche le résultat
- **Entrée** = copie le résultat dans le presse-papier
- **Menu contextuel** (Maj+Entrée) : copier le résultat, ou « expression = résultat »

> Plugin isolé dans `plugins-custom/CalculateAnything/` — **aucune modif du core C#**.

## Ce qu'il comprend

| Catégorie | Exemples |
|---|---|
| Arithmétique | `2+2`, `(2+3)*4`, `10/3`, `-5 + 3` |
| Puissances | `2^10`, `2**8`, `3 squared`, `2 cubed`, `2 to the power of 8` |
| Langage naturel | `2 plus 2`, `10 times 5`, `100 divided by 4`, `5 x 3` |
| Pourcentages | `15% of 80`, `80 + 15%`, `200 - 10%`, `50%` |
| Fonctions | `sqrt(2)`, `abs(-5)`, `log(100)`, `ln(e)`, `log2(8)`, `min(1,2,3)`, `gcd(12,18)` |
| Trigonométrie | `sin(90)`, `cos(0)` (unité d'angle configurable : radians/degrés) |
| Constantes | `pi`, `e`, `tau` |
| Factorielle / modulo | `5!`, `10 mod 3`, `10 % 3` |
| Bases | `0xFF`, `0b1010` |

## Réglages (Flow → Settings → Plugins → Calculate Anything)
- **Angle unit** — `radians` (défaut) ou `degrees` pour `sin/cos/tan`
- **Thousands separator** — grouper les grands résultats (`1,234,567`)

## Sécurité
Le moteur **n'utilise pas `eval`**. Il analyse l'expression avec le module `ast` et
n'autorise qu'une liste blanche d'opérateurs, fonctions et constantes. Les imports,
appels arbitraires, accès attributs, exposants/factorielles démesurés sont refusés.

## Déploiement pour test (Windows)

```powershell
cd plugins-custom\CalculateAnything
pip install -r requirements.txt -t .\lib
Copy-Item -Recurse -Force . "$env:APPDATA\FlowLauncher\Plugins\CalculateAnything"
```

Puis dans Flow : **`Reload Plugin Data`** (ou redémarre Flow). Teste : `= 15% of 80`.

> Le moteur de calcul n'a **aucune** dépendance tierce (stdlib only) ; seule la lib
> `flowlauncher` (RPC) est requise, d'où le `pip install -t .\lib`.
