```python
from github import GitHub

def create_github_issue(title, body):
    gh = GitHub()
    repo = gh.repository("alfrexo95", "bounty-bot")
    issue = repo.create_issue(title=title, body=body)
    return issue.to_dict()

# Example usage:
# create_github_issue("Bounty Seguro ($$250): [Bounty] Preserv", " Bounty Seguro ($$250): [Bounty] Preserv\n\n*Este issue fue creado automáticamente por mi bot.*")
```