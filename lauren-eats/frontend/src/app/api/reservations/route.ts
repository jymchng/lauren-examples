import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { Prisma } from '@prisma/client';

// GET /api/reservations - Fetch reservations with optional filters
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);

    const where: Prisma.ReservationWhereInput = {};

    // Date filter
    const date = searchParams.get('date');
    if (date) {
      where.date = date;
    }

    // Status filter
    const status = searchParams.get('status');
    if (status) {
      where.status = status;
    }

    const reservations = await db.reservation.findMany({
      where,
      include: {
        user: {
          select: {
            id: true,
            name: true,
            email: true,
          },
        },
      },
      orderBy: [
        { date: 'asc' },
        { time: 'asc' },
      ],
    });

    return NextResponse.json({
      success: true,
      data: reservations,
    });
  } catch (error) {
    console.error('Error fetching reservations:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to fetch reservations' },
      { status: 500 }
    );
  }
}

// POST /api/reservations - Create a reservation
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const {
      customerName,
      customerPhone,
      customerEmail,
      partySize,
      date,
      time,
      specialRequests,
      occasion,
      userId,
    } = body;

    // Validate required fields
    if (!customerName || !customerPhone || !partySize || !date || !time) {
      return NextResponse.json(
        { success: false, error: 'Missing required fields: customerName, customerPhone, partySize, date, time' },
        { status: 400 }
      );
    }

    // Validate party size
    if (partySize < 1 || partySize > 20) {
      return NextResponse.json(
        { success: false, error: 'Party size must be between 1 and 20' },
        { status: 400 }
      );
    }

    // Validate date format
    const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
    if (!dateRegex.test(date)) {
      return NextResponse.json(
        { success: false, error: 'Date must be in YYYY-MM-DD format' },
        { status: 400 }
      );
    }

    // Validate time format
    const timeRegex = /^\d{2}:\d{2}$/;
    if (!timeRegex.test(time)) {
      return NextResponse.json(
        { success: false, error: 'Time must be in HH:MM format' },
        { status: 400 }
      );
    }

    // Validate occasion if provided
    const validOccasions = ['birthday', 'anniversary', 'business', 'casual'];
    if (occasion && !validOccasions.includes(occasion)) {
      return NextResponse.json(
        { success: false, error: `Invalid occasion. Valid options: ${validOccasions.join(', ')}` },
        { status: 400 }
      );
    }

    const reservation = await db.reservation.create({
      data: {
        userId: userId || null,
        customerName,
        customerPhone,
        customerEmail: customerEmail || null,
        partySize,
        date,
        time,
        status: 'pending',
        specialRequests: specialRequests || null,
        occasion: occasion || null,
      },
      include: {
        user: {
          select: {
            id: true,
            name: true,
            email: true,
          },
        },
      },
    });

    return NextResponse.json({
      success: true,
      data: reservation,
    }, { status: 201 });
  } catch (error) {
    console.error('Error creating reservation:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to create reservation' },
      { status: 500 }
    );
  }
}
