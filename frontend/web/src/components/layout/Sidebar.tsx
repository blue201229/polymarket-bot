"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: "📊" },
  { href: "/markets", label: "Markets", icon: "🏪" },
  { href: "/trades", label: "Trades", icon: "📈" },
  { href: "/wallets", label: "Wallets", icon: "👛" },
  { href: "/ai", label: "AI Center", icon: "🤖" },
  { href: "/settings", label: "Settings", icon: "⚙️" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-60 min-h-screen bg-gray-950 border-r border-gray-800 flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-gray-800">
        <h1 className="text-white font-bold text-lg leading-tight">
          Polymarket AI
          <span className="block text-xs text-gray-500 font-normal mt-0.5">Trading Platform</span>
        </h1>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-1">
        {NAV_ITEMS.map(({ href, label, icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
              pathname === href
                ? "bg-white/10 text-white"
                : "text-gray-400 hover:text-white hover:bg-white/5",
            )}
          >
            <span>{icon}</span>
            <span>{label}</span>
          </Link>
        ))}
      </nav>

      {/* Paper trading indicator */}
      <div className="p-4 border-t border-gray-800">
        <div className="flex items-center gap-2 px-3 py-2 bg-blue-500/10 border border-blue-500/20 rounded-lg">
          <span className="text-blue-300 text-sm">📝</span>
          <div>
            <p className="text-blue-300 text-xs font-medium">Paper Trading Mode</p>
            <p className="text-blue-400/70 text-xs">No real funds at risk</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
