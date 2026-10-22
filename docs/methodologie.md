# Méthodologie de déploiement RV/RA pour la maintenance

Ce document décrit comment passer d'un nuage de points d'atelier à un outil utilisé par les équipes maintenance, et
comment décider si l'usage mérite d'être généralisé. Le démonstrateur de ce dépôt applique chaque étape à une cellule
de soudure fictive.

## 1. Choisir les cas d'usage

Chaque cas d'usage proposé par les correspondants maintenance est noté de 1 à 5 sur cinq critères, puis classé.

| Critère | Question posée | Poids |
|---|---|---|
| Fréquence | Combien de fois par mois la situation se présente ? | 25 % |
| Coût d'une erreur ou d'un retard | Arrêt de ligne, sécurité, qualité ? | 25 % |
| Besoin de se repérer dans l'espace | La difficulté vient-elle de « où est-ce » plutôt que de « quoi faire » ? | 20 % |
| Données disponibles | Scan, GMAO, procédures existent-ils et sont-ils à jour ? | 20 % |
| Faisabilité sur site | Réseau, casque autorisé, mains libres nécessaires ? | 10 % |

Cas d'usage types retenus pour le démonstrateur :

1. **Localiser un équipement et son historique** avant une intervention (technicien d'astreinte qui connaît mal la zone).
2. **Dérouler une procédure pas à pas** avec consignation obligatoire (opération peu fréquente, risque d'oubli).
3. **Préparer un chantier à distance** : mesurer un passage, vérifier un encombrement sans se déplacer.
4. **Former un nouvel arrivant** à la cellule en réalité virtuelle avant sa première intervention.

## 2. Préparer les données

| Donnée | Source | Traitement dans le dépôt |
|---|---|---|
| Nuage de points | Scan laser de l'atelier (export E57, LAS ou PLY) | Réduction par voxels jusqu'au budget de points du terminal (`armaint/scene.py`) |
| Boîtes des équipements | Saisie une fois par repère, à partir du nuage | `EQUIPMENT` dans `armaint/scene.py` |
| Historique de maintenance | Export GMAO (OT, type, mode de défaillance, dates, statut) | Indicateurs MTBF, MTTR, disponibilité, OT ouverts (`armaint/cmms.py`) |
| Procédures | Bureau des méthodes maintenance | Fichier YAML vérifié avant publication (`armaint/procedures.py`) |

Règle de publication : une procédure n'est publiée que si chaque étape vise un repère connu, si toute étape qui
travaille sur une énergie est précédée de sa consignation, et si la durée annoncée correspond aux étapes.

## 3. Choisir le terminal

| Terminal | Usage conseillé | Budget de points indicatif |
|---|---|---|
| PC ou tablette (navigateur) | Préparation, consultation de l'historique, mesure | 250 000 à 1 000 000 |
| Casque RV autonome | Formation, visite virtuelle de la cellule | 300 000 à 500 000 |
| Casque ou smartphone RA | Maquette sur table au 1:10, revue de chantier en réunion | 100 000 à 300 000 |

Le budget se règle au moment de la construction : `python -m armaint.build --points 150000`.

## 4. Expérimenter sur site

1. Choisir deux équipes comparables, une avec l'outil et une avec la méthode actuelle.
2. Former l'équipe outil (support `formation.md`, 1 heure).
3. Mesurer selon `protocole_evaluation.md` pendant 2 à 4 semaines.
4. Recueillir les retours en fin d'essai (questionnaire SUS et entretien de 15 minutes).

## 5. Décider de la généralisation

Un cas d'usage est proposé à la généralisation si les trois conditions sont réunies :

- gain de temps médian d'au moins 20 % sur la tâche visée, ou baisse des erreurs ;
- score SUS d'au moins 68 (au-dessus de la moyenne observée sur les logiciels) ;
- coût de mise à jour des données soutenable : un responsable nommé pour le scan, la GMAO et les procédures.

Les résultats et recommandations sont consignés dans le rapport d'évaluation (`rapport_evaluation_modele.md`).
