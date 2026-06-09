import { Link } from 'react-router-dom'

export default function Layout({ children }) {
  return (
    <div className="layout">
      <header className="site-header">
        <Link to="/" className="site-logo">pcarmarket</Link>
      </header>
      <main className="layout-body">{children}</main>
    </div>
  )
}
