"""
Implementation patch for [ESCROW BOUNTY] 🔌 2 for alfrexo95/bounty-bot.
Source: https://github.com/alfrexo95/bounty-bot/issues/31

This module adds a simple escrow bounty tracking mechanism, with
secure, modular, and testable code. No external dependencies.
"""

from typing import Dict, Optional, List


class EscrowBounty:
    """
    Represents a single escrow bounty.
    """
    def __init__(self, bounty_id: int, title: str, amount_usd: float, link: str) -> None:
        """
        Initialize a new EscrowBounty.

        :param bounty_id: Unique identifier for the bounty.
        :param title: Title or description of the bounty.
        :param amount_usd: Amount in USD.
        :param link: Reference link for the bounty.
        """
        self.bounty_id: int = bounty_id
        self.title: str = title
        self.amount_usd: float = amount_usd
        self.link: str = link
        self.is_claimed: bool = False
        self.claimer: Optional[str] = None

    def claim(self, user: str) -> bool:
        """
        Attempt to claim the bounty.

        :param user: Username of the claimer.
        :return: True if claim successful, False if already claimed.
        """
        if self.is_claimed:
            return False
        self.is_claimed = True
        self.claimer = user
        return True

    def release(self) -> None:
        """
        Release the bounty claim.
        """
        self.is_claimed = False
        self.claimer = None

    def to_dict(self) -> Dict[str, object]:
        """
        Serialize bounty to dictionary.

        :return: Dictionary representation of the bounty.
        """
        return {
            "bounty_id": self.bounty_id,
            "title": self.title,
            "amount_usd": self.amount_usd,
            "link": self.link,
            "is_claimed": self.is_claimed,
            "claimer": self.claimer,
        }


class EscrowBountyManager:
    """
    Manages multiple escrow bounties.
    """
    def __init__(self) -> None:
        self._bounties: Dict[int, EscrowBounty] = {}
        self._next_id: int = 1

    def create_bounty(self, title: str, amount_usd: float, link: str) -> EscrowBounty:
        """
        Create a new bounty.

        :param title: Title or description.
        :param amount_usd: Amount in USD.
        :param link: Reference link.
        :return: The created EscrowBounty object.
        """
        bounty = EscrowBounty(
            bounty_id=self._next_id,
            title=title,
            amount_usd=amount_usd,
            link=link
        )
        self._bounties[self._next_id] = bounty
        self._next_id += 1
        return bounty

    def get_bounty(self, bounty_id: int) -> Optional[EscrowBounty]:
        """
        Retrieve a bounty by its ID.

        :param bounty_id: The bounty's unique ID.
        :return: The EscrowBounty or None if not found.
        """
        return self._bounties.get(bounty_id)

    def list_bounties(self, only_open: bool = False) -> List[EscrowBounty]:
        """
        List all bounties.

        :param only_open: If True, only unclaimed bounties are returned.
        :return: List of EscrowBounty objects.
        """
        if only_open:
            return [b for b in self._bounties.values() if not b.is_claimed]
        return list(self._bounties.values())

    def claim_bounty(self, bounty_id: int, user: str) -> bool:
        """
        Attempt to claim a bounty.

        :param bounty_id: The bounty's unique ID.
        :param user: Username of the claimer.
        :return: True if claim successful, False otherwise.
        """
        bounty = self.get_bounty(bounty_id)
        if bounty is None:
            return False
        return bounty.claim(user)

    def release_bounty(self, bounty_id: int) -> bool:
        """
        Release a claimed bounty.

        :param bounty_id: The bounty's unique ID.
        :return: True if released, False if not found or not claimed.
        """
        bounty = self.get_bounty(bounty_id)
        if bounty is None or not bounty.is_claimed:
            return False
        bounty.release()
        return True


# --- Tests ---

def _test_escrow_bounty_manager() -> None:
    manager = EscrowBountyManager()
    # Create bounties
    b1 = manager.create_bounty(
        title="Implement feature X",
        amount_usd=25.0,
        link="https://github.com/alfrexo95/bounty-bot/issues/31"
    )
    b2 = manager.create_bounty(
        title="Fix bug Y",
        amount_usd=10.0,
        link="https://github.com/alfrexo95/bounty-bot/issues/32"
    )

    assert b1.bounty_id == 1
    assert b2.bounty_id == 2
    assert not b1.is_claimed
    assert manager.get_bounty(1) is b1
    assert manager.get_bounty(2) is b2
    assert manager.get_bounty(3) is None

    # List bounties
    all_bounties = manager.list_bounties()
    assert len(all_bounties) == 2

    open_bounties = manager.list_bounties(only_open=True)
    assert len(open_bounties) == 2

    # Claim bounty
    assert manager.claim_bounty(1, "alice")
    assert b1.is_claimed
    assert b1.claimer == "alice"
    assert not manager.claim_bounty(1, "bob")  # Already claimed

    open_bounties = manager.list_bounties(only_open=True)
    assert len(open_bounties) == 1
    assert open_bounties[0].bounty_id == 2

    # Release bounty
    assert manager.release_bounty(1)
    assert not b1.is_claimed
    assert b1.claimer is None

    # Claim again
    assert manager.claim_bounty(1, "bob")
    assert b1.is_claimed
    assert b1.claimer == "bob"

    # Release non-claimed
    assert not manager.release_bounty(2)  # Not claimed

    print("All tests passed.")


if __name__ == "__main__":
    _test_escrow_bounty_manager()