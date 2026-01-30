export function CustomHeroAvatar() {
  return (
    <div className="custom-hero-avatar">
      <svg viewBox="0 0 120 120" className="custom-hero-avatar__silhouette" aria-hidden>
        <path
          d="M60 64c10.5 0 19-8.5 19-19s-8.5-19-19-19-19 8.5-19 19 8.5 19 19 19Zm0 9c-15.5 0-28 10.9-28 24.4 0 1.9 1.5 3.6 3.6 3.6h48.8c2 0 3.6-1.7 3.6-3.6C88 83.9 75.5 73 60 73Z"
          fill="none"
          stroke="rgba(255,255,255,0.9)"
          strokeWidth="3.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <style>
        {`
        .custom-hero-avatar {
          position: absolute;
          inset: 0;
          border-radius: 1.5rem;
          overflow: hidden;
          background: radial-gradient(circle at 30% 30%, rgba(143, 194, 255, 0.15), transparent 40%),
                      radial-gradient(circle at 70% 70%, rgba(255, 142, 209, 0.18), transparent 45%),
                      linear-gradient(135deg, #0d0f1f 0%, #1d1235 45%, #0a1124 100%);
          box-shadow: 0 0 0 1px rgba(255,255,255,0.04), 0 10px 30px rgba(0,0,0,0.35);
        }
        .custom-hero-avatar::before {
          content: "";
          position: absolute;
          inset: -10%;
          background-image:
            radial-gradient(1px 1px at 20% 30%, rgba(255,255,255,0.7), transparent 45%),
            radial-gradient(1px 1px at 60% 20%, rgba(255,255,255,0.5), transparent 45%),
            radial-gradient(1px 1px at 80% 55%, rgba(255,255,255,0.65), transparent 45%),
            radial-gradient(1px 1px at 35% 75%, rgba(255,255,255,0.55), transparent 45%),
            radial-gradient(1px 1px at 50% 50%, rgba(255,255,255,0.6), transparent 45%);
          opacity: 0.35;
          animation: hero-twinkle 6s ease-in-out infinite alternate;
        }
        .custom-hero-avatar::after {
          content: "";
          position: absolute;
          inset: 15%;
          border-radius: 50%;
          background: radial-gradient(circle, rgba(255,255,255,0.18), transparent 70%);
          filter: blur(18px);
          opacity: 0.9;
          animation: hero-pulse 5.5s ease-in-out infinite;
        }
        .custom-hero-avatar__silhouette {
          position: absolute;
          inset: 18% 14%;
          width: 72%;
          height: 64%;
          filter: drop-shadow(0 0 12px rgba(255,255,255,0.2));
          animation: hero-pulse 6s ease-in-out infinite alternate;
        }
        @keyframes hero-pulse {
          0% { transform: scale(1); opacity: 1; }
          50% { transform: scale(1.02); opacity: 0.9; }
          100% { transform: scale(1); opacity: 1; }
        }
        @keyframes hero-twinkle {
          0% { opacity: 0.2; transform: translate3d(0,0,0); }
          50% { opacity: 0.35; transform: translate3d(0.3%, -0.3%, 0); }
          100% { opacity: 0.15; transform: translate3d(-0.2%, 0.4%, 0); }
        }
      `}
      </style>
    </div>
  );
}
