'use client'

import { motion } from 'framer-motion'
import { getAgentByType } from './agents'
import type { AgentType } from '@/types'

interface TypingIndicatorProps {
  agentType: AgentType
}

export function TypingIndicator({ agentType }: TypingIndicatorProps) {
  const agent = getAgentByType(agentType)

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.2 }}
      className="flex items-end gap-2.5 px-4 py-2"
    >
      {/* Agent avatar */}
      <div
        className="flex items-center justify-center w-8 h-8 rounded-full shrink-0 text-sm shadow-sm"
        style={{ backgroundColor: agent.color + '20', border: `1.5px solid ${agent.color}40` }}
      >
        {agent.emoji}
      </div>

      {/* Typing bubble */}
      <div className="flex flex-col gap-1">
        <span className="text-[11px] text-muted-foreground/70 pl-1">
          {agent.name} is typing...
        </span>
        <div className="bg-card border border-border/60 rounded-2xl rounded-bl-md px-4 py-3 shadow-sm">
          <div className="flex items-center gap-1.5">
            <motion.span
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: agent.color }}
              animate={{ opacity: [0.3, 1, 0.3], scale: [0.85, 1.1, 0.85] }}
              transition={{ duration: 1.2, repeat: Infinity, delay: 0 }}
            />
            <motion.span
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: agent.color }}
              animate={{ opacity: [0.3, 1, 0.3], scale: [0.85, 1.1, 0.85] }}
              transition={{ duration: 1.2, repeat: Infinity, delay: 0.2 }}
            />
            <motion.span
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: agent.color }}
              animate={{ opacity: [0.3, 1, 0.3], scale: [0.85, 1.1, 0.85] }}
              transition={{ duration: 1.2, repeat: Infinity, delay: 0.4 }}
            />
          </div>
        </div>
      </div>
    </motion.div>
  )
}
