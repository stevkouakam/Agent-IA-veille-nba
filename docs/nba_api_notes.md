# Notes — endpoint scoreboard de nba_api (historique)

> **Superseded.** Ce document garde la trace de l'investigation initiale
> et du choix technique qui en a découlé. Le blocage réseau décrit plus
> bas s'est avéré permanent et plus large que prévu (voir la dernière
> section) — le projet utilise désormais `balldontlie.io`, documenté dans
> [`balldontlie_setup.md`](balldontlie_setup.md). Les sections ci-dessous
> ne reflètent plus le code actuel de `nba_data/scoreboard.py`.

## Endpoint utilisé (abandonné)

`nba_api.live.nba.endpoints.scoreboard.ScoreBoard` — wrapper autour de
`https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json`.

Retourne l'état de tous les matchs du jour (scores, période, chrono). C'est
l'endpoint "live", distinct de `nba_api.stats.endpoints` qui sert des
statistiques historiques (`stats.nba.com`) — on utilisera ce dernier plus
tard si besoin de données saison/carrière, mais pour la veille en direct
c'est `live` qu'il nous faut.

## Forme du payload

```json
{
  "meta": { "version": 3, "time": "...", "code": 200 },
  "scoreboard": {
    "gameDate": "2026-01-15",
    "games": [
      {
        "gameId": "0022500601",
        "gameStatus": 1,
        "gameStatusText": "7:30 pm ET",
        "period": 0,
        "gameClock": "",
        "homeTeam": {
          "teamTricode": "NYK",
          "score": 0,
          "wins": 24,
          "losses": 16
        },
        "awayTeam": { "teamTricode": "BOS", "score": 0, ... }
      }
    ]
  }
}
```

`gameStatus` — code numérique stable, mappé dans `GameStatus` (voir
[scoreboard.py](../src/agent_ia_veille_nba/nba_data/scoreboard.py)) :

| Valeur | Signification            |
|--------|---------------------------|
| 1      | Match pas encore commencé |
| 2      | Match en cours            |
| 3      | Match terminé              |

`gameClock` est au format ISO 8601 duration (`PT05M23.00S`) quand le match
est en cours, vide sinon.

## Fetch vs parse

Le module [`nba_data/scoreboard.py`](../src/agent_ia_veille_nba/nba_data/scoreboard.py)
sépare volontairement :
- `fetch_scoreboard()` — appelle le réseau, retourne le JSON brut. Effet de
  bord, pas testé unitairement.
- `parse_scoreboard(raw)` — fonction pure, JSON brut → liste de
  `GameUpdate`. Testée dans
  [`tests/nba_data/test_scoreboard.py`](../tests/nba_data/test_scoreboard.py)
  contre une fixture figée (`tests/fixtures/scoreboard_sample.json`), sans
  appel réseau.

Cette séparation garde les tests rapides et déterministes, et permettra
plus tard de brancher `parse_scoreboard` sur le state graph LangGraph sans
que l'agent ne connaisse les détails HTTP.

## ⚠️ Blocage réseau — confirmé permanent et généralisé (étape 7)

Tenter `fetch_scoreboard()` (ou un `requests.get()` direct sur
`cdn.nba.com`) a systématiquement renvoyé un `403 Access Denied` de
l'edge Akamai de nba.com — pas une erreur nba_api, un rejet réseau au
niveau CDN. À l'étape 7, ce point a été vérifié dans les trois
environnements possibles :

| Environnement | Résultat |
|---|---|
| Sandbox de développement (Claude Code) | `403` |
| Conteneur Docker (même machine) | `403` (même trace, via `nba_api`) |
| Runner GitHub Actions hébergé | `403` (voir `.github/workflows/network-check.yml`) |
| **Terminal PowerShell perso, réseau résidentiel** | **`403` aussi** |

Le dernier résultat a tranché : ce n'est pas un blocage d'IP de
datacenter/cloud (l'hypothèse initiale, documentée dans la communauté
nba_api pour AWS/GCP/Azure) — c'est plus large, probablement géographique
ou lié à une politique anti-bot d'Akamai qui dépasse le cadre de ce
projet. `stats.nba.com` (l'autre domaine de nba_api) ne renvoie même pas
de 403 propre : la connexion TLS s'établit puis reste bloquée jusqu'au
timeout, signe d'un filtrage similaire.

**Décision :** migration vers `balldontlie.io`, qui n'est pas affecté et
dont l'offre gratuite couvre le score en direct. Voir
[`balldontlie_setup.md`](balldontlie_setup.md).
