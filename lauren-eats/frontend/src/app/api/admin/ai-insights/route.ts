import { NextResponse } from 'next/server';
import { db } from '@/lib/db';

export async function GET() {
  try {
    // Agent interaction statistics from conversations
    const conversations = await db.conversation.findMany({
      select: { agentType: true },
    });

    const agentStats: Record<string, number> = {};
    for (const conv of conversations) {
      const agent = conv.agentType || 'unknown';
      agentStats[agent] = (agentStats[agent] || 0) + 1;
    }

    // Build agent data with names and icons
    const agentConfig: Record<string, { name: string; color: string }> = {
      concierge: { name: 'Concierge', color: '#C41E3A' },
      food_recommender: { name: 'Food Recommender', color: '#D4A843' },
      dietary: { name: 'Dietary Specialist', color: '#10B981' },
      ordering: { name: 'Ordering Assistant', color: '#F59E0B' },
      reservation: { name: 'Reservation Agent', color: '#8B5CF6' },
      support: { name: 'Support Agent', color: '#6B7280' },
    };

    const agentInteractions = Object.entries(agentConfig).map(([key, config]) => ({
      agentType: key,
      name: config.name,
      color: config.color,
      conversations: agentStats[key] || 0,
    }));

    // Most common user queries - from agent messages
    const userMessages = await db.agentMessage.findMany({
      where: { role: 'user' },
      select: { content: true },
      take: 500,
      orderBy: { createdAt: 'desc' },
    });

    // Simple keyword-based categorization
    const queryCategories: Record<string, { count: number; label: string }> = {
      menu_browse: { count: 0, label: 'Menu Browsing' },
      recommendation: { count: 0, label: 'Recommendations' },
      dietary: { count: 0, label: 'Dietary Questions' },
      ordering: { count: 0, label: 'Ordering Help' },
      reservation: { count: 0, label: 'Reservations' },
      spicy: { count: 0, label: 'Spice Level' },
      pricing: { count: 0, label: 'Pricing' },
      general: { count: 0, label: 'General' },
    };

    for (const msg of userMessages) {
      const text = msg.content.toLowerCase();
      if (text.includes('recommend') || text.includes('suggest') || text.includes('what should') || text.includes('best dish')) {
        queryCategories.recommendation.count++;
      }
      if (text.includes('menu') || text.includes('dish') || text.includes('item') || text.includes('what do you have')) {
        queryCategories.menu_browse.count++;
      }
      if (text.includes('allerg') || text.includes('gluten') || text.includes('vegan') || text.includes('vegetarian') || text.includes('dairy')) {
        queryCategories.dietary.count++;
      }
      if (text.includes('order') || text.includes('place') || text.includes('checkout') || text.includes('cart')) {
        queryCategories.ordering.count++;
      }
      if (text.includes('reserv') || text.includes('book') || text.includes('table') || text.includes('seat')) {
        queryCategories.reservation.count++;
      }
      if (text.includes('spic') || text.includes('hot') || text.includes('mild') || text.includes('chili')) {
        queryCategories.spicy.count++;
      }
      if (text.includes('price') || text.includes('cost') || text.includes('how much') || text.includes('expensive')) {
        queryCategories.pricing.count++;
      }
      queryCategories.general.count++;
    }

    const commonQueries = Object.entries(queryCategories)
      .filter(([key]) => key !== 'general')
      .map(([key, val]) => ({
        category: key,
        label: val.label,
        count: val.count,
      }))
      .sort((a, b) => b.count - a.count);

    // Response quality metrics (mock + real data)
    const totalAssistantMessages = await db.agentMessage.count({
      where: { role: 'assistant' },
    });
    const totalConversations = await db.conversation.count();
    const activeConversations = await db.conversation.count({
      where: { status: 'active' },
    });
    const endedConversations = await db.conversation.count({
      where: { status: 'ended' },
    });

    // Calculate average messages per conversation
    const avgMessagesPerConv = totalConversations > 0
      ? Math.round((userMessages.length + totalAssistantMessages) / totalConversations * 10) / 10
      : 0;

    const qualityMetrics = {
      totalConversations,
      activeConversations,
      endedConversations,
      totalUserMessages: userMessages.length,
      totalAssistantMessages,
      avgMessagesPerConversation: avgMessagesPerConv,
      avgResponseTimeMs: 850, // Mock - in production, track actual response times
      satisfactionScore: 4.7, // Mock - in production, pull from feedback
      resolutionRate: endedConversations > 0
        ? Math.round((endedConversations / totalConversations) * 100)
        : 92, // Mock fallback
    };

    return NextResponse.json({
      success: true,
      data: {
        agentInteractions,
        commonQueries,
        qualityMetrics,
      },
    });
  } catch (error) {
    console.error('Error fetching AI insights:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to fetch AI insights' },
      { status: 500 }
    );
  }
}
