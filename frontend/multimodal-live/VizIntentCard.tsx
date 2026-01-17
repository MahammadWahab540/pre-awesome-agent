import { motion } from "framer-motion";
import { Sparkles, Target, Workflow, AlertTriangle, BarChart3 } from "lucide-react";

interface VizIntentCardProps {
  intent: string;
  data: any;
  reasoning?: string;
  isGenerating?: boolean;
}

const INTENT_CONFIG = {
  PROCESS_FLOW: {
    icon: Workflow,
    color: "cyan",
    gradient: "from-cyan-500 to-blue-500",
    label: "Workflow Detected",
    description: "Mapping process steps"
  },
  KPI_DASHBOARD: {
    icon: BarChart3,
    color: "emerald",
    gradient: "from-emerald-500 to-green-500",
    label: "Metrics Detected",
    description: "Building KPI visualization"
  },
  RISK_CARD: {
    icon: AlertTriangle,
    color: "amber",
    gradient: "from-amber-500 to-orange-500",
    label: "Risk Identified",
    description: "Analyzing problem impact"
  },
  STAGE_SUMMARY_CARD: {
    icon: Target,
    color: "violet",
    gradient: "from-violet-500 to-purple-500",
    label: "Stage Complete",
    description: "Generating summary card"
  }
};

export function VizIntentCard({ intent, data, reasoning, isGenerating = true }: VizIntentCardProps) {
  const config = INTENT_CONFIG[intent as keyof typeof INTENT_CONFIG] || {
    icon: Sparkles,
    color: "indigo",
    gradient: "from-indigo-500 to-purple-500",
    label: "Insight Detected",
    description: "Creating visualization"
  };

  const Icon = config.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="flex items-center justify-center min-h-[400px] p-8"
    >
      <div className="relative max-w-lg w-full">
        {/* Glowing Background Effect */}
        <motion.div
          className={`absolute inset-0 bg-gradient-to-r ${config.gradient} opacity-20 blur-3xl rounded-full`}
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.2, 0.3, 0.2],
          }}
          transition={{
            duration: 3,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />

        {/* Main Card */}
        <div className="relative backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl p-8 shadow-2xl">
          
          {/* Header with Icon */}
          <div className="flex items-center gap-4 mb-6">
            <motion.div
              className={`relative flex items-center justify-center w-16 h-16 rounded-xl bg-gradient-to-br ${config.gradient} shadow-lg`}
              animate={{
                rotate: isGenerating ? [0, 5, -5, 0] : 0,
              }}
              transition={{
                duration: 2,
                repeat: isGenerating ? Infinity : 0,
                ease: "easeInOut"
              }}
            >
              <Icon className="w-8 h-8 text-white" />
              
              {/* Ping Effect */}
              {isGenerating && (
                <span className={`absolute -top-1 -right-1 flex h-4 w-4`}>
                  <span className={`animate-ping absolute inline-flex h-full w-full rounded-full bg-${config.color}-400 opacity-75`}></span>
                  <span className={`relative inline-flex rounded-full h-4 w-4 bg-${config.color}-500`}></span>
                </span>
              )}
            </motion.div>

            <div className="flex-1">
              <h3 className="text-xl font-bold text-white mb-1">
                {config.label}
              </h3>
              <p className="text-sm text-gray-400">
                {config.description}
              </p>
            </div>
          </div>

          {/* Divider */}
          <div className={`h-[1px] bg-gradient-to-r ${config.gradient} opacity-20 mb-6`} />

          {/* Data Preview */}
          {data && Object.keys(data).length > 0 && (
            <div className="mb-6 space-y-3">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
                Extracted Data
              </p>
              {Object.entries(data).slice(0, 3).map(([key, value]) => (
                <div key={key} className="flex items-start gap-3">
                  <div className="flex-shrink-0 w-2 h-2 mt-1.5 rounded-full bg-gradient-to-r from-cyan-400 to-blue-400" />
                  <div className="flex-1">
                    <span className="text-xs text-gray-500 capitalize">{key.replace(/_/g, ' ')}</span>
                    <p className="text-sm text-white font-medium mt-0.5">
                      {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Reasoning */}
          {reasoning && (
            <div className="mb-6">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                AI Reasoning
              </p>
              <p className="text-sm text-gray-300 leading-relaxed italic">
                "{reasoning}"
              </p>
            </div>
          )}

          {/* Loading Indicator */}
          {isGenerating && (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <motion.div
                  className="flex gap-1.5"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                >
                  {[0, 1, 2].map((i) => (
                    <motion.div
                      key={i}
                      className={`w-2 h-2 rounded-full bg-gradient-to-r ${config.gradient}`}
                      animate={{
                        scale: [1, 1.3, 1],
                        opacity: [0.5, 1, 0.5],
                      }}
                      transition={{
                        duration: 1.5,
                        repeat: Infinity,
                        delay: i * 0.2,
                        ease: "easeInOut"
                      }}
                    />
                  ))}
                </motion.div>
                <p className="text-sm text-gray-400 font-medium">
                  Crafting beautiful visualization...
                </p>
              </div>

              {/* Progress Bar */}
              <div className="relative h-1 bg-white/5 rounded-full overflow-hidden">
                <motion.div
                  className={`absolute inset-y-0 left-0 bg-gradient-to-r ${config.gradient}`}
                  initial={{ width: "0%" }}
                  animate={{ width: "100%" }}
                  transition={{
                    duration: 3,
                    ease: "easeInOut",
                    repeat: Infinity,
                  }}
                />
              </div>
            </div>
          )}

          {/* Status Badge */}
          <div className="mt-6 flex items-center justify-between">
            <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-${config.color}-500/10 border border-${config.color}-500/20`}>
              <span className={`relative flex h-2 w-2`}>
                <span className={`animate-pulse absolute inline-flex h-full w-full rounded-full bg-${config.color}-400 opacity-75`}></span>
                <span className={`relative inline-flex rounded-full h-2 w-2 bg-${config.color}-500`}></span>
              </span>
              <span className={`text-xs font-bold text-${config.color}-400 uppercase tracking-wider`}>
                {isGenerating ? 'Processing' : 'Ready'}
              </span>
            </div>

            <Sparkles className={`w-5 h-5 text-${config.color}-400 opacity-50`} />
          </div>
        </div>
      </div>
    </motion.div>
  );
}

