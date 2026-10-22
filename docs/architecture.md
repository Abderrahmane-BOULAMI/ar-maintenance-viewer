# Architecture et prérequis techniques

```
Scan laser (E57/LAS/PLY) ──► armaint/scene.py ──► réduction par voxels ──► web/data/cell.ply
Export GMAO (CSV)        ──► armaint/cmms.py  ──► MTBF, MTTR, disponibilité, OT ouverts ─┐
Procédures (YAML)        ──► armaint/procedures.py ──► contrôle avant publication ───────┼─► web/data/scene.json
                                                                                          │
web/index.html + app.js (three.js, WebXR) ◄───────────────────────────────────────────────┘
        │
        └─► journal de session (JSON) ──► armaint/evaluation.py ──► rapport d'évaluation
```

## Prérequis

| Élément | Choix du démonstrateur | Alternative industrielle |
|---|---|---|
| Rendu 3D | three.js 0.160 (MIT), fourni dans `web/vendor` | Unity ou Unreal avec un plugin nuage de points |
| RV / RA | WebXR dans le navigateur, sans installation | Application native du fabricant du casque |
| Hébergement | Fichiers statiques (aucun serveur applicatif) | Serveur web interne, accès par le réseau usine |
| Données | Fichiers générés hors ligne | Extraction GMAO planifiée, API du logiciel de scan |
| Licences | Aucune (code MIT, three.js MIT) | Licences casque et logiciel de scan à prévoir |

## Matériel testé

- Navigateur Chromium (bureau) : vue 3D, recherche, procédure, mesure, journal ; test automatique
  `tests/e2e_viewer.py`.
- Les modes RV et RA n'ont pas été testés sur casque dans ce dépôt : les boutons n'apparaissent que si le navigateur
  annonce la prise en charge de WebXR.

## Sécurité et données

- Aucune donnée personnelle dans les journaux (pas de nom, pas d'identifiant de poste).
- Les indicateurs sont en lecture seule : l'outil n'écrit jamais dans la GMAO.
