/**
 * Frontend tests — vitest + @testing-library/react
 * Run: cd frontend && npx vitest run
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { QueryClient } from '@tanstack/react-query'

// ── Utilities ─────────────────────────────────────────────────────────────────
function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) => (
    <MemoryRouter>
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    </MemoryRouter>
  )
}

// ── format utilities ──────────────────────────────────────────────────────────
import { formatNumber, formatBytes, formatDuration, formatScore } from '../../frontend/src/utils/format'

describe('formatNumber', () => {
  it('formats millions', () => expect(formatNumber(1_820_000)).toBe('1.82M'))
  it('formats thousands', () => expect(formatNumber(12_500)).toBe('12.5K'))
  it('formats small numbers', () => expect(formatNumber(42)).toBe('42'))
  it('handles null', () => expect(formatNumber(null)).toBe('—'))
  it('handles undefined', () => expect(formatNumber(undefined)).toBe('—'))
})

describe('formatBytes', () => {
  it('formats MB', () => expect(formatBytes(2_500_000)).toContain('MB'))
  it('formats KB', () => expect(formatBytes(2048)).toBe('2.0 KB'))
  it('formats zero', () => expect(formatBytes(0)).toBe('0 B'))
})

describe('formatDuration', () => {
  it('formats seconds', () => expect(formatDuration(18.4)).toBe('18.4s'))
  it('formats minutes', () => expect(formatDuration(125)).toBe('2m 5s'))
  it('handles null', () => expect(formatDuration(null)).toBe('—'))
})

describe('formatScore', () => {
  it('formats score with 1 decimal', () => expect(formatScore(98.7)).toBe('98.7%'))
  it('handles null', () => expect(formatScore(null)).toBe('—'))
})

// ── Badge component ────────────────────────────────────────────────────────────
import { Badge, RunStatusBadge, DatasetStatusBadge, SeverityBadge } from '../../frontend/src/components/ui/Badge'

describe('Badge', () => {
  it('renders children', () => {
    render(<Badge>Hello</Badge>)
    expect(screen.getByText('Hello')).toBeDefined()
  })

  it('renders dot when prop set', () => {
    const { container } = render(<Badge dot>Active</Badge>)
    expect(container.querySelector('span.rounded-full')).toBeDefined()
  })
})

describe('RunStatusBadge', () => {
  it('renders success status', () => {
    render(<RunStatusBadge status="success" />)
    expect(screen.getByText('success')).toBeDefined()
  })

  it('renders failed status', () => {
    render(<RunStatusBadge status="failed" />)
    expect(screen.getByText('failed')).toBeDefined()
  })
})

describe('DatasetStatusBadge', () => {
  it('renders ready', () => {
    render(<DatasetStatusBadge status="ready" />)
    expect(screen.getByText('ready')).toBeDefined()
  })
})

// ── Button component ───────────────────────────────────────────────────────────
import { Button } from '../../frontend/src/components/ui/Button'

describe('Button', () => {
  it('renders text', () => {
    render(<Button>Click me</Button>)
    expect(screen.getByText('Click me')).toBeDefined()
  })

  it('calls onClick', () => {
    const fn = vi.fn()
    render(<Button onClick={fn}>Go</Button>)
    fireEvent.click(screen.getByText('Go'))
    expect(fn).toHaveBeenCalledOnce()
  })

  it('is disabled when loading', () => {
    render(<Button loading>Submit</Button>)
    expect(screen.getByRole('button')).toHaveProperty('disabled', true)
  })

  it('is disabled when disabled prop set', () => {
    render(<Button disabled>Submit</Button>)
    expect(screen.getByRole('button')).toHaveProperty('disabled', true)
  })
})

// ── StatCard component ─────────────────────────────────────────────────────────
import { StatCard } from '../../frontend/src/components/ui/Card'

describe('StatCard', () => {
  it('renders label and value', () => {
    render(<StatCard label="Total Records" value="1.82M" />)
    expect(screen.getByText('Total Records')).toBeDefined()
    expect(screen.getByText('1.82M')).toBeDefined()
  })

  it('renders trend', () => {
    render(<StatCard label="Quality" value="98.7%" trend="+2.3%" />)
    expect(screen.getByText('+2.3%')).toBeDefined()
  })
})

// ── EmptyState component ───────────────────────────────────────────────────────
import { EmptyState } from '../../frontend/src/components/ui/EmptyState'

describe('EmptyState', () => {
  it('renders title and description', () => {
    render(<EmptyState title="No datasets" description="Upload your first file" />)
    expect(screen.getByText('No datasets')).toBeDefined()
    expect(screen.getByText('Upload your first file')).toBeDefined()
  })

  it('renders action button when provided', () => {
    const fn = vi.fn()
    render(<EmptyState title="Empty" action={fn} actionLabel="Add item" />)
    fireEvent.click(screen.getByText('Add item'))
    expect(fn).toHaveBeenCalled()
  })
})

// ── Pagination component ───────────────────────────────────────────────────────
import { Pagination } from '../../frontend/src/components/ui/Pagination'

describe('Pagination', () => {
  it('shows correct range', () => {
    render(<Pagination page={2} totalPages={10} total={200} pageSize={20} onChange={() => {}} />)
    expect(screen.getByText(/21–40/)).toBeDefined()
  })

  it('disables prev on first page', () => {
    const { container } = render(<Pagination page={1} totalPages={5} total={100} pageSize={20} onChange={() => {}} />)
    const buttons = container.querySelectorAll('button')
    expect(buttons[0]).toHaveProperty('disabled', true)
  })

  it('calls onChange when clicking next', () => {
    const fn = vi.fn()
    render(<Pagination page={1} totalPages={5} total={100} pageSize={20} onChange={fn} />)
    const buttons = screen.getAllByRole('button')
    fireEvent.click(buttons[buttons.length - 1])
    expect(fn).toHaveBeenCalledWith(2)
  })
})
