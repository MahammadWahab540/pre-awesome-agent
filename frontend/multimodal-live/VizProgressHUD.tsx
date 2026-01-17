import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, Loader2, CheckCircle2, Database, Cpu, FileCode } from "lucide-react";

interface VizProgressHUDProps {
  isVisible: boolean;
  step?: string;
  message?: string;
  progress?: number;
  intent?: string;
  data?: any;
}

const STEP_ICONS = {
  preparing: Sparkles,
  analyzing: Database,
  generating: Cpu,
  finalizing: FileCode
};

const STEP_COLORS = {
  preparing: "from-blue-500 to-cyan-500",
  analyzing: "from-purple-500 to-pink-500",
  generating: "from-orange-500 to-red-500",
  finalizing: "from-green-500 to-emerald-500"
};

export function VizProgressHUD({
  isVisible,
  step = "preparing",
  message = "Processing...",
  progress = 0,
  intent,
  data
}: VizProgressHUDProps) {
  const Icon = STEP_ICONS[step as keyof typeof STEP_ICONS] || Loader2;
  const colorGradient = STEP_COLORS[step as keyof typeof STEP_COLORS] || "from-indigo-500 to-purple-500";

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ opacity: 0, y: -20, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -20, scale: 0.9 }}
          transition={{ duration: 0.3 }}
          className="absolute top-6 right-6 z-50 w-[400px] pointer-events-none"
        >
          {/* Main HUD Card - Matching VizIntentCard style */}
          <div className="relative backdrop-blur-xl bg-[#0B0F17]/90 border border-white/10 rounded-2xl shadow-2xl overflow-hidden w-full">

            {/* Animated Background Glow */}
            <motion.div
              className={`absolute inset-0 bg-gradient-to-r ${colorGradient} opacity-10`}
              animate={{
                scale: [1, 1.1, 1],
                opacity: [0.1, 0.2, 0.1],
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: "easeInOut"
              }}
            />

            {/* Content */}
            <div className="relative p-4">

              {/* Header */}
              <div className="flex items-center gap-3 mb-3">
                <motion.div
                  className={`relative flex items-center justify-center w-10 h-10 rounded-lg bg-gradient-to-br ${colorGradient}`}
                  animate={{
                    rotate: step === "generating" ? [0, 360] : 0,
                  }}
                  transition={{
                    duration: 2,
                    repeat: step === "generating" ? Infinity : 0,
                    ease: "linear"
                  }}
                >
                  <Icon className="w-5 h-5 text-white" />
                </motion.div>

                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                      AI Visualizing
                    </h3>
                    <motion.div
                      className="flex gap-0.5"
                      animate={{ opacity: [0.5, 1, 0.5] }}
                      transition={{ duration: 1.5, repeat: Infinity }}
                    >
                      {[0, 1, 2].map((i) => (
                        <div key={i} className="w-1 h-1 bg-cyan-400 rounded-full" />
                      ))}
                    </motion.div>
                  </div>
                  <p className="text-[10px] text-gray-400 mt-0.5">
                    {intent?.replace(/_/g, ' ')}
                  </p>
                </div>
              </div>

              {/* Message */}
              <p className="text-sm text-gray-300 mb-3 font-medium">
                {message}
              </p>

              {/* Progress Bar */}
              <div className="relative h-1.5 bg-white/10 rounded-full overflow-hidden mb-3">
                <motion.div
                  className={`absolute inset-y-0 left-0 bg-gradient-to-r ${colorGradient} rounded-full`}
                  initial={{ width: "0%" }}
                  animate={{ width: `${progress}%` }}
                  transition={{ duration: 0.5, ease: "easeOut" }}
                />

                {/* Shimmer effect */}
                <motion.div
                  className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent"
                  animate={{
                    x: ["-100%", "200%"],
                  }}
                  transition={{
                    duration: 1.5,
                    repeat: Infinity,
                    ease: "linear"
                  }}
                />
              </div>

              {/* Progress Percentage */}
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-gray-400">
                  {progress}% Complete
                </span>
                <span className="text-xs font-mono text-cyan-400">
                  {step.charAt(0).toUpperCase() + step.slice(1)}
                </span>
              </div>

              {/* Optional: Show extracted data */}
              {data && Object.keys(data).length > 0 && (
                <div className="mt-3 pt-3 border-t border-white/10">
                  <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-2">
                    Extracted Data
                  </p>
                  <div className="space-y-1">
                    {Object.entries(data).slice(0, 2).map(([key, value]) => (
                      <div key={key} className="flex items-center gap-2 text-xs">
                        <div className="w-1.5 h-1.5 rounded-full bg-cyan-400"></div>
                        <span className="text-gray-500">{key}:</span>
                        <span className="text-white font-medium truncate">
                          {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Bottom accent line */}
            <div className={`h-0.5 bg-gradient-to-r ${colorGradient}`} />
          </div>

          {/* Floating particles effect */}
          <div className="absolute inset-0 pointer-events-none">
            {[...Array(3)].map((_, i) => (
              <motion.div
                key={i}
                className="absolute w-1 h-1 bg-cyan-400 rounded-full"
                style={{
                  left: `${20 + i * 30}%`,
                  top: "50%",
                }}
                animate={{
                  y: [-20, -60],
                  opacity: [0, 1, 0],
                  scale: [0, 1, 0],
                }}
                transition={{
                  duration: 2,
                  repeat: Infinity,
                  delay: i * 0.3,
                  ease: "easeOut"
                }}
              />
            ))}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

