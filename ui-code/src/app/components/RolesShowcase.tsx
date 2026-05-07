import { motion, useScroll, useTransform } from "motion/react";
import { useRef, useState } from "react";
import { UserCog, Ship, TrendingUp, Truck, Building2 } from "lucide-react";

const roles = [
  {
    icon: UserCog,
    title: "Admin Dashboard",
    description: "Complete system oversight with user management, analytics, and system health monitoring",
    color: "from-red-500 to-orange-500",
    features: ["User Management", "System Analytics", "Audit Logs", "Global Settings"]
  },
  {
    icon: Ship,
    title: "Port Workers",
    description: "Real-time terminal operations, slot management, and vessel tracking",
    color: "from-blue-500 to-cyan-500",
    features: ["Slot Allocation", "Vessel Status", "Terminal Capacity", "Delay Reports"]
  },
  {
    icon: TrendingUp,
    title: "Data Analysts",
    description: "Advanced predictive analytics, disruption modeling, and resilience simulation",
    color: "from-purple-500 to-pink-500",
    features: ["Trend Analysis", "ML Models", "Forecasting", "Custom Reports"]
  },
  {
    icon: Truck,
    title: "Truck Drivers",
    description: "Route optimization, real-time alerts, and gamified delivery tracking",
    color: "from-green-500 to-emerald-500",
    features: ["Route Planning", "Live Updates", "Points & Badges", "Trip History"]
  },
  {
    icon: Building2,
    title: "MSME Exporters",
    description: "Shipment visibility, disruption alerts, and smart booking recommendations",
    color: "from-yellow-500 to-orange-500",
    features: ["Shipment Tracking", "Cost Optimization", "Alert Notifications", "Booking System"]
  }
];

export function RolesShowcase() {
  const [activeRole, setActiveRole] = useState(0);
  const ref = useRef(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "end start"]
  });

  const y = useTransform(scrollYProgress, [0, 1], ["5%", "-5%"]);

  return (
    <section ref={ref} className="relative py-32 bg-gradient-to-b from-slate-900 via-slate-950 to-slate-900 overflow-hidden">
      <motion.div style={{ y }} className="absolute inset-0">
        <div className="absolute top-1/3 left-10 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/3 right-10 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl" />
      </motion.div>

      <div className="relative z-10 max-w-7xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-white to-purple-200 bg-clip-text text-transparent">
            Multi-Role Intelligence
          </h2>
          <p className="text-xl text-slate-400 max-w-3xl mx-auto">
            Tailored dashboards for every stakeholder in the supply chain ecosystem
          </p>
        </motion.div>

        <div className="grid lg:grid-cols-2 gap-12 items-center">
          <div className="space-y-4">
            {roles.map((role, index) => (
              <motion.div
                key={role.title}
                initial={{ opacity: 0, x: -50 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                onClick={() => setActiveRole(index)}
                className={`group cursor-pointer p-6 rounded-2xl border transition-all ${
                  activeRole === index
                    ? 'bg-slate-800/80 border-blue-500/50 shadow-[0_0_30px_rgba(59,130,246,0.2)]'
                    : 'bg-slate-900/50 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="flex items-start gap-4">
                  <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${role.color} flex items-center justify-center flex-shrink-0 ${
                    activeRole === index ? 'shadow-[0_0_20px_rgba(59,130,246,0.3)]' : ''
                  }`}>
                    <role.icon className="w-6 h-6 text-white" />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-xl font-bold text-white mb-2">{role.title}</h3>
                    <p className="text-slate-400 text-sm mb-3">{role.description}</p>
                    <div className="flex flex-wrap gap-2">
                      {role.features.map((feature) => (
                        <span
                          key={feature}
                          className="px-2.5 py-1 bg-slate-800/60 text-slate-300 rounded-lg text-xs border border-slate-700/50"
                        >
                          {feature}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>

          <motion.div
            key={activeRole}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
            className="relative"
          >
            <div className="absolute -inset-4 bg-gradient-to-r rounded-3xl opacity-30 blur-2xl"
                 style={{
                   backgroundImage: `linear-gradient(to right, var(--tw-gradient-stops))`,
                   '--tw-gradient-from': 'rgb(59 130 246)',
                   '--tw-gradient-to': 'rgb(147 51 234)'
                 } as any} />

            <div className="relative bg-slate-900/90 border border-slate-700/50 rounded-3xl p-8 backdrop-blur-sm">
              <div className={`w-20 h-20 rounded-2xl bg-gradient-to-br ${roles[activeRole].color} flex items-center justify-center mb-6 shadow-[0_0_30px_rgba(59,130,246,0.3)]`}>
                {(() => {
                  const Icon = roles[activeRole].icon;
                  return <Icon className="w-10 h-10 text-white" />;
                })()}
              </div>

              <h3 className="text-3xl font-bold text-white mb-4">{roles[activeRole].title}</h3>
              <p className="text-slate-300 mb-6 leading-relaxed">{roles[activeRole].description}</p>

              <div className="space-y-3">
                {roles[activeRole].features.map((feature, index) => (
                  <motion.div
                    key={feature}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.3, delay: index * 0.1 }}
                    className="flex items-center gap-3 p-3 bg-slate-800/50 rounded-xl border border-slate-700/50"
                  >
                    <div className="w-2 h-2 rounded-full bg-blue-500" />
                    <span className="text-slate-200">{feature}</span>
                  </motion.div>
                ))}
              </div>

              <button className="mt-8 w-full py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-xl hover:shadow-[0_0_30px_rgba(59,130,246,0.4)] transition-all hover:scale-105">
                Explore Dashboard
              </button>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
