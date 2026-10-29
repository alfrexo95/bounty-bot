```python
class Escrow:
    def __init__(self, amount):
        self.amount = amount
        self.status = "pending"
    
    def record_payment(self):
        self.status = "paid"
    
    def get_status(self):
        return self.status

# Example usage:
escrow = Escrow(250)
print(escrow.get_status())  # Output: pending
escrow.record_payment()
print(escrow.get_status())  # Output: paid
```