import { Navbar } from "./components/Navbar";
import { Hero } from "./components/Hero";
import { Features } from "./components/Features";
import { StatsSection } from "./components/StatsSection";
import { TechStack } from "./components/TechStack";
import { RolesShowcase } from "./components/RolesShowcase";
import { CTASection } from "./components/CTASection";
import { Footer } from "./components/Footer";

export default function App() {
  return (
    <div className="min-h-screen bg-slate-950 text-white overflow-x-hidden">
      <Navbar />
      <Hero />
      <Features />
      <StatsSection />
      <TechStack />
      <RolesShowcase />
      <CTASection />
      <Footer />
    </div>
  );
}