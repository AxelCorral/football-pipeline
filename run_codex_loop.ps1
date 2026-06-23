$ErrorActionPreference = "Continue"

Set-Location "D:\Project_claude_code\football-pipeline"

$cyclePrompt = @"
Continue la boucle autonome définie dans CODEX_AUTONOMOUS_LOOP.md.

Exécute exactement UN cycle complet maintenant :
1. Choisis la prochaine amélioration utile dans ton périmètre Codex : tests, bugs locaux, qualité, lint, robustesse ciblée.
2. Modifie le minimum de fichiers nécessaire.
3. Lance les tests ou checks pertinents.
4. Corrige si nécessaire.
5. Mets à jour la documentation uniquement si nécessaire.
6. Fais un commit Git propre.
7. Donne le résumé du cycle.

Après ce cycle, ne demande pas de validation humaine sauf blocage critique.
Ne touche pas aux secrets, .env, credentials, AWS réel, facturation, crédits, auto-reload ou pay-as-you-go.
"@

while ($true) {
    Write-Host ""
    Write-Host "==============================="
    Write-Host "Nouveau cycle Codex"
    Write-Host "==============================="
    Write-Host ""

    & "C:\Users\AxelC\AppData\Roaming\npm\codex.cmd" exec --dangerously-bypass-approvals-and-sandbox $cyclePrompt

    Write-Host ""
    Write-Host "Cycle Codex terminé. Redémarrage dans 10 secondes..."
    Start-Sleep -Seconds 10
}