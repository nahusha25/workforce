import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { MetricCard } from './MetricCard';

afterEach(() => {
  cleanup();
});

describe('MetricCard', () => {
  it('renders title, value, and subtitle correctly', () => {
    render(
      <MetricCard
        title="Active Workforce"
        value="42"
        subtitle="Distinct active employees"
      />
    );

    expect(screen.getByText('Active Workforce')).toBeTruthy();
    expect(screen.getByText('42')).toBeTruthy();
    expect(screen.getByText('Distinct active employees')).toBeTruthy();
  });

  it('renders skeleton in loading state', () => {
    render(
      <MetricCard
        title="Active Workforce"
        value="42"
        isLoading={true}
      />
    );

    expect(screen.getByTestId('metric-card-loading')).toBeTruthy();
    expect(screen.queryByText('42')).toBeNull();
  });

  it('renders error state banner', () => {
    render(
      <MetricCard
        title="Material Spend"
        value={null}
        isError={true}
      />
    );

    expect(screen.getByText(/Failed to load metric/i)).toBeTruthy();
  });

  it('renders trend indicators with up/down direction', () => {
    const { rerender } = render(
      <MetricCard
        title="Completed"
        value="120"
        trend={{ direction: 'up', text: '+12% vs last month' }}
      />
    );
    expect(screen.getByText(/↑ \+12% vs last month/i)).toBeTruthy();

    rerender(
      <MetricCard
        title="Completed"
        value="100"
        trend={{ direction: 'down', text: '-5% vs last month' }}
      />
    );
    expect(screen.getByText(/↓ -5% vs last month/i)).toBeTruthy();
  });

  it('handles click events when onClick is provided', () => {
    const handleClick = vi.fn();
    render(
      <MetricCard
        title="Clickable Metric"
        value="500"
        onClick={handleClick}
      />
    );

    const card = screen.getByRole('button');
    fireEvent.click(card);
    expect(handleClick).toHaveBeenCalledTimes(1);

    fireEvent.keyDown(card, { key: 'Enter' });
    expect(handleClick).toHaveBeenCalledTimes(2);
  });
});
