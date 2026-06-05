import { NextRequest } from 'next/server';
import { db } from '@/lib/db';
import ZAI from 'z-ai-web-dev-sdk';

// ─── Agent definitions ────────────────────────────────────────────────

const AGENT_INFO: Record<string, { name: string; emoji: string }> = {
  concierge: { name: 'Concierge', emoji: '🎩' },
  food_recommender: { name: 'Food Expert', emoji: '🍜' },
  dietary: { name: 'Dietary Guide', emoji: '🥬' },
  ordering: { name: 'Order Assistant', emoji: '🛒' },
  reservation: { name: 'Reservation Desk', emoji: '📅' },
  support: { name: 'Support', emoji: '🛟' },
};

const VALID_AGENT_TYPES = Object.keys(AGENT_INFO);

// ─── System Prompts with Handoff Tool ─────────────────────────────────

const HANDOFF_TOOL_INSTRUCTION = `
## Handoff Tool

You have the ability to hand off the conversation to another AI agent when the user's needs are better served by a specialist. This is a powerful capability — use it proactively when you detect the user's intent has shifted.

### When to Hand Off:
- **ordering** (🛒): User wants to place, modify, or confirm an order; asks about cart totals; wants to add items to their order
- **food_recommender** (🍜): User asks for dish suggestions, pairings, meal combos, or "what should I order?"
- **dietary** (🥬): User mentions allergies, dietary restrictions (vegan/vegetarian/gluten-free), or asks about ingredients
- **reservation** (📅): User wants to book, modify, or cancel a table reservation
- **support** (🛟): User has complaints, refund requests, or order tracking needs
- **concierge** (🎩): User has general questions about the restaurant, hours, location, or needs navigation help

### How to Hand Off:
To hand off, include this exact format anywhere in your response:

<<HANDOFF:agent_type>>

For example: <<HANDOFF:ordering>>

You can include a brief message before the handoff to explain the transition. The system will automatically route the user to the new agent.

### Examples:
- If the user says "I'd like to order the Peking Duck" → respond with a brief acknowledgment, then <<HANDOFF:ordering>>
- If the user says "I'm vegan, what can I eat?" → respond briefly, then <<HANDOFF:dietary>>
- If the user says "Can I book a table for tonight?" → respond briefly, then <<HANDOFF:reservation>>

### Important Rules:
1. Always provide a brief, friendly message before handing off — never just output the handoff tag alone
2. Only hand off when the user's intent clearly matches another agent's specialty
3. You may answer the question yourself if it's within your expertise — don't hand off unnecessarily
4. If the user's intent is ambiguous, ask for clarification rather than handing off
5. You can mention the agent you're handing off to by name (e.g., "I'll connect you with our Order Assistant")
`;

const SYSTEM_PROMPTS: Record<string, string> = {
  concierge:
    `You are the Lauren Eats concierge, a warm and knowledgeable host for our authentic Chinese restaurant. Help guests navigate our menu, find what they're looking for, and answer questions about the restaurant. You can also help route guests to the right specialist.\n\n${HANDOFF_TOOL_INSTRUCTION}`,
  food_recommender:
    `You are a Chinese cuisine expert at Lauren Eats. Recommend dishes based on preferences, suggest pairings, adapt to dietary needs, handle spicy level preferences, and suggest meal combinations for parties of any size. When the user is ready to order, hand off to the ordering agent.\n\n${HANDOFF_TOOL_INSTRUCTION}`,
  dietary:
    `You are a dietary and allergy specialist at Lauren Eats. Handle allergy questions, detect unsafe ingredients, recommend safe alternatives, support vegetarian/vegan filtering, and explain ingredients in detail. If the user wants to place an order after learning about safe options, hand off to the ordering agent.\n\n${HANDOFF_TOOL_INSTRUCTION}`,
  ordering:
    `You are the ordering assistant at Lauren Eats. Help build orders conversationally, modify cart contents, suggest upsells intelligently, validate menu options, and confirm purchases. If the user asks for recommendations first, hand off to the food recommender. If they have dietary questions, hand off to the dietary guide.\n\n${HANDOFF_TOOL_INSTRUCTION}`,
  reservation:
    `You are the reservation concierge at Lauren Eats. Handle table bookings, manage scheduling, ask follow-up questions about party size and preferences, and confirm reservations. If the user wants to explore the menu while booking, hand off to the food recommender.\n\n${HANDOFF_TOOL_INSTRUCTION}`,
  support:
    `You are customer support at Lauren Eats. Handle complaints professionally, manage refund requests, provide order tracking information, and escalate issues when needed. If the user wants to place a new order after resolving their issue, hand off to the ordering agent.\n\n${HANDOFF_TOOL_INSTRUCTION}`,
};

const DEFAULT_SYSTEM_PROMPT =
  `You are the Lauren Eats AI assistant, a helpful and friendly chatbot for our authentic Chinese restaurant. Answer questions about our menu, take orders, help with reservations, and provide excellent customer service.\n\n${HANDOFF_TOOL_INSTRUCTION}`;

// ─── Handoff Detection ────────────────────────────────────────────────

const HANDOFF_REGEX = /<<HANDOFF:(concierge|food_recommender|dietary|ordering|reservation|support)>>/g;

function extractHandoff(content: string): { cleanContent: string; targetAgent: string | null } {
  const matches = [...content.matchAll(HANDOFF_REGEX)];
  if (matches.length === 0) {
    return { cleanContent: content, targetAgent: null };
  }

  // Take the last handoff tag (in case the model outputs multiple)
  const targetAgent = matches[matches.length - 1][1];
  // Remove all handoff tags from content
  const cleanContent = content.replace(HANDOFF_REGEX, '').trim();

  return { cleanContent, targetAgent };
}

// ─── POST Handler ─────────────────────────────────────────────────────

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { message, conversationId, agentType } = body;

    if (!message || typeof message !== 'string') {
      return new Response(
        JSON.stringify({ success: false, error: 'Message is required' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    // Determine system prompt based on agent type
    const systemPrompt = (agentType && SYSTEM_PROMPTS[agentType])
      ? SYSTEM_PROMPTS[agentType]
      : DEFAULT_SYSTEM_PROMPT;

    // Build messages array for AI
    const aiMessages: { role: 'system' | 'user' | 'assistant'; content: string }[] = [
      { role: 'system', content: systemPrompt },
    ];

    // Load conversation history if conversationId provided
    let conversation;
    if (conversationId) {
      conversation = await db.conversation.findUnique({
        where: { id: conversationId },
        include: {
          messages: {
            orderBy: { createdAt: 'asc' },
            take: 20, // Limit context window
          },
        },
      });

      if (conversation) {
        for (const msg of conversation.messages) {
          if (msg.role === 'user' || msg.role === 'assistant') {
            // Strip any previous handoff tags from history
            const cleanContent = msg.content.replace(HANDOFF_REGEX, '').trim();
            if (cleanContent) {
              aiMessages.push({
                role: msg.role as 'user' | 'assistant',
                content: cleanContent,
              });
            }
          }
        }
      }
    }

    // Add the current user message
    aiMessages.push({ role: 'user', content: message });

    // Save user message to database
    let dbConversationId = conversationId;
    if (!conversation) {
      // Create new conversation
      const newConversation = await db.conversation.create({
        data: {
          agentType: agentType || null,
          title: message.substring(0, 50),
          status: 'active',
        },
      });
      dbConversationId = newConversation.id;
    }

    await db.agentMessage.create({
      data: {
        conversationId: dbConversationId,
        role: 'user',
        content: message,
        agentType: agentType || null,
      },
    });

    // Call AI SDK with streaming
    const zai = await ZAI.create();
    const stream = await zai.chat.completions.create({
      messages: aiMessages,
      stream: true,
    }) as ReadableStream<Uint8Array>;

    // Create a TransformStream to process the AI response
    let fullAssistantContent = '';

    const transformStream = new TransformStream({
      transform(chunk, controller) {
        // Pass through the raw SSE chunks
        const text = new TextDecoder().decode(chunk);
        fullAssistantContent += text;
        controller.enqueue(chunk);
      },
      async flush() {
        // After the stream ends, save the assistant message to DB
        try {
          // Extract the actual content from SSE data
          let extractedContent = '';
          const lines = fullAssistantContent.split('\n');
          for (const line of lines) {
            if (line.startsWith('data: ') && line !== 'data: [DONE]') {
              try {
                const json = JSON.parse(line.substring(6));
                const delta = json.choices?.[0]?.delta?.content;
                if (delta) {
                  extractedContent += delta;
                }
              } catch {
                // Skip malformed JSON lines
              }
            }
          }

          if (extractedContent) {
            // Check for handoff
            const { cleanContent, targetAgent } = extractHandoff(extractedContent);

            await db.agentMessage.create({
              data: {
                conversationId: dbConversationId!,
                role: 'assistant',
                content: cleanContent,
                agentType: targetAgent || agentType || null,
                metadata: targetAgent ? JSON.stringify({ handoff: { from: agentType, to: targetAgent } }) : null,
              },
            });

            // Update conversation's agentType if handoff occurred
            if (targetAgent) {
              await db.conversation.update({
                where: { id: dbConversationId! },
                data: { agentType: targetAgent, updatedAt: new Date() },
              });
            } else {
              await db.conversation.update({
                where: { id: dbConversationId! },
                data: { updatedAt: new Date() },
              });
            }
          }
        } catch (dbError) {
          console.error('Error saving assistant message:', dbError);
        }
      },
    });

    // Pipe the AI stream through our transform
    const processedStream = stream.pipeThrough(transformStream);

    // Create the final SSE stream with metadata, content, and handoff events
    const encoder = new TextEncoder();
    let contentBuffer = ''; // Track accumulated content for handoff detection

    const sseStream = new ReadableStream({
      async start(controller) {
        // Send conversation metadata as the first SSE event
        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify({ type: 'meta', conversationId: dbConversationId })}\n\n`)
        );

        // Pipe the processed stream, intercepting content for handoff detection
        const reader = processedStream.getReader();
        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            // Decode the chunk to check for handoff markers
            const text = new TextDecoder().decode(value);
            const lines = text.split('\n');

            for (const line of lines) {
              if (!line.startsWith('data: ') || line === 'data: [DONE]') continue;

              try {
                const json = JSON.parse(line.slice(6).trim());
                const delta = json.choices?.[0]?.delta?.content;
                if (delta) {
                  contentBuffer += delta;
                }
              } catch {
                // skip
              }
            }

            // Pass through the raw chunk
            controller.enqueue(value);
          }
        } catch (error) {
          console.error('Stream read error:', error);
        }

        // After stream is complete, check for handoff in accumulated content
        const { cleanContent, targetAgent } = extractHandoff(contentBuffer);

        if (targetAgent && VALID_AGENT_TYPES.includes(targetAgent)) {
          const fromAgent = agentType || 'concierge';
          const fromInfo = AGENT_INFO[fromAgent] || { name: 'Assistant', emoji: '🤖' };
          const toInfo = AGENT_INFO[targetAgent];

          // Emit handoff event
          controller.enqueue(
            encoder.encode(
              `data: ${JSON.stringify({
                type: 'handoff',
                fromAgent,
                toAgent: targetAgent,
                fromAgentName: fromInfo.name,
                toAgentName: toInfo.name,
                fromAgentEmoji: fromInfo.emoji,
                toAgentEmoji: toInfo.emoji,
                reason: `Transferring you to ${toInfo.name}`,
              })}\n\n`
            )
          );

          // If the content had handoff tags, emit a content-replace event
          // so the frontend can clean up the displayed content
          if (cleanContent !== contentBuffer) {
            controller.enqueue(
              encoder.encode(
                `data: ${JSON.stringify({
                  type: 'content_replace',
                  content: cleanContent,
                })}\n\n`
              )
            );
          }
        }

        // Send done event
        controller.enqueue(
          encoder.encode('data: [DONE]\n\n')
        );
        controller.close();
      },
    });

    return new Response(sseStream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive',
      },
    });
  } catch (error) {
    console.error('Error in chat API:', error);
    return new Response(
      JSON.stringify({ success: false, error: 'Failed to process chat message' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}
