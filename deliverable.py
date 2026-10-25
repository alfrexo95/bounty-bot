"""
Patch for alfrexo95/bounty-bot issue #37: "💰 Bounty Seguro (Ver enlace):" message handling

This patch implements a clean, modular solution for recognizing and processing
the "💰 Bounty Seguro (Ver enlace):" bounty message pattern in the bounty-bot.

Assumptions:
- The bot receives messages as strings.
- The bot should detect messages matching the bounty pattern and extract the link.
- The bot should provide a function to process such messages.

No external dependencies are used.
"""

import re
from typing import Optional, Dict

BOUNTY_PATTERN = r"💰 Bounty Seguro \(Ver enlace\):\s*(https?://[^\s]+)"

def extract_bounty_link(message: str) -> Optional[str]:
    """
    Extracts the bounty link from a message if it matches the bounty pattern.

    Args:
        message (str): The message to process.

    Returns:
        Optional[str]: The extracted link if found, else None.
    """
    match = re.search(BOUNTY_PATTERN, message)
    if match:
        return match.group(1)
    return None

def process_bounty_message(message: str) -> Optional[Dict[str, str]]:
    """
    Processes a message to extract bounty information.

    Args:
        message (str): The message to process.

    Returns:
        Optional[Dict[str, str]]: A dictionary with bounty info if found, else None.
    """
    link = extract_bounty_link(message)
    if link:
        return {
            "type": "bounty_seguro",
            "link": link
        }
    return None

# --- TESTS ---

def _test_extract_bounty_link() -> None:
    # Positive test
    msg = "💰 Bounty Seguro (Ver enlace): https://bounties.example.com/123"
    assert extract_bounty_link(msg) == "https://bounties.example.com/123"

    # Negative test
    msg2 = "No bounty here"
    assert extract_bounty_link(msg2) is None

    # Edge case: extra spaces
    msg3 = "💰 Bounty Seguro (Ver enlace):    https://bounties.example.com/456"
    assert extract_bounty_link(msg3) == "https://bounties.example.com/456"

def _test_process_bounty_message() -> None:
    msg = "💰 Bounty Seguro (Ver enlace): https://bounties.example.com/789"
    result = process_bounty_message(msg)
    assert result == {
        "type": "bounty_seguro",
        "link": "https://bounties.example.com/789"
    }

    msg2 = "Random message"
    assert process_bounty_message(msg2) is None

if __name__ == "__main__":
    _test_extract_bounty_link()
    _test_process_bounty_message()
    print("All tests passed.")