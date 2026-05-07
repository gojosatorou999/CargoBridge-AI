import { motion, useScroll, useTransform } from "motion/react";
import { useRef } from "react";
import { Brain, Ship, BarChart3, Bell, Award, Users } from "lucide-react";

const features = [
  {
    icon: Brain,
    title: "AI-Powered Disruption Intelligence",
    description: "Multi-agent CrewAI pipeline analyzes disruptions with confidence scoring and weather validation",
    gradient: "from-violet-500 to-purple-600"
  },
  {
    icon: Ship,
    title: "Real-Time Vessel Tracking",
    description: "Live AIS data integration for accurate vessel positions and predictive ETAs",
    gradient: "from-blue-500 to-cyan-600"
  },
  {
    icon: BarChart3,
    title: "Predictive Analytics",
    description: "Advanced simulation tools for supply chain resilience and disruption trend analysis",
    gradient: "from-emerald-500 to-teal-600"
  },
  {
    icon: Bell,
    title: "Instant Alerts",
    description: "WhatsApp & SMS notifications via Twilio for critical updates and disruptions",
    gradient: "from-orange-500 to-red-600"
  },
  {
    icon: Award,
    title: "Gamification System",
    description: "Earn points and badges for on-time deliveries and verified reports",
    gradient: "from-yellow-500 to-orange-600"
  },
  {
    icon: Users,
    title: "Multi-Role Dashboards",
    description: "Customized views for Admins, Port Workers, Analysts, Drivers, and Exporters",
    gradient: "from-pink-500 to-rose-600"
  }
];

export function Features() {
  const ref = useRef(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "end start"]
  });

  const y = useTransform(scrollYProgress, [0, 1], ["10%", "-10%"]);

  return (
    <section ref={ref} className="relative py-32 bg-gradient-to-b from-slate-900 via-slate-800 to-slate-900 overflow-hidden">
      <motion.div style={{ y }} className="absolute inset-0 opacity-30">
        <div className="absolute top-20 left-1/4 w-72 h-72 bg-purple-500/20 rounded-full blur-3xl" />
        <div className="absolute bottom-20 right-1/4 w-72 h-72 bg-blue-500/20 rounded-full blur-3xl" />
      </motion.div>

      <div className="relative z-10 max-w-7xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="text-center mb-16"
        >
          <h2 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-white to-blue-200 bg-clip-text text-transparent">
            Enterprise-Grade Features
          </h2>
          <p className="text-xl text-slate-300 max-w-3xl mx-auto">
            Built for government agencies and large-scale logistics operations
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((feature, index) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 50 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              whileHover={{ scale: 1.05, y: -10 }}
              className="group relative"
            >
              <div className="absolute -inset-0.5 bg-gradient-to-r opacity-0 group-hover:opacity-100 rounded-2xl blur transition duration-500"
                   style={{
                     backgroundImage: `linear-gradient(to right, var(--tw-gradient-stops))`,
                     '--tw-gradient-from': 'rgb(59 130 246)',
                     '--tw-gradient-to': 'rgb(147 51 234)'
                   } as any} />

              <div className="relative h-full bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-8 hover:border-slate-600/50 transition-all">
                <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${feature.gradient} flex items-center justify-center mb-6 group-hover:shadow-[0_0_30px_rgba(59,130,246,0.3)] transition-shadow`}>
                  <feature.icon className="w-7 h-7 text-white" />
                </div>

                <h3 className="text-2xl font-bold text-white mb-4 group-hover:text-blue-300 transition-colors">
                  {feature.title}
                </h3>

                <p className="text-slate-400 leading-relaxed">
                  {feature.description}
                </p>

                <div className="absolute top-4 right-4 w-20 h-20 bg-gradient-to-br opacity-0 group-hover:opacity-20 rounded-full blur-2xl transition-opacity"
                     style={{
                       backgroundImage: `linear-gradient(to bottom right, var(--tw-gradient-stops))`,
                       '--tw-gradient-from': 'rgb(59 130 246)',
                       '--tw-gradient-to': 'rgb(147 51 234)'
                     } as any} />
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
