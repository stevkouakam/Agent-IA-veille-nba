# Notes — endpoint scoreboard de nba_api

## Endpoint utilisé

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

## ⚠️ Blocage réseau observé (Akamai 403)

Tenter `fetch_scoreboard()` (ou un `requests.get()` direct sur
`cdn.nba.com`) depuis l'environnement d'exécution de Claude Code a renvoyé
un `403 Access Denied` de l'edge Akamai de nba.com — pas une erreur
nba_api, un rejet réseau au niveau CDN. C'est un problème documenté dans la
communauté nba_api : Akamai bloque fréquemment les IP de datacenter/cloud
(AWS, GCP, Azure), probablement y compris certains runners GitHub Actions.

**À vérifier :**
- [ ] Confirmer que `fetch_scoreboard()` fonctionne depuis ton terminal
      PowerShell habituel (IP résidentielle) — probable que oui.
- [ ] Garder ce point en tête pour l'étape 7 (scheduling GitHub Actions) :
      si les runners hébergés se font aussi bloquer, il faudra un runner
      self-hosted ou un proxy.

## Prochaine étape suggérée

Étape 3 du plan de match : modéliser la table des matchs suivis avec
SQLAlchemy + Alembic, en s'appuyant sur les champs de `GameUpdate` comme
première ébauche de schéma.
