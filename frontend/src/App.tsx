import { Route, Routes } from "react-router-dom";
import { Nav } from "./components/Nav";
import { DiscoveryFeed } from "./pages/DiscoveryFeed";
import { DiscoveryDetail } from "./pages/DiscoveryDetail";
import { States } from "./pages/States";
import { StateDetail } from "./pages/StateDetail";
import { SystemPage } from "./pages/System";

export default function App() {
  return (
    <div className="app-shell">
      <Nav />
      <Routes>
        <Route path="/" element={<DiscoveryFeed />} />
        <Route path="/discoveries/:id" element={<DiscoveryDetail />} />
        <Route path="/states" element={<States />} />
        <Route path="/states/:id" element={<StateDetail />} />
        <Route path="/system" element={<SystemPage />} />
      </Routes>
    </div>
  );
}
