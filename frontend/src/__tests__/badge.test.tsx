import { describe, it, expect } from 'vitest';
import React from 'react';
import { render, screen } from '@testing-library/react';
import { RiskBadge, StatusBadge, PriorityBadge } from '../components/common/Badge';

describe('Badge Components', () => {
  it('renders Critical RiskBadge with score and appropriate contrast', () => {
    const { container } = render(<RiskBadge category="Critical" score={85} />);
    expect(screen.getByText('Critical')).toBeDefined();
    expect(screen.getByText('85')).toBeDefined();
    expect(container.querySelector('.text-rose-300')).toBeDefined();
  });

  it('renders Low RiskBadge with emerald styling', () => {
    const { container } = render(<RiskBadge category="Low" score={15} />);
    expect(screen.getByText('Low')).toBeDefined();
    expect(container.querySelector('.text-emerald-400')).toBeDefined();
  });

  it('renders StatusBadge with formatted text', () => {
    render(<StatusBadge status="in_progress" />);
    expect(screen.getByText('in progress')).toBeDefined();
  });

  it('renders PriorityBadge with uppercase text', () => {
    render(<PriorityBadge priority="high" />);
    expect(screen.getByText('high')).toBeDefined();
  });
});
