export function formatWeight(kg: number | null | undefined): string {
  if (kg === null || kg === undefined) return "—";
  const num = Number(kg);
  if (isNaN(num)) return "—";
  if (num >= 1000) {
    const mt = num / 1000;
    return `${mt.toLocaleString("en-IN", { maximumFractionDigits: 1 })} MT`;
  }
  return `${num.toLocaleString("en-IN", { maximumFractionDigits: 0 })} kg`;
}

export function formatCurrency(amount: number | null | undefined, unit: string = "/kg"): string {
  if (amount === null || amount === undefined) return "—";
  const num = Number(amount);
  if (isNaN(num)) return "—";
  return `₹${num.toFixed(2)}${unit}`;
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const num = Number(value);
  if (isNaN(num)) return "—";
  return `${num.toFixed(1)}%`;
}

export function getRiskBadgeClass(level: string | null | undefined): string {
  switch (level?.toUpperCase()) {
    case "HIGH":
      return "badge-risk-high";
    case "MEDIUM":
      return "badge-risk-medium";
    case "LOW":
      return "badge-risk-low";
    default:
      return "badge-neutral";
  }
}

export function formatActionTitle(action: string): string {
  switch (action) {
    case "SELL_NOW":
      return "Sell Produce Now";
    case "STAGGER_HARVEST":
      return "Stagger Your Harvest";
    case "STORE_COLD":
      return "Utilize Cold Storage";
    case "SEEK_ALTERNATE_MARKET":
      return "Sell in Alternate Mandi";
    case "MONITOR_PRICE":
      return "Hold & Monitor Market Prices";
    case "STAGGER_RELEASES":
      return "Stagger Inventory Releases";
    case "COORDINATE_WITH_BUYERS":
      return "Coordinate Forward Contracts with Buyers";
    case "PRIORITIZE_LONG_STORAGE":
      return "Prioritize Long-Duration Storage";
    case "MAINTAIN_NORMAL_OPERATIONS":
      return "Maintain Normal Operations";
    default:
      return action.replace(/_/g, " ");
  }
}
