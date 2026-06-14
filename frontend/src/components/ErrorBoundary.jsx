import { Component } from "react";

// Catches render-time errors anywhere below it so a bug shows a friendly message
// instead of a blank white screen.
export default class ErrorBoundary extends Component {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (this.state.failed) {
      return (
        <div className="app">
          <h1>Vocabio</h1>
          <p className="muted">
            Something broke on this page. Try reloading.
          </p>
        </div>
      );
    }
    return this.props.children;
  }
}
