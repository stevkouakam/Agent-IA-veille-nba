# Notes — configuration du bot Telegram

## Pourquoi un bot, pas un compte perso

Un bot Telegram est une entité séparée du compte personnel, pilotable par
API via un token. Deux identifiants suffisent pour lui faire envoyer un
message : le **token** (authentifie le bot) et le **chat_id** (à qui
envoyer). Un bot ne peut pas initier une conversation — l'utilisateur doit
lui parler en premier, ce qui conditionne l'ordre des étapes ci-dessous.

## Étapes

1. **Créer le bot** — dans Telegram, ouvrir une conversation avec
   `@BotFather` (compte officiel), envoyer `/newbot`, choisir un nom
   d'affichage puis un username se terminant par `bot`. BotFather répond
   avec le **token**.
2. **Démarrer la conversation** — chercher ce username dans Telegram et
   cliquer *Démarrer* (ou envoyer n'importe quel message). Sans ça,
   `getUpdates` (étape 3) ne renverra rien.
3. **Récupérer le chat_id** — mettre `TELEGRAM_BOT_TOKEN` dans `.env`,
   puis lancer :
   ```powershell
   uv run python scripts/get_telegram_chat_id.py
   ```
   qui interroge `getUpdates` et affiche le(s) `chat_id` trouvé(s).
4. Copier ce chat_id dans `TELEGRAM_CHAT_ID` dans `.env`.

## Sécurité

Le token équivaut à un mot de passe pour le bot (accès complet en son
nom) — jamais commité, `.env` est gitignored. En cas de fuite, révoquer
via `@BotFather` → `/revoke`.
