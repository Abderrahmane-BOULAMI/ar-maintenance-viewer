# Guide utilisateur : maintenance 3D et réalité augmentée

## Ouvrir l'outil

Ouvrir l'adresse communiquée par le responsable (navigateur Chrome, Edge ou navigateur du casque). Le nuage de points de
la cellule s'affiche en quelques secondes.

## Se déplacer dans la vue

| Action | Souris | Écran tactile |
|---|---|---|
| Tourner autour | clic gauche maintenu | un doigt |
| Se déplacer | clic droit maintenu | deux doigts |
| Zoomer | molette | pincer |

## Trouver un équipement

- Taper un repère (R1, HPU) ou un mot du nom (« centrale ») dans la barre de recherche, puis Entrée.
- Ou cliquer sur la boîte colorée de l'équipement.

La couleur résume l'état :

- **vert** : rien à signaler ;
- **orange** : un ordre de travail est ouvert, ou la disponibilité est sous 99,8 % ;
- **rouge** : pannes répétitives, 20 ou plus sur les 12 derniers mois.

La fiche affiche les pannes, le MTBF, le MTTR, la disponibilité, les OT ouverts, la prochaine préventive, les modes de
défaillance principaux, les dernières interventions et les énergies à consigner.

## Suivre une procédure

1. Dans la fiche de l'équipement, cliquer sur **Démarrer** à côté de la procédure.
2. La vue se place sur l'équipement concerné par chaque étape. Les étapes de **consignation** sont signalées en rouge.
3. Cliquer sur **Étape suivante** une fois l'étape faite. Le temps passé par étape est enregistré.
4. **Quitter** interrompt la procédure (l'interruption est notée dans le journal).

## Mesurer une distance

Cliquer sur **Mesurer**, puis sur deux points du nuage. La distance s'affiche en mètres. Précision : celle du scan,
quelques millimètres sur un scan laser réel, dégradée par la réduction du nuage (taille de voxel indiquée dans
`results/build_report.json`).

## Casque RV ou RA

Si le terminal le permet, les boutons **ENTER VR** ou **START AR** apparaissent en haut à droite.

- En RV : la cellule est à l'échelle 1, devant vous.
- En RA : la cellule apparaît en maquette au 1:10 à hauteur de table, pour les revues en réunion.

## Journal de session

Le bouton **Journal** télécharge un fichier `session_log.json` (équipements ouverts, étapes et durées, mesures). Il ne
contient aucun nom : le transmettre au responsable de l'expérimentation à la fin de chaque essai.
