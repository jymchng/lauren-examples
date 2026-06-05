import { NextResponse } from 'next/server';
import { db } from '@/lib/db';

export async function GET() {
  try {
    // Total orders
    const totalOrders = await db.order.count();

    // Total revenue (from non-cancelled orders)
    const revenueResult = await db.order.aggregate({
      _sum: { totalAmount: true },
      where: { status: { not: 'cancelled' } },
    });
    const totalRevenue = revenueResult._sum.totalAmount || 0;

    // Total reservations
    const totalReservations = await db.reservation.count();

    // Total unique customers (users with customer role)
    const totalCustomers = await db.user.count({
      where: { role: 'customer' },
    });

    // Orders by status
    const ordersRaw = await db.order.findMany({
      select: { status: true },
    });
    const ordersByStatus: Record<string, number> = {};
    for (const order of ordersRaw) {
      ordersByStatus[order.status] = (ordersByStatus[order.status] || 0) + 1;
    }

    // Recent orders (last 10)
    const recentOrders = await db.order.findMany({
      take: 10,
      orderBy: { createdAt: 'desc' },
      include: {
        orderItems: {
          include: {
            menuItem: {
              select: { name: true, nameZh: true },
            },
          },
        },
        user: {
          select: { id: true, name: true, email: true },
        },
      },
    });

    // Popular items (top 5 by order count)
    const popularItemsRaw = await db.orderItem.groupBy({
      by: ['menuItemId'],
      _sum: { quantity: true },
      orderBy: { _sum: { quantity: 'desc' } },
      take: 5,
    });

    const popularItems = await Promise.all(
      popularItemsRaw.map(async (item) => {
        const menuItem = await db.menuItem.findUnique({
          where: { id: item.menuItemId },
          select: { id: true, name: true, nameZh: true, price: true, image: true },
        });
        return {
          ...menuItem,
          totalOrdered: item._sum.quantity || 0,
        };
      })
    );

    // Revenue chart data - last 7 days
    const revenueChartData = [];
    const today = new Date();
    for (let i = 6; i >= 0; i--) {
      const date = new Date(today);
      date.setDate(date.getDate() - i);
      const dateStr = date.toISOString().split('T')[0];
      const nextDateStr = new Date(date.getTime() + 86400000).toISOString().split('T')[0];

      const dayOrders = await db.order.findMany({
        where: {
          createdAt: {
            gte: new Date(dateStr),
            lt: new Date(nextDateStr),
          },
          status: { not: 'cancelled' },
        },
        select: { totalAmount: true },
      });

      const dayRevenue = dayOrders.reduce((sum, o) => sum + o.totalAmount, 0);
      const dayOrderCount = dayOrders.length;

      const dayName = date.toLocaleDateString('en-US', { weekday: 'short' });

      revenueChartData.push({
        date: dateStr,
        day: dayName,
        revenue: Math.round(dayRevenue * 100) / 100,
        orders: dayOrderCount,
      });
    }

    return NextResponse.json({
      success: true,
      data: {
        totalOrders,
        totalRevenue,
        totalReservations,
        totalCustomers,
        ordersByStatus,
        recentOrders,
        popularItems,
        revenueChartData,
      },
    });
  } catch (error) {
    console.error('Error fetching admin stats:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to fetch admin stats' },
      { status: 500 }
    );
  }
}
