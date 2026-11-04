```python
import requests

def fetch_bounty_details():
    url = "https://github.com/zhangjiayang6835-cyber/bounty-plaza/issues/4168"
    response = requests.get(url)
    return response.text

# Example usage:
# print(fetch_bounty_details())
```