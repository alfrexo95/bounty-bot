/**
 * Simple USDC Escrow implementation using ethers.js.
 *
 * This module provides an `Escrow` class that can be used to lock USDC tokens
 * from a payer until a designated beneficiary releases them. It also supports
 * a refund mechanism if the escrow is cancelled.
 *
 * Prerequisites:
 *   - Node.js >= 14
 *   - ethers (npm install ethers)
 *   - USDC token contract address on the target network
 *
 * Note: This is a client‑side helper; the actual token transfer logic is
 * performed on-chain via the USDC ERC‑20 contract. Ensure the payer has
 * approved the escrow contract (or this helper's signer) to spend the required
 * amount before calling `deposit`.
 */

import { ethers, Contract, Signer, providers } from "ethers";

/**
 * Minimal ERC‑20 ABI required for allowance, approve and transferFrom.
 */
const ERC20_ABI = [
  "function name() view returns (string)",
  "function symbol() view returns (string)",
  "function decimals() view returns (uint8)",
  "function balanceOf(address) view returns (uint256)",
  "function allowance(address owner, address spender) view returns (uint256)",
  "function approve(address spender, uint256 amount) returns (bool)",
  "function transferFrom(address from, address to, uint256 amount) returns (bool)",
] as const;

/**
 * Escrow state enumeration.
 */
enum EscrowStatus {
  Pending = "Pending",
  Completed = "Completed",
  Refunded = "Refunded",
  Cancelled = "Cancelled",
}

/**
 * Interface describing an escrow record.
 */
interface EscrowRecord {
  id: string;
  payer: string;
  beneficiary: string;
  amount: ethers.BigNumber;
  token: Contract;
  status: EscrowStatus;
}

/**
 * Escrow manager class.
 */
export class Escrow {
  private provider: providers.Provider;
  private signer: Signer;
  private usdc: Contract;
  private escrows: Map<string, EscrowRecord>;

  /**
   * @param provider   Ethers provider (e.g., Infura, Alchemy, JsonRpc)
   * @param signer     Signer that will act as the escrow manager (must have ETH for gas)
   * @param usdcAddress USDC token contract address on the target network
   */
  constructor(provider: providers.Provider, signer: Signer, usdcAddress: string) {
    this.provider = provider;
    this.signer = signer;
    this.usdc = new ethers.Contract(usdcAddress, ERC20_ABI, signer);
    this.escrows = new Map();
  }

  /**
   * Creates a new escrow entry and transfers USDC from the payer to the escrow manager.
   *
   * @param payer        Address of the token sender.
   * @param beneficiary  Address that will receive the tokens when released.
   * @param amount       Amount of USDC (in smallest unit, i.e., 6 decimals).
   * @returns            Unique escrow ID.
   */
  async createEscrow(payer: string, beneficiary: string, amount: ethers.BigNumberish): Promise<string> {
    const escrowId = ethers.utils.keccak256(
      ethers.utils.defaultAbiCoder.encode(
        ["address", "address", "uint256", "uint256"],
        [payer, beneficiary, amount, Date.now()]
      )
    );

    // Ensure allowance is sufficient
    const allowance: ethers.BigNumber = await this.usdc.allowance(payer, await this.signer.getAddress());
    if (allowance.lt(amount)) {
      throw new Error("Insufficient allowance. Payer must approve the escrow contract to spend USDC.");
    }

    // Transfer tokens from payer to escrow manager (this.signer)
    const tx = await this.usdc.transferFrom(payer, await this.signer.getAddress(), amount);
    await tx.wait();

    const record: EscrowRecord = {
      id: escrowId,
      payer,
      beneficiary,
      amount: ethers.BigNumber.from(amount),
      token: this.usdc,
      status: EscrowStatus.Pending,
    };
    this.escrows.set(escrowId, record);
    return escrowId;
  }

  /**
   * Releases the locked USDC to the beneficiary.
   *
   * @param escrowId ID of the escrow to release.
   */
  async release(escrowId: string): Promise<void> {
    const record = this.escrows.get(escrowId);
    if (!record) throw new Error("Escrow not found");
    if (record.status !== EscrowStatus.Pending) throw new Error("Escrow not in a releasable state");

    const tx = await record.token.transfer(record.beneficiary, record.amount);
    await tx.wait();

    record.status = EscrowStatus.Completed;
    this.escrows.set(escrowId, record);
  }

  /**
   * Refunds the locked USDC back to the payer.
   *
   * @param escrowId ID of the escrow to refund.
   */
  async refund(escrowId: string): Promise<void> {
    const record = this.escrows.get(escrowId);
    if (!record) throw new Error("Escrow not found");
    if (record.status !== EscrowStatus.Pending) throw new Error("Escrow not in a refundable state");

    const tx = await record.token.transfer(record.payer, record.amount);
    await tx.wait();

    record.status = EscrowStatus.Refunded;
    this.escrows.set(escrowId, record);
  }

  /**
   * Retrieves escrow details.
   *
   * @param escrowId ID of the escrow.
   */
  getEscrow(escrowId: string): EscrowRecord | undefined {
    return this.escrows.get(escrowId);
  }

  /**
   * Utility: fetch USDC token metadata.
   */
  async getTokenInfo(): Promise<{ name: string; symbol: string; decimals: number }> {
    const [name, symbol, decimals] = await Promise.all([
      this.usdc.name(),
      this.usdc.symbol(),
      this.usdc.decimals(),
    ]);
    return { name, symbol, decimals };
  }
}

/* -------------------------------------------------------------------------- */
/* Example usage (uncomment to run)                                          */
/* -------------------------------------------------------------------------- */
/*
(async () => {
  const provider = new ethers.providers.InfuraProvider("goerli", "<INFURA_API_KEY>");
  const wallet = new ethers.Wallet("<PRIVATE_KEY>", provider);
  const USDC_GOERLI = "0x07865c6e87b9f70255377e024ace6630c1eaa37f"; // USDC on Goerli

  const escrow = new Escrow(provider, wallet, USDC_GOERLI);

  // Payer must approve the escrow manager first:
  // const usdc = new ethers.Contract(USDC_GOERLI, ERC20_ABI, wallet);
  // await usdc.approve(await wallet.getAddress(), ethers.utils.parseUnits("100", 6));

  const escrowId = await escrow.createEscrow(
    "0xPayerAddress...",
    "0xBeneficiaryAddress...",
    ethers.utils.parseUnits("10", 6) // 10 USDC
  );
  console.log("Escrow created:", escrowId);

  // Release funds:
  // await escrow.release(escrowId);

  // Or refund:
  // await escrow.refund(escrowId);
})();
*/