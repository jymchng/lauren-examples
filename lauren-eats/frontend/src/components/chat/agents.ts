import type { AgentType } from '@/types'

export interface AgentDef {
  type: AgentType
  name: string
  emoji: string
  color: string
  description: string
  quickPrompts: string[]
}

export const AGENTS: AgentDef[] = [
  {
    type: 'concierge' as AgentType,
    name: 'Concierge',
    emoji: '🎩',
    color: '#C41E3A',
    description: 'Welcome & navigation',
    quickPrompts: [
      'Tell me about the restaurant',
      'What do you recommend?',
      'Help me find something',
    ],
  },
  {
    type: 'food_recommender' as AgentType,
    name: 'Food Expert',
    emoji: '🍜',
    color: '#D4A843',
    description: 'Dish recommendations & pairings',
    quickPrompts: [
      'Best dishes for a first visit?',
      'Suggest a meal for 4',
      'What pairs well with duck?',
    ],
  },
  {
    type: 'dietary' as AgentType,
    name: 'Dietary Guide',
    emoji: '🥬',
    color: '#4CAF50',
    description: 'Allergies & dietary needs',
    quickPrompts: [
      'I have a peanut allergy',
      'Show me vegan options',
      'Is this dish gluten-free?',
    ],
  },
  {
    type: 'ordering' as AgentType,
    name: 'Order Assistant',
    emoji: '🛒',
    color: '#FF6B35',
    description: 'Build & modify orders',
    quickPrompts: [
      'I want to order Peking Duck',
      'Add spring rolls to my order',
      'What is my current total?',
    ],
  },
  {
    type: 'reservation' as AgentType,
    name: 'Reservation Desk',
    emoji: '📅',
    color: '#7B68EE',
    description: 'Table bookings & scheduling',
    quickPrompts: [
      'Book a table for tonight',
      'Reserve for 6 people Friday',
      'Cancel my reservation',
    ],
  },
  {
    type: 'support' as AgentType,
    name: 'Support',
    emoji: '🛟',
    color: '#2196F3',
    description: 'Help with orders & issues',
    quickPrompts: [
      'Where is my order?',
      'I have a complaint',
      'Request a refund',
    ],
  },
]

export function getAgentByType(type: AgentType): AgentDef {
  return AGENTS.find((a) => a.type === type) ?? AGENTS[0]
}
