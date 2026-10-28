```python
from .models import Bounty

def check_escrow(bounty_id):
    """
    Verifica si el escrow está activo antes de trabajar en la Bounty.
    """
    try:
        bounty = Bounty.objects.get(id=bounty_id)
        if bounty.escrow_status == "active":
            return True
        return False
    except Bounty.DoesNotExist:
        return False
    except Exception as e:
        print(f"Error al verificar el escrow: {e}")
        return False

# Nota: Asegúrate de que el escrow esté activo antes de trabajar.
```