import { motion } from "motion/react";
import { Menu, X } from "lucide-react";
import { useState } from "react";

export function Navbar() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <motion.nav
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      transition={{ duration: 0.6 }}
      className="fixed top-0 left-0 right-0 z-50 bg-slate-950/80 backdrop-blur-md border-b border-white/10"
    >
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-[0_0_20px_rgba(59,130,246,0.3)]">
              <span className="text-white font-bold text-xl">CB</span>
            </div>
            <span className="text-xl font-bold text-white">CargoBridge AI</span>
          </div>

          <div className="hidden md:flex items-center gap-8">
            <a href="#features" className="text-slate-300 hover:text-white transition-colors">Features</a>
            <a href="#technology" className="text-slate-300 hover:text-white transition-colors">Technology</a>
            <a href="#roles" className="text-slate-300 hover:text-white transition-colors">Solutions</a>
            <a href="#pricing" className="text-slate-300 hover:text-white transition-colors">Pricing</a>
            <button className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-all hover:shadow-[0_0_20px_rgba(59,130,246,0.4)]">
              Get Started
            </button>
          </div>

          <button
            onClick={() => setIsOpen(!isOpen)}
            className="md:hidden text-white"
          >
            {isOpen ? <X /> : <Menu />}
          </button>
        </div>

        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="md:hidden mt-4 pb-4 space-y-4"
          >
            <a href="#features" className="block text-slate-300 hover:text-white transition-colors">Features</a>
            <a href="#technology" className="block text-slate-300 hover:text-white transition-colors">Technology</a>
            <a href="#roles" className="block text-slate-300 hover:text-white transition-colors">Solutions</a>
            <a href="#pricing" className="block text-slate-300 hover:text-white transition-colors">Pricing</a>
            <button className="w-full px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-all">
              Get Started
            </button>
          </motion.div>
        )}
      </div>
    </motion.nav>
  );
}
