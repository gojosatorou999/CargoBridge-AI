import { motion } from "motion/react";
import { ArrowRight, CheckCircle2, Shield } from "lucide-react";

export function CTASection() {
  return (
    <section className="relative py-32 bg-gradient-to-br from-blue-950 via-slate-950 to-purple-950 overflow-hidden">
      <div className="absolute inset-0">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-blue-500/20 rounded-full blur-3xl" />
      </div>

      <div className="relative z-10 max-w-5xl mx-auto px-6 text-center">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-500/10 border border-blue-500/30 text-blue-300 mb-8 backdrop-blur-sm"
        >
          <Shield className="w-4 h-4" />
          <span className="text-sm">SOC 2 Certified • GDPR Compliant • ISO 27001</span>
        </motion.div>

        <motion.h2
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.2 }}
          className="text-5xl md:text-7xl font-bold mb-6 bg-gradient-to-r from-white via-blue-100 to-cyan-200 bg-clip-text text-transparent leading-tight"
        >
          Ready to Transform Your
          <br />
          Supply Chain?
        </motion.h2>

        <motion.p
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.4 }}
          className="text-xl text-blue-100/80 max-w-3xl mx-auto mb-12 leading-relaxed"
        >
          Join government agencies and enterprises worldwide using CargoBridge AI
          to optimize logistics, reduce costs, and build resilient supply chains.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.6 }}
          className="flex flex-col sm:flex-row gap-4 justify-center mb-12"
        >
          <button className="group relative px-8 py-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-xl overflow-hidden transition-all hover:scale-105 hover:shadow-[0_0_40px_rgba(59,130,246,0.6)]">
            <span className="relative z-10 flex items-center gap-2">
              Schedule Demo
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </span>
          </button>
          <button className="px-8 py-4 bg-white/10 hover:bg-white/20 text-white rounded-xl backdrop-blur-sm border border-white/20 transition-all hover:scale-105">
            Contact Sales
          </button>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.8 }}
          className="flex flex-wrap gap-6 justify-center text-sm text-blue-200/80"
        >
          {[
            "30-day free trial",
            "No credit card required",
            "24/7 support",
            "Custom deployment options"
          ].map((item) => (
            <div key={item} className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-green-400" />
              <span>{item}</span>
            </div>
          ))}
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 1 }}
          className="mt-16 pt-12 border-t border-white/10"
        >
          <p className="text-sm text-slate-400 mb-4">Trusted by leading organizations</p>
          <div className="flex flex-wrap gap-8 justify-center items-center opacity-60">
            {["Ministry of Transport", "Port Authority", "Global Logistics Corp", "Trade Bureau", "Export Council"].map((org) => (
              <div key={org} className="text-slate-500 font-semibold">{org}</div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
}
