import { create } from "zustand";
import type { ChatMessage, AgentType } from "@/types";

interface ChatState {
  messages: ChatMessage[];
  currentAgent: AgentType;
  isStreaming: boolean;
  conversationId: string | null;

  // Actions
  addMessage: (message: ChatMessage) => void;
  updateMessage: (id: string, updates: Partial<ChatMessage>) => void;
  setStreaming: (streaming: boolean) => void;
  setAgent: (agent: AgentType) => void;
  clearMessages: () => void;
  setConversationId: (id: string | null) => void;
  addHandoffMessage: (fromAgent: AgentType, toAgent: AgentType, fromName: string, toName: string, fromEmoji: string, toEmoji: string, reason?: string) => void;
}

export const useChatStore = create<ChatState>()((set, get) => ({
  messages: [],
  currentAgent: "concierge" as AgentType,
  isStreaming: false,
  conversationId: null,

  addMessage: (message: ChatMessage) => {
    set((state) => ({
      messages: [...state.messages, message],
    }));
  },

  updateMessage: (id: string, updates: Partial<ChatMessage>) => {
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === id ? { ...msg, ...updates } : msg
      ),
    }));
  },

  setStreaming: (streaming: boolean) => {
    set({ isStreaming: streaming });
  },

  setAgent: (agent: AgentType) => {
    set({ currentAgent: agent });
  },

  clearMessages: () => {
    set({ messages: [], conversationId: null });
  },

  setConversationId: (id: string | null) => {
    set({ conversationId: id });
  },

  addHandoffMessage: (
    fromAgent: AgentType,
    toAgent: AgentType,
    fromName: string,
    toName: string,
    fromEmoji: string,
    toEmoji: string,
    reason?: string
  ) => {
    const handoffMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: reason || `Transferring you to ${toName}`,
      agentType: fromAgent,
      timestamp: Date.now(),
      metadata: {
        type: "handoff",
        fromAgent,
        toAgent,
        fromName,
        toName,
        fromEmoji,
        toEmoji,
      },
    };
    set((state) => ({
      messages: [...state.messages, handoffMsg],
      currentAgent: toAgent,
    }));
  },
}));
