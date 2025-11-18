function App() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="max-w-md w-full px-6 py-8 rounded-3xl border border-white/10 bg-white/5 backdrop-blur">
        <h1 className="text-3xl font-semibold mb-2">Vitte</h1>
        <p className="text-sm text-white/70 mb-4">
          Здесь будет мини-апп романтического AI-компаньона. Пока это только
          каркас (Этап 0).
        </p>
        <p className="text-xs text-white/40">
          Backend healthcheck: <code>/health</code> на сервисе FastAPI.
        </p>
      </div>
    </div>
  );
}

export default App;
