import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { EmptyState, ItemCard, Pagination, ScoreBar, StatusBadge } from './ui'
import { titleCase } from '../lib/format'
import { qs } from '../lib/api'

describe('ui components', () => {
  it('renders status badge with readable label', () => {
    render(<StatusBadge status="in_review" />)
    expect(screen.getByText('In Review')).toBeInTheDocument()
  })
  it('item card shows public fields and links to detail page', () => {
    render(<MemoryRouter><ItemCard item={{ id: 7, title: 'Blue bag', description: 'A blue bag', category: 'Bags', location: 'Library', date: '2026-03-01', status: 'available', images: [] }} /></MemoryRouter>)
    expect(screen.getByRole('link')).toHaveAttribute('href', '/items/7')
    expect(screen.getByText('No photo')).toBeInTheDocument()
  })
  it('score bar exposes accessible meter value', () => {
    render(<ScoreBar score={82.4} />)
    expect(screen.getByRole('meter')).toHaveAttribute('aria-valuenow', '82.4')
    expect(screen.getByText('82%')).toBeInTheDocument()
  })
  it('pagination calls back with next page', () => {
    let got = 0
    render(<Pagination page={1} pages={3} total={30} onChange={(p) => { got = p }} />)
    screen.getByText('Next').click()
    expect(got).toBe(2)
  })
  it('empty state renders title and text', () => {
    render(<EmptyState title="Nothing here" text="Try again" />)
    expect(screen.getByText('Nothing here')).toBeInTheDocument()
  })
  it('helpers format values', () => {
    expect(titleCase('claim_approved')).toBe('Claim Approved')
    expect(qs({ a: 1, b: '', c: undefined, d: 'x y' })).toBe('?a=1&d=x+y')
  })
})
