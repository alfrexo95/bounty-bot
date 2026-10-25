// escrow.ts
// Simple USDC escrow simulation in TypeScript

type Currency = 'USDC' | 'BTC' | 'ETH' | 'LTC';

interface Deposit {
  from: string;
  amount: number;
  currency: Currency;
  timestamp: Date;
}

interface Withdrawal {
  to: string;
  amount: number;
  currency: Currency;
  timestamp: Date;
}

class Escrow {
  private balances: Map<Currency, number>;
  private deposits: Deposit[];
  private withdrawals: Withdrawal[];

  constructor() {
    this.balances = new Map<Currency, number>([
      ['USDC', 0],
      ['BTC', 0],
      ['ETH', 0],
      ['LTC', 0],
    ]);
    this.deposits = [];
    this.withdrawals = [];
  }

  // Deposit funds into the escrow
  deposit(from: string, amount: number, currency: Currency): void {
    if (amount <= 0) {
      throw new Error('Deposit amount must be positive');
    }
    const current = this.balances.get(currency) ?? 0;
    this.balances.set(currency, current + amount);
    this.deposits.push({ from, amount, currency, timestamp: new Date() });
    console.log(`Deposited ${amount} ${currency} from ${from}`);
  }

  // Withdraw funds from the escrow
  withdraw(to: string, amount: number, currency: Currency): void {
    const current = this.balances.get(currency) ?? 0;
    if (amount <= 0) {
      throw new Error('Withdrawal amount must be positive');
    }
    if (amount > current) {
      throw new Error(`Insufficient ${currency} balance`);
    }
    this.balances.set(currency, current - amount);
    this.withdrawals.push({ to, amount, currency, timestamp: new Date() });
    console.log(`Withdrew ${amount} ${currency} to ${to}`);
  }

  // Get current balance for a specific currency
  getBalance(currency: Currency): number {
    return this.balances.get(currency) ?? 0;
  }

  // Get full ledger of deposits and withdrawals
  getLedger(): { deposits: Deposit[]; withdrawals: Withdrawal[] } {
    return {
      deposits: [...this.deposits],
      withdrawals: [...this.withdrawals],
    };
  }
}

// Example usage (can be removed in production)
if (require.main === module) {
  const escrow = new Escrow();

  // Simulate deposits
  escrow.deposit('alice@example.com', 100, 'USDC');
  escrow.deposit('bob@example.com', 0.005, 'BTC');

  // Simulate withdrawals
  escrow.withdraw('charlie@example.com', 50, 'USDC');
  escrow.withdraw('dave@example.com', 0.002, 'BTC');

  console.log('Final Balances:');
  console.log('USDC:', escrow.getBalance('USDC'));
  console.log('BTC:', escrow.getBalance('BTC'));

  console.log('Ledger:', escrow.getLedger());
}

export { Escrow, Currency, Deposit, Withdrawal };