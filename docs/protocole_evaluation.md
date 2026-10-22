# Protocole d'évaluation sur site

But : mesurer la valeur ajoutée de l'outil pour les équipes maintenance, avec des chiffres comparables, avant de
décider d'une généralisation.

## Indicateurs

| Indicateur | Mesure | Source |
|---|---|---|
| Temps pour localiser un équipement et son historique | Secondes, du début de la demande à la lecture du dernier OT | Chronométrage |
| Temps de réalisation d'une procédure | Minutes, première à dernière étape | Journal de session (outil) ou chronométrage (papier) |
| Erreurs ou oublis | Étape oubliée, mauvais repère, consignation incomplète | Observation par un pair |
| Utilisabilité | Score SUS de 0 à 100 | Questionnaire en fin d'essai |
| Adoption | Sessions par technicien et par semaine pendant l'essai | Journaux de session |

## Plan d'essai

- Deux méthodes : **papier** (dossier, écrans GMAO actuels) et **3D** (cet outil).
- Au moins 8 participants par méthode, en croisant si possible (chaque technicien fait une tâche avec chaque méthode,
  dans un ordre tiré au sort, pour limiter l'effet d'apprentissage).
- Mêmes tâches, mêmes équipements, mêmes conditions de sécurité.

## Analyse

```python
import pandas as pd
from armaint.evaluation import compare, report
timings = pd.read_csv("mesures.csv")    # participant, method, task, seconds, errors
sus = pd.read_csv("sus.csv")             # participant, q1 ... q10
print(report(timings, sus))
```

Le test de Mann-Whitney indique si l'écart de temps peut s'expliquer par le hasard (p supérieur à 0,05 : pas de
conclusion possible avec cet échantillon). Le fichier `evaluation/exemple_mesures.csv` contient des données
**fictives**, uniquement pour tester le script.

## Biais à surveiller

- Effet nouveauté : comparer les semaines 1 et 3.
- Volontaires plus à l'aise avec le numérique : noter l'ancienneté et l'usage habituel de la tablette.
- Données périmées : une seule extraction GMAO pendant l'essai, datée.
