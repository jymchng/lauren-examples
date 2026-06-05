import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';

// PUT /api/reservations/[id] - Update reservation status
export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const body = await request.json();
    const { status } = body;

    // Validate status
    const validStatuses = ['pending', 'confirmed', 'cancelled', 'completed'];
    if (!status || !validStatuses.includes(status)) {
      return NextResponse.json(
        { success: false, error: `Valid status is required (${validStatuses.join(', ')})` },
        { status: 400 }
      );
    }

    // Check if reservation exists
    const existingReservation = await db.reservation.findUnique({ where: { id } });
    if (!existingReservation) {
      return NextResponse.json(
        { success: false, error: 'Reservation not found' },
        { status: 404 }
      );
    }

    const updatedReservation = await db.reservation.update({
      where: { id },
      data: { status },
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
      data: updatedReservation,
    });
  } catch (error) {
    console.error('Error updating reservation:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to update reservation' },
      { status: 500 }
    );
  }
}
