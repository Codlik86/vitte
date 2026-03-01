import { Component, type ErrorInfo, type ReactNode } from "react";
import { withTranslation, type WithTranslation } from "react-i18next";

type ErrorBoundaryProps = {
  children: ReactNode;
} & WithTranslation;

type ErrorBoundaryState = {
  hasError: boolean;
  error?: Error;
};

class ErrorBoundaryBase extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: undefined };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log to console so we can see the root cause instead of silent black screen.
    console.error("[Vitte miniapp] Unhandled render error", error, errorInfo);
  }

  handleReload = () => {
    // A simple manual retry to avoid the app staying blank.
    window.location.reload();
  };

  render() {
    const { t } = this.props;
    if (this.state.hasError) {
      return (
        <div className="min-h-dvh bg-bg-dark text-white flex flex-col items-center justify-center px-6 text-center">
          <p className="text-lg font-semibold">{t("error_generic")}</p>
          {this.state.error?.message && (
            <p className="mt-2 text-sm text-white/70">
              {this.state.error.message}
            </p>
          )}
          <button
            type="button"
            onClick={this.handleReload}
            className="mt-4 rounded-full bg-white px-4 py-2 text-sm font-semibold text-bg-dark active:scale-[0.98]"
          >
            {t("reload")}
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export const ErrorBoundary = withTranslation()(ErrorBoundaryBase);
