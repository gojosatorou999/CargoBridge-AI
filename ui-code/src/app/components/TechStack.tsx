import { motion } from "motion/react";
import { Code2, Database, Cpu, Cloud, Lock, Zap } from "lucide-react";

const technologies = [
  { category: "AI & ML", items: ["CrewAI", "OpenAI GPT-4", "LangChain", "TensorFlow"], icon: Cpu, color: "from-purple-500 to-pink-500" },
  { category: "Backend", items: ["Python Flask", "SQLAlchemy", "PostgreSQL", "APScheduler"], icon: Code2, color: "from-blue-500 to-cyan-500" },
  { category: "Data & APIs", items: ["AISStream", "Weather APIs", "MarineTraffic", "Twilio"], icon: Database, color: "from-green-500 to-emerald-500" },
  { category: "Infrastructure", items: ["Docker", "Kubernetes", "AWS", "Redis"], icon: Cloud, color: "from-orange-500 to-red-500" },
  { category: "Security", items: ["OAuth 2.0", "JWT", "SSL/TLS", "SOC 2 Compliant"], icon: Lock, color: "from-yellow-500 to-orange-500" },
  { category: "Performance", items: ["Real-time WebSockets", "CDN", "Load Balancing", "Caching"], icon: Zap, color: "from-indigo-500 to-purple-500" }
];

export function TechStack() {
  return (
    <section className="relative py-32 bg-slate-950 overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-blue-900/20 via-slate-950 to-slate-950" />

      <div className="relative z-10 max-w-7xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-white via-blue-100 to-cyan-200 bg-clip-text text-transparent">
            Battle-Tested Technology
          </h2>
          <p className="text-xl text-slate-400 max-w-3xl mx-auto">
            Built on enterprise-grade infrastructure for mission-critical operations
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {technologies.map((tech, index) => (
            <motion.div
              key={tech.category}
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              className="group relative"
            >
              <div className="absolute -inset-1 bg-gradient-to-r rounded-2xl opacity-0 group-hover:opacity-100 blur-xl transition duration-500"
                   style={{
                     backgroundImage: `linear-gradient(to right, var(--tw-gradient-stops))`,
                     '--tw-gradient-from': 'rgb(59 130 246)',
                     '--tw-gradient-to': 'rgb(147 51 234)'
                   } as any} />

              <div className="relative bg-slate-900/80 backdrop-blur-sm border border-slate-800 rounded-2xl p-6 hover:border-blue-500/50 transition-all">
                <div className="flex items-center gap-4 mb-4">
                  <div className={`w-12 h-12 rounded-lg bg-gradient-to-br ${tech.color} flex items-center justify-center`}>
                    <tech.icon className="w-6 h-6 text-white" />
                  </div>
                  <h3 className="text-xl font-bold text-white">{tech.category}</h3>
                </div>

                <div className="flex flex-wrap gap-2">
                  {tech.items.map((item) => (
                    <span
                      key={item}
                      className="px-3 py-1.5 bg-slate-800/80 text-slate-300 rounded-lg text-sm border border-slate-700/50 hover:border-blue-500/50 hover:text-blue-300 transition-colors cursor-default"
                    >
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mt-16 text-center"
        >
          <div className="inline-flex items-center gap-8 px-8 py-6 bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/20 rounded-2xl backdrop-blur-sm">
            <div className="text-center">
              <div className="text-3xl font-bold text-white mb-1">99.9%</div>
              <div className="text-sm text-slate-400">Uptime SLA</div>
            </div>
            <div className="w-px h-12 bg-slate-700" />
            <div className="text-center">
              <div className="text-3xl font-bold text-white mb-1">&lt;100ms</div>
              <div className="text-sm text-slate-400">API Response</div>
            </div>
            <div className="w-px h-12 bg-slate-700" />
            <div className="text-center">
              <div className="text-3xl font-bold text-white mb-1">SOC 2</div>
              <div className="text-sm text-slate-400">Certified</div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
