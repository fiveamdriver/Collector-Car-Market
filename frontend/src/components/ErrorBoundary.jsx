import { Component } from 'react'
import { Link } from 'react-router-dom'

// Without a boundary, any render-time throw unmounts the entire app into a
// blank white page with no recovery path.
export default class ErrorBoundary extends Component {
  state = { error: null }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    console.error('Unhandled render error:', error, info)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="inner">
          <div className="page-header">
            <h1 className="page-title">Something went wrong</h1>
          </div>
          <p className="status error">
            An unexpected error occurred while rendering this page.
          </p>
          <p>
            <Link to="/" onClick={() => this.setState({ error: null })}>
              Back to Markets
            </Link>
          </p>
        </div>
      )
    }
    return this.props.children
  }
}
