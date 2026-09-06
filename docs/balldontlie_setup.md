# Notes — balldontlie.io

Remplace `nba_api` comme source de données live (voir
[`nba_api_notes.md`](nba_api_notes.md) pour le pourquoi).

## Obtenir une clé API

1. Créer un compte gratuit sur https://app.balldontlie.io/signup
2. Récupérer la clé API depuis le dashboard
3. La mettre dans `.env` :
   ```
   BALLDONTLIE_API_KEY=<ta clé>
   ```

Offre gratuite : 1 sport (NBA), **5 requêtes/minute**, données en direct
incluses (`Game data is realtime for in-progress games`). Largement
suffisant pour notre cadence de polling (un cycle toutes les quelques
minutes, pas plusieurs requêtes par minute).

## Endpoint utilisé

`GET https://api.balldontlie.io/v1/games?dates[]=YYYY-MM-DD`, header
`Authorization: <clé>` (pas de préfixe `Bearer`).

## Forme du payload

```json
{
  "data": [
    {
      "id": 15900602,
      "date": "2026-01-15",
      "status": "3rd Qtr",
      "status_state": "in_progress",
      "period": 3,
      "time": "5:23",
      "home_team_score": 88,
      "visitor_team_score": 91,
      "home_team": { "abbreviation": "LAL", "...": "..." },
      "visitor_team": { "abbreviation": "MIA", "...": "..." }
    }
  ],
  "meta": { "next_cursor": null, "per_page": 25 }
}
```

`status_state` — string stable, mappée directement sur `GameStatus` (voir
[scoreboard.py](../src/agent_ia_veille_nba/nba_data/scoreboard.py)) :

| Valeur         | `GameStatus` |
|----------------|--------------|
| `scheduled`    | `SCHEDULED`  |
| `in_progress`  | `LIVE`       |
| `final`        | `FINAL`      |

Les autres valeurs possibles (`postponed`, `canceled`, `delayed`,
`suspended`, `abandoned`, `unknown`) sont ignorées dans
`parse_scoreboard` — rien à suivre pour ces matchs pour l'instant.

## Ce qui n'a pas changé

`fetch_scoreboard()` / `parse_scoreboard()` gardent la même signature
publique qu'avant (à un détail près : `fetch_scoreboard` prend maintenant
un `game_date` optionnel, puisque balldontlie n'a pas de notion
implicite de "aujourd'hui" comme le faisait l'endpoint live de nba_api).
Le reste du pipeline (`agents/`, `db/`, `notifications/`) n'a pas eu à
changer — c'est exactement ce que la séparation fetch/parse est censée
permettre.
