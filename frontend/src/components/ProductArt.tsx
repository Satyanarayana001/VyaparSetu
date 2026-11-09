/** Lightweight inline SVG pack illustrations (a few hundred bytes each; no image downloads on slow networks). Unbranded. */
export function ProductArt({ sku, className = "" }: { sku: string; className?: string }) {
  const common = { viewBox: "0 0 240 180", role: "img" as const, className, preserveAspectRatio: "xMidYMid meet" as const };
  if (sku === "SKU-BS-075")
    return (
      <svg {...common} aria-label="Biscuit packet">
        <rect width="240" height="180" fill="#EEF0FF" />
        <path d="M70 28h100l8 124H62z" fill="#F6C453" stroke="#12162B" strokeWidth="3" strokeLinejoin="round" />
        <path d="M66 28h108M64 152h112" stroke="#12162B" strokeWidth="3" strokeDasharray="4 5" />
        <circle cx="120" cy="86" r="30" fill="#E3A33A" stroke="#12162B" strokeWidth="3" />
        {[[110, 78], [128, 80], [118, 96], [132, 96], [108, 92]].map(([x, y]) => <circle key={`${x}${y}`} cx={x} cy={y} r="2.6" fill="#12162B" />)}
        <rect x="84" y="124" width="72" height="14" rx="3" fill="#fff" stroke="#12162B" strokeWidth="2" />
      </svg>
    );
  if (sku === "SKU-DT-1KG")
    return (
      <svg {...common} aria-label="Detergent pouch">
        <rect width="240" height="180" fill="#EEF0FF" />
        <path d="M64 34c18-8 94-8 112 0l6 118c-26 10-98 10-124 0z" fill="#3640D6" stroke="#12162B" strokeWidth="3" strokeLinejoin="round" />
        <circle cx="120" cy="84" r="28" fill="#fff" stroke="#12162B" strokeWidth="3" />
        <path d="M104 84q8-12 16 0t16 0" fill="none" stroke="#3640D6" strokeWidth="5" strokeLinecap="round" />
        <rect x="84" y="122" width="72" height="14" rx="3" fill="#fff" stroke="#12162B" strokeWidth="2" />
        <circle cx="168" cy="52" r="5" fill="#fff" opacity=".8" /><circle cx="180" cy="66" r="3" fill="#fff" opacity=".8" />
      </svg>
    );
  if (sku === "SKU-TE-250")
    return (
      <svg {...common} aria-label="Tea box">
        <rect width="240" height="180" fill="#EEF0FF" />
        <path d="M78 30h84l10 122H68z" fill="#2F8F5B" stroke="#12162B" strokeWidth="3" strokeLinejoin="round" />
        <path d="M120 66c-26 2-34 22-30 38 22 2 36-12 30-38z" fill="#D9F2E2" stroke="#12162B" strokeWidth="3" strokeLinejoin="round" />
        <path d="M120 66c-4 14-10 26-20 36" fill="none" stroke="#12162B" strokeWidth="2.5" />
        <rect x="88" y="122" width="64" height="14" rx="3" fill="#fff" stroke="#12162B" strokeWidth="2" />
      </svg>
    );
  return (
    <svg {...common} aria-label="Product"><rect width="240" height="180" fill="#EEF0FF" /><rect x="80" y="40" width="80" height="100" rx="8" fill="#fff" stroke="#12162B" strokeWidth="3" /></svg>
  );
}
