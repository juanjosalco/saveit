import { Routes, Route, NavLink } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Transactions from "./pages/Transactions";
import Upload from "./pages/Upload";
import Rules from "./pages/Rules";
import Settings from "./pages/Settings";

const navCls = ({ isActive }: { isActive: boolean }) =>
  `px-3 py-2 rounded-md text-sm font-medium transition ${isActive ? "bg-slate-900 text-white" : "text-slate-700 hover:bg-slate-200"}`;

export default function App() {
  return (
    <div className="min-h-full">
      <nav className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center gap-2">
          <div className="font-bold text-slate-900 mr-4">🪙 SaveIt</div>
          <NavLink to="/" end className={navCls}>Dashboard</NavLink>
          <NavLink to="/transactions" className={navCls}>Transactions</NavLink>
          <NavLink to="/upload" className={navCls}>Upload</NavLink>
          <NavLink to="/rules" className={navCls}>Rules</NavLink>
          <NavLink to="/settings" className={navCls}>Settings</NavLink>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto px-4 py-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/transactions" element={<Transactions />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/rules" element={<Rules />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}
