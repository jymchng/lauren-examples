import { NextResponse } from 'next/server';
import { seed } from '@/lib/seed';

export async function POST() {
  try {
    const result = await seed();
    return NextResponse.json({
      success: true,
      data: result,
    });
  } catch (error) {
    console.error('Error seeding database:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to seed database' },
      { status: 500 }
    );
  }
}
