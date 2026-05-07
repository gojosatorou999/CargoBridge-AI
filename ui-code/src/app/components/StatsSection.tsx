import { motion, useScroll, useTransform } from "motion/react";
import { useRef, useEffect, useState } from "react";
import { TrendingUp, Users, Globe, Zap } from "lucide-react";

function AnimatedCounter({ end, duration = 2 }: { end: number; duration?: number }) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    let startTime: number;
    let animationFrame: number;

    const animate = (currentTime: number) => {
      if (!startTime) startTime = currentTime;
      const progress = Math.min((currentTime - startTime) / (duration * 1000), 1);

      setCount(Math.floor(progress * end));

      if (progress < 1) {
        animationFrame = requestAnimationFrame(animate);
      }
    };

    animationFrame = requestAnimationFrame(animate);

    return () => cancelAnimationFrame(animationFrame);
  }, [end, duration]);

  return <span>{count.toLocaleString()}</span>;
}

export function StatsSection() {
  const ref = useRef(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "end start"]
  });

  const y = useTransform(scrollYProgress, [0, 1], ["10%", "-10%"]);

  const stats = [
    { icon: Globe, value: 15000, suffix: "+", label: "Shipments Tracked", color: "from-blue-500 to-cyan-500" },
    { icon: Users, value: 5000, suffix: "+", label: "Active Users", color: "from-purple-500 to-pink-500" },
    { icon: TrendingUp, value: 98, suffix: "%", label: "Prediction Accuracy", color: "from-green-500 to-emerald-500" },
    { icon: Zap, value: 30, suffix: "%", label: "Cost Reduction", color: "from-orange-500 to-red-500" }
  ];

  return (
    <section ref={ref} className="relative py-32 bg-slate-900 overflow-hidden">
      <motion.div style={{ y }} className="absolute inset-0">
        <div className="absolute top-1/2 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl" />
        <div className="absolute top-1/2 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl" />
      </motion.div>

      <div className="relative z-10 max-w-7xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-white to-blue-200 bg-clip-text text-transparent">
            Impact at Scale
          </h2>
          <p className="text-xl text-slate-400 max-w-3xl mx-auto">
            Real results from real deployments across government and enterprise
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
          {stats.map((stat, index) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 50 }}
              whileInView={{ opacity: 1, y: 0 }}
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

              <div className="relative bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-8 text-center hover:border-blue-500/50 transition-all">
                <div className={`w-16 h-16 rounded-xl bg-gradient-to-br ${stat.color} flex items-center justify-center mx-auto mb-6 group-hover:shadow-[0_0_30px_rgba(59,130,246,0.4)] transition-shadow`}>
                  <stat.icon className="w-8 h-8 text-white" />
                </div>

                <div className="text-5xl font-bold text-white mb-2">
                  <AnimatedCounter end={stat.value} />
                  {stat.suffix}
                </div>

                <div className="text-slate-400">{stat.label}</div>
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
          <div className="inline-flex flex-col md:flex-row items-center gap-6 px-8 py-6 bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/20 rounded-2xl backdrop-blur-sm">
            <div className="text-center px-6">
              <div className="text-4xl font-bold text-white mb-1">$2.3M</div>
              <div className="text-sm text-slate-400">Annual Savings</div>
            </div>
            <div className="hidden md:block w-px h-12 bg-slate-700" />
            <div className="text-center px-6">
              <div className="text-4xl font-bold text-white mb-1">45%</div>
              <div className="text-sm text-slate-400">Faster Processing</div>
            </div>
            <div className="hidden md:block w-px h-12 bg-slate-700" />
            <div className="text-center px-6">
              <div className="text-4xl font-bold text-white mb-1">24/7</div>
              <div className="text-sm text-slate-400">AI Monitoring</div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
