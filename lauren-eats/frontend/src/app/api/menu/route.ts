import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { Prisma } from '@prisma/client';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);

    // Build filter conditions
    const where: Prisma.MenuItemWhereInput = { isAvailable: true };

    // Category filter
    const category = searchParams.get('category');
    if (category && category !== 'all') {
      where.category = {
        slug: category,
      };
    }

    // Search filter (name contains, case insensitive)
    const search = searchParams.get('search');
    if (search) {
      where.OR = [
        { name: { contains: search } },
        { nameZh: { contains: search } },
        { description: { contains: search } },
      ];
    }

    // Dietary filters
    const isVegetarian = searchParams.get('isVegetarian');
    if (isVegetarian === 'true') {
      where.isVegetarian = true;
    }

    const isVegan = searchParams.get('isVegan');
    if (isVegan === 'true') {
      where.isVegan = true;
    }

    const isGlutenFree = searchParams.get('isGlutenFree');
    if (isGlutenFree === 'true') {
      where.isGlutenFree = true;
    }

    // Spicy level filter
    const spicyLevel = searchParams.get('spicyLevel');
    if (spicyLevel) {
      const level = parseInt(spicyLevel, 10);
      if (!isNaN(level)) {
        where.spicyLevel = { lte: level };
      }
    }

    // Popular filter
    const isPopular = searchParams.get('isPopular');
    if (isPopular === 'true') {
      where.isPopular = true;
    }

    // ─── Pagination ─────────────────────────────────────────────────────
    const page = Math.max(1, parseInt(searchParams.get('page') || '1', 10) || 1);
    const limit = Math.min(
      100,
      Math.max(1, parseInt(searchParams.get('limit') || '12', 10) || 12)
    );
    const skip = (page - 1) * limit;

    // Get total count for pagination metadata
    const [menuItems, total] = await Promise.all([
      db.menuItem.findMany({
        where,
        include: {
          category: true,
        },
        orderBy: [
          { isPopular: 'desc' },
          { name: 'asc' },
        ],
        skip,
        take: limit,
      }),
      db.menuItem.count({ where }),
    ]);

    const totalPages = Math.ceil(total / limit);

    return NextResponse.json({
      success: true,
      data: menuItems,
      pagination: {
        page,
        limit,
        total,
        totalPages,
        hasMore: page < totalPages,
      },
    });
  } catch (error) {
    console.error('Error fetching menu items:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to fetch menu items' },
      { status: 500 }
    );
  }
}
