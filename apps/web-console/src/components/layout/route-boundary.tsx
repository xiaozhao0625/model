import { Component, type ReactNode } from "react";
import { Card } from "../ui/card";

interface RouteBoundaryProps {
  children: ReactNode;
}

interface RouteBoundaryState {
  error: string | null;
}

export class RouteBoundary extends Component<RouteBoundaryProps, RouteBoundaryState> {
  state: RouteBoundaryState = { error: null };

  static getDerivedStateFromError(error: unknown): RouteBoundaryState {
    return { error: error instanceof Error ? error.message : String(error) };
  }

  componentDidUpdate(previousProps: RouteBoundaryProps) {
    if (previousProps.children !== this.props.children && this.state.error) {
      this.setState({ error: null });
    }
  }

  render() {
    if (this.state.error) {
      return (
        <Card title="Page Error" eyebrow="route boundary">
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-100">
            <p>{this.state.error}</p>
          </div>
        </Card>
      );
    }
    return this.props.children;
  }
}
