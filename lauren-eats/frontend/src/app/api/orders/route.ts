import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { Prisma } from '@prisma/client';

// GET /api/orders - Fetch orders with optional filters
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);

    const where: Prisma.OrderWhereInput = {};

    // Status filter
    const status = searchParams.get('status');
    if (status) {
      where.status = status;
    }

    // UserId filter
    const userId = searchParams.get('userId');
    if (userId) {
      where.userId = userId;
    }

    const orders = await db.order.findMany({
      where,
      include: {
        orderItems: {
          include: {
            menuItem: true,
          },
        },
        user: {
          select: {
            id: true,
            name: true,
            email: true,
          },
        },
      },
      orderBy: { createdAt: 'desc' },
    });

    return NextResponse.json({
      success: true,
      data: orders,
    });
  } catch (error) {
    console.error('Error fetching orders:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to fetch orders' },
      { status: 500 }
    );
  }
}

// POST /api/orders - Create a new order
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { userId, items, type, tableNumber, notes } = body;

    // Validate required fields
    if (!items || !Array.isArray(items) || items.length === 0) {
      return NextResponse.json(
        { success: false, error: 'Order must contain at least one item' },
        { status: 400 }
      );
    }

    if (!type || !['dine_in', 'takeout', 'delivery'].includes(type)) {
      return NextResponse.json(
        { success: false, error: 'Valid order type is required (dine_in, takeout, delivery)' },
        { status: 400 }
      );
    }

    // Fetch all menu items to calculate prices
    const menuItemIds = items.map((item: { menuItemId: string }) => item.menuItemId);
    const menuItems = await db.menuItem.findMany({
      where: {
        id: { in: menuItemIds },
        isAvailable: true,
      },
    });

    if (menuItems.length !== menuItemIds.length) {
      return NextResponse.json(
        { success: false, error: 'One or more menu items are unavailable' },
        { status: 400 }
      );
    }

    // Build order items with prices
    const orderItemsData = items.map((item: { menuItemId: string; quantity: number; notes?: string }) => {
      const menuItem = menuItems.find((mi) => mi.id === item.menuItemId);
      if (!menuItem) {
        throw new Error(`Menu item ${item.menuItemId} not found`);
      }
      const quantity = item.quantity || 1;
      const totalPrice = Math.round(menuItem.price * quantity * 100) / 100;
      return {
        menuItemId: item.menuItemId,
        quantity,
        unitPrice: menuItem.price,
        totalPrice,
        notes: item.notes || null,
      };
    });

    // Calculate totals
    const subtotal = Math.round(
      orderItemsData.reduce((sum: number, item: { totalPrice: number }) => sum + item.totalPrice, 0) * 100
    ) / 100;
    const tax = Math.round(subtotal * 0.08 * 100) / 100;
    const totalAmount = Math.round((subtotal + tax) * 100) / 100;

    // Generate order number
    const orderNumber = `LE-${Date.now().toString(36).toUpperCase()}-${Math.random().toString(36).substring(2, 6).toUpperCase()}`;

    const order = await db.order.create({
      data: {
        userId: userId || null,
        orderNumber,
        status: 'pending',
        type,
        tableNumber: tableNumber || null,
        notes: notes || null,
        subtotal,
        tax,
        totalAmount,
        orderItems: {
          create: orderItemsData,
        },
      },
      include: {
        orderItems: {
          include: {
            menuItem: true,
          },
        },
      },
    });

    return NextResponse.json({
      success: true,
      data: order,
    }, { status: 201 });
  } catch (error) {
    console.error('Error creating order:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to create order' },
      { status: 500 }
    );
  }
}
